"""Dollar value of NDIS fraud, from public data.

Two layers, kept clearly separate:
  - SYSTEMIC: the NDIA/ANAO published estimate of annual leakage (a reference
    band, not something we computed).
  - CASES: real charged / alleged / sentenced / seized amounts extracted from
    Fraud Fusion Taskforce (AFP) media releases, dated, each linking its source.

Nothing here is undetected live fraud — that only becomes visible with claims
data (see the Claims lab). This is the value the system has *surfaced or that is
being prosecuted*, on a timeline.

CLI: python -m app.money
"""
from __future__ import annotations

import re

from .db import connect

AMOUNT = re.compile(r'\$\s?([\d,]+(?:\.\d+)?)\s?(billion|million|m\b|bn|k\b|thousand)?', re.I)

# Annual systemic estimate (NDIA / ANAO Report 48, 2024-25): 6-10% of ~$42B outlays.
SYSTEMIC = {
    "label": "NDIA estimate of non-compliant / fraudulent payments",
    "low": 2.5e9,
    "high": 4.2e9,
    "basis": "6–10% of ~$42B in annual NDIS outlays",
    "source": "NDIA; ANAO Report 48 (2024–25)",
}


def to_aud(num: str, unit: str | None) -> float:
    n = float(num.replace(",", ""))
    u = (unit or "").lower().strip()
    if u in ("billion", "bn"):
        return n * 1e9
    if u in ("million", "m"):
        return n * 1e6
    if u in ("k", "thousand"):
        return n * 1e3
    return n


def classify(text: str) -> str:
    t = text.lower()
    if "sentenc" in t or "jail" in t or "guilty" in t:
        return "sentenced"
    if "seiz" in t:
        return "seized"
    if "charged" in t or "arrest" in t:
        return "charged"
    return "alleged"


def case_amounts() -> list[dict]:
    """One headline amount per AFP article, taken from the title where possible."""
    conn = connect()
    out = []
    for a in conn.execute("SELECT url, published, title, body FROM articles "
                          "WHERE source='afp' ORDER BY published"):
        blob = (a["title"] + " " + a["body"][:1200]).lower()
        if "ndis" not in blob and "disability insurance" not in blob:
            continue  # AFP search returns non-NDIS stories; keep only NDIS fraud
        m = AMOUNT.search(a["title"])
        src_text = a["title"]
        if not m:  # fall back to the largest figure in the body
            cands = [(to_aud(g.group(1), g.group(2)), g) for g in AMOUNT.finditer(a["body"])]
            if not cands:
                continue
            amount, g = max(cands, key=lambda x: x[0])
            src_text = a["body"]
        else:
            amount = to_aud(m.group(1), m.group(2))
        if amount < 10000:  # skip incidental small figures
            continue
        out.append({
            "date": a["published"], "amount": amount, "title": a["title"],
            "kind": classify(a["title"] + " " + a["body"][:400]), "url": a["url"],
        })
    return out


def summary() -> dict:
    cases = case_amounts()
    total = sum(c["amount"] for c in cases)
    by_kind: dict[str, float] = {}
    for c in cases:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + c["amount"]
    return {"systemic": SYSTEMIC, "cases": cases, "case_total": total,
            "by_kind": by_kind, "case_count": len(cases)}


def main() -> int:
    s = summary()
    print(f"systemic estimate: ${s['systemic']['low']/1e9:.1f}–{s['systemic']['high']/1e9:.1f}B/yr")
    print(f"\n{s['case_count']} prosecuted/charged cases, total ${s['case_total']/1e6:.1f}M:")
    for c in sorted(s["cases"], key=lambda x: -x["amount"]):
        print(f"  {c['date']}  ${c['amount']/1e6:7.2f}M  [{c['kind']:9}] {c['title'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
