"""Generate a synthetic invoice batch seeding every detectable fraud typology.

Uses real support items and price caps from the catalogue, and a real sanctioned
provider name from the enforcement register (clearly marked as a simulation —
participants and other providers are fictional).

CLI: python -m app.synth
"""
from __future__ import annotations

import csv
from pathlib import Path

from .claims import catalogue_index, fetch_catalogue
from .db import connect

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic_invoices.csv"


def main() -> int:
    cat = catalogue_index(fetch_catalogue())
    # pick a common hourly item with NSW cap
    items = [(c, v) for c, v in cat.items() if v["caps"].get("NSW")]
    base_code, base = items[0]
    cap = base["caps"]["NSW"]
    sat = next(((c, v) for c, v in items if "saturday" in v["name"].lower()), (base_code, base))

    conn = connect()
    banned = conn.execute(
        "SELECT name, abn FROM actions WHERE type='ER - Banning Order' AND abn != '' "
        "ORDER BY date_from DESC LIMIT 1").fetchone()

    rows = [
        # clean lines
        dict(participant="P001", provider_name="Fictional Care Co", provider_abn="11111111111",
             item_code=base_code, service_date="2026-05-04", claim_date="2026-05-06",
             qty=2, unit_price=round(cap * 0.95, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31", worker_id="W1", hours=2),
        # R1 price-cap breach (+30%)
        dict(participant="P002", provider_name="Fictional Care Co", provider_abn="11111111111",
             item_code=base_code, service_date="2026-05-05", claim_date="2026-05-07",
             qty=1, unit_price=round(cap * 1.30, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31", worker_id="W1", hours=1),
        # R2 invalid item
        dict(participant="P003", provider_name="Fictional Care Co", provider_abn="11111111111",
             item_code="99_999_9999_9_9", service_date="2026-05-05", claim_date="2026-05-07",
             qty=1, unit_price=100, state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31"),
        # R3 duplicate (x2 identical)
        dict(participant="P004", provider_name="Dupe Services", provider_abn="22222222222",
             item_code=base_code, service_date="2026-05-08", claim_date="2026-05-09",
             qty=3, unit_price=round(cap * 0.9, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31"),
        dict(participant="P004", provider_name="Dupe Services", provider_abn="22222222222",
             item_code=base_code, service_date="2026-05-08", claim_date="2026-05-09",
             qty=3, unit_price=round(cap * 0.9, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31"),
        # R4 impossible day (3 x 9h same worker/day)
        *[dict(participant=f"P00{5 + i}", provider_name="Marathon Support",
               provider_abn="33333333333", item_code=base_code,
               service_date="2026-05-11", claim_date="2026-05-12", qty=9,
               unit_price=round(cap * 0.9, 2), state="NSW",
               plan_start="2026-01-01", plan_end="2026-12-31", worker_id="W9", hours=9)
          for i in range(3)],
        # R5 expired plan
        dict(participant="P008", provider_name="Fictional Care Co", provider_abn="11111111111",
             item_code=base_code, service_date="2026-05-20", claim_date="2026-05-21",
             qty=1, unit_price=round(cap * 0.9, 2), state="NSW",
             plan_start="2025-01-01", plan_end="2025-12-31"),
        # R8 advance claim
        dict(participant="P009", provider_name="Fictional Care Co", provider_abn="11111111111",
             item_code=base_code, service_date="2026-07-01", claim_date="2026-05-25",
             qty=1, unit_price=round(cap * 0.9, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31"),
        # R6 weekend item on a Tuesday
        dict(participant="P010", provider_name="Fictional Care Co", provider_abn="11111111111",
             item_code=sat[0], service_date="2026-05-05", claim_date="2026-05-07",
             qty=1, unit_price=round((sat[1]["caps"].get("NSW") or cap) * 0.9, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31"),
        # R7 sanctioned provider (real register entry, fictional invoice)
        dict(participant="P011", provider_name=banned["name"] if banned else "Banned Provider",
             provider_abn=banned["abn"] if banned else "", item_code=base_code,
             service_date="2026-05-12", claim_date="2026-05-13", qty=2,
             unit_price=round(cap * 0.9, 2), state="NSW",
             plan_start="2026-01-01", plan_end="2026-12-31"),
    ]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {len(rows)} synthetic invoice lines -> {OUT}")
    print(f"seeded: R1 cap-breach, R2 invalid item, R3 duplicate, R4 impossible day, "
          f"R5 expired plan, R6 weekend item, R7 sanctioned provider "
          f"({banned['name'] if banned else 'n/a'}), R8 advance claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
