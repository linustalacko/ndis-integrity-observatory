"""M4: Claims integrity engine.

Deterministic invoice screening against the NDIS Support Catalogue price caps
and the fraud typologies that are decidable from claims data alone:

  R1 price-cap breach        (rate > catalogue limit for item/state)
  R2 invalid support item    (item code not in catalogue)
  R3 duplicate claim         (same participant+provider+item+date+qty)
  R4 overlapping deliveries  (same worker/provider >24h in one day)
  R5 expired-plan claim      (service date outside plan period)
  R6 weekend/holiday loading on a weekday item code
  R7 sanctioned provider     (provider ABN/name in enforcement register)
  R8 advance claiming        (service date after invoice/claim date)

Every finding cites the rule, the catalogue row or register record, and the
invoice line. CLI: python -m app.claims [invoices.csv]
"""
from __future__ import annotations

import io
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pandas as pd

from .db import connect

CATALOGUE_URL = "https://www.ndis.gov.au/media/7739/download?attachment="  # 2025-26 v1.1 XLSX
CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "data" / "support_catalogue.xlsx"

STATE_CAP_COLS = {
    "ACT": "ACT", "NSW": "NSW", "NT": "NT", "QLD": "QLD",
    "SA": "SA", "TAS": "TAS", "VIC": "VIC", "WA": "WA",
}


@dataclass
class Finding:
    rule: str
    severity: str           # "breach" | "warning"
    invoice_line: int
    detail: str
    citation: str


@dataclass
class Invoice:
    """One invoice line. CSV columns map 1:1."""
    line: int
    participant: str
    provider_name: str
    provider_abn: str
    item_code: str
    service_date: str       # ISO
    claim_date: str         # ISO
    qty: float
    unit_price: float
    state: str
    plan_start: str
    plan_end: str
    worker_id: str = ""
    hours: float = 0.0


