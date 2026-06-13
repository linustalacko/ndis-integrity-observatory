"""Crowd-sourced fraud registry — build provider-level reports from a screened
batch, gate on detection, persist to the shared table.
"""
from __future__ import annotations

import hashlib
import json

from .claims import Finding, Invoice
from .ingest import norm_name


def _service_categories(invoices: list[Invoice], provider: str) -> str:
    """Coarse support category from item code prefix (e.g. '01' = assistance daily)."""
    prefixes = {inv.item_code.split("_")[0] for inv in invoices
                if inv.provider_name == provider and inv.item_code}
    names = {"01": "Daily living", "02": "Transport", "03": "Consumables",
             "04": "Social & community", "05": "Capital/AT", "06": "Coordination",
             "07": "Coordination", "08": "Living arrangements", "09": "Home mods",
             "10": "Therapeutic", "11": "Behaviour", "12": "Group", "13": "Plan mgmt",
             "14": "Employment", "15": "Capacity building", "16": "Daily activity",
             "17": "Health & wellbeing", "18": "Lifelong learning", "99": "Unknown/invalid"}
    return ", ".join(sorted({names.get(p, p) for p in prefixes})) or "—"


def build_reports(invoices: list[Invoice], findings: list[Finding],
                  sanctions: dict, source: str = "csv") -> list[dict]:
    """One report per provider that has at least one breach."""
    by_provider: dict[str, list[Finding]] = {}
    for f in findings:
        if f.severity == "breach":
            by_provider.setdefault(f.provider, []).append(f)

    reports = []
    for provider, fs in by_provider.items():
        prov_inv = [i for i in invoices if i.provider_name == provider]
        billed = sum(i.unit_price * i.qty for i in prov_inv)
        abn = next((i.provider_abn for i in prov_inv if i.provider_abn), "")
        state = next((i.state for i in prov_inv if i.state), "")
        sanction = sanctions.get(abn) or sanctions.get(norm_name(provider)) or ""
        rid = hashlib.sha1(f"{provider}|{source}|{billed}".encode()).hexdigest()[:12]
        reports.append({
            "report_id": rid, "provider_name": provider, "provider_abn": abn,
            "state": state, "postcode": "", "city": "",
            "services": _service_categories(invoices, provider),
            "billed": round(billed, 2), "at_risk": round(sum(f.at_risk for f in fs), 2),
            "n_breaches": len(fs), "rules": sorted({f.rule.split(" ", 1)[0] for f in fs}),
            "findings": [{"line": f.invoice_line, "rule": f.rule, "detail": f.detail,
                          "at_risk": f.at_risk} for f in fs],
            "source": source, "already_sanctioned": sanction,
        })
    return sorted(reports, key=lambda r: -r["at_risk"])


def submit(conn, reports: list[dict]) -> int:
    for r in reports:
        conn.execute(
            "INSERT OR REPLACE INTO reports (report_id, provider_name, provider_abn, "
            "state, postcode, city, services, billed, at_risk, n_breaches, rules, "
            "findings, source, already_sanctioned) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["report_id"], r["provider_name"], r["provider_abn"], r["state"],
             r.get("postcode", ""), r.get("city", ""), r["services"], r["billed"],
             r["at_risk"], r["n_breaches"], json.dumps(r["rules"]),
             json.dumps(r["findings"]), r["source"], r["already_sanctioned"]))
    conn.commit()
    return len(reports)


def listing(conn) -> dict:
    rows = []
    for r in conn.execute("SELECT * FROM reports ORDER BY at_risk DESC"):
        d = dict(r)
        d["rules"] = json.loads(d["rules"] or "[]")
        d["findings"] = json.loads(d["findings"] or "[]")
        rows.append(d)
    total = sum(r["at_risk"] for r in rows)
    return {
        "reports": rows,
        "total_at_risk": round(total, 2),
        "count": len(rows),
        "providers": len({r["provider_name"] for r in rows}),
        "sanctioned": sum(1 for r in rows if r["already_sanctioned"]),
    }