def fetch_catalogue() -> pd.DataFrame:
    if not CATALOGUE_PATH.exists():
        r = httpx.get(CATALOGUE_URL, timeout=180, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        CATALOGUE_PATH.write_bytes(r.content)
    df = pd.read_excel(CATALOGUE_PATH, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def catalogue_index(df: pd.DataFrame) -> dict:
    """item code -> {name, caps per state}. Column names vary; detect them."""
    code_col = next((c for c in df.columns if "item number" in c.lower()
                     or c.lower() in ("support item number", "item code")), df.columns[0])
    name_col = next((c for c in df.columns if "item name" in c.lower()), df.columns[1])
    idx = {}
    for _, row in df.iterrows():
        code = str(row[code_col]).strip()
        caps = {}
        for state in STATE_CAP_COLS:
            col = next((c for c in df.columns if c.strip().upper() == state), None)
            if col is not None:
                try:
                    caps[state] = float(row[col])
                except (TypeError, ValueError):
                    pass
        idx[code] = {"name": str(row[name_col]), "caps": caps}
    return idx


def sanctioned_providers(conn) -> dict[str, str]:
    """abn/norm_name -> action summary for screening."""
    out = {}
    for r in conn.execute("SELECT name, norm_name, abn, type, date_from FROM actions "
                          "WHERE type IN ('ER - Banning Order', "
                          "'ER - Revocation of registration', "
                          "'ER - Suspension of registration')"):
        summary = f"{r['type'][5:]} effective {r['date_from']} ({r['name']})"
        if r["abn"]:
            out[r["abn"]] = summary
        out[r["norm_name"]] = summary
    return out


def screen(invoices: list[Invoice], catalogue: dict, sanctions: dict) -> list[Finding]:
    from .ingest import norm_name
    findings: list[Finding] = []
    seen = {}
    worker_day_hours = defaultdict(float)

    for inv in invoices:
        item = catalogue.get(inv.item_code)
        if item is None:
            findings.append(Finding("R2 invalid support item", "breach", inv.line,
                                    f"item {inv.item_code} not in Support Catalogue 2025-26",
                                    "NDIS Support Catalogue 2025-26 v1.1"))
        else:
            cap = item["caps"].get(inv.state.upper())
            if cap and inv.unit_price > cap + 0.005:
                findings.append(Finding(
                    "R1 price-cap breach", "breach", inv.line,
                    f"{inv.item_code} charged ${inv.unit_price:.2f} vs cap ${cap:.2f} "
                    f"({inv.state}) — {(inv.unit_price / cap - 1) * 100:.0f}% over",
                    f"Support Catalogue: {item['name'][:60]}"))

        key = (inv.participant, inv.provider_abn or inv.provider_name,
               inv.item_code, inv.service_date, inv.qty)
        if key in seen:
            findings.append(Finding("R3 duplicate claim", "breach", inv.line,
                                    f"identical to line {seen[key]} "
                                    f"(participant/provider/item/date/qty)",
                                    "duplicate-detection rule"))
        seen.setdefault(key, inv.line)

        if inv.worker_id and inv.hours:
            wd = (inv.worker_id, inv.service_date)
            worker_day_hours[wd] += inv.hours
            if worker_day_hours[wd] > 24:
                findings.append(Finding(
                    "R4 impossible day", "breach", inv.line,
                    f"worker {inv.worker_id} billed {worker_day_hours[wd]:.1f}h "
                    f"on {inv.service_date}", "24h/day physical limit"))

        if inv.plan_start and inv.plan_end and not (
                inv.plan_start <= inv.service_date <= inv.plan_end):
            findings.append(Finding(
                "R5 expired-plan claim", "breach", inv.line,
                f"service {inv.service_date} outside plan {inv.plan_start}..{inv.plan_end}",
                "NDIA typology: claiming from expired plans"))

        if inv.service_date and inv.claim_date and inv.service_date > inv.claim_date:
            findings.append(Finding(
                "R8 advance claiming", "breach", inv.line,
                f"service {inv.service_date} is after claim date {inv.claim_date}",
                "NDIA typology: claiming in advance of delivery"))

        import datetime
        try:
            wd = datetime.date.fromisoformat(inv.service_date).weekday()
            code_l = inv.item_code.lower()
            if wd < 5 and ("saturday" in (catalogue.get(inv.item_code) or {}).get(
                    "name", "").lower() or "sunday" in (catalogue.get(inv.item_code) or {}).get("name", "").lower()):
                findings.append(Finding(
                    "R6 weekend item on weekday", "warning", inv.line,
                    f"weekend-loaded item {inv.item_code} delivered on a weekday "
                    f"({inv.service_date})", "Support Catalogue item name"))
        except ValueError:
            pass

        hit = sanctions.get(inv.provider_abn) or sanctions.get(norm_name(inv.provider_name))
        if hit:
            findings.append(Finding(
                "R7 sanctioned provider", "breach", inv.line,
                f"provider '{inv.provider_name}' matches enforcement register: {hit}",
                "NDIS Commission compliance register (data.gov.au)"))

    return findings


def load_invoices(path: str | Path) -> list[Invoice]:
    df = pd.read_csv(path)
    out = []
    for i, r in df.iterrows():
        out.append(Invoice(
            line=i + 1, participant=str(r.get("participant", "")),
            provider_name=str(r.get("provider_name", "")),
            provider_abn=str(r.get("provider_abn", "") or "").replace(" ", ""),
            item_code=str(r.get("item_code", "")), service_date=str(r.get("service_date", "")),
            claim_date=str(r.get("claim_date", "")), qty=float(r.get("qty", 1) or 1),
            unit_price=float(r.get("unit_price", 0) or 0), state=str(r.get("state", "NSW")),
            plan_start=str(r.get("plan_start", "") or ""), plan_end=str(r.get("plan_end", "") or ""),
            worker_id=str(r.get("worker_id", "") or ""), hours=float(r.get("hours", 0) or 0)))
    return out


def main(argv: list[str]) -> int:
    conn = connect()
    cat = catalogue_index(fetch_catalogue())
    print(f"catalogue: {len(cat)} support items")
    path = argv[0] if argv else "data/synthetic_invoices.csv"
    invoices = load_invoices(path)
    findings = screen(invoices, cat, sanctioned_providers(conn))
    print(f"{len(invoices)} invoice lines -> {len(findings)} findings")
    for f in findings:
        print(f"  [{f.severity:7}] L{f.invoice_line} {f.rule}: {f.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
