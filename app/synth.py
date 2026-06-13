"""Generate a realistic synthetic invoice batch for the Claims lab.

Real claims data is private (it lives with plan managers). To prove the engine
works at scale this builds a plausible book of invoices — real Support Catalogue
items and price caps, many fictional providers/participants, a realistic ~8%
embedded fraud rate across all detectable typologies, plus a handful of lines
attributed to genuinely sanctioned providers (real names from the register,
fictional invoices, clearly a simulation).

Deterministic (seeded) so the demo is reproducible.

CLI: python -m app.synth [n_lines]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from .claims import catalogue_index, fetch_catalogue
from .db import connect

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic_invoices.csv"

# small deterministic PRNG (no Math.random / os randomness needed)
class Rng:
    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF

    def pick(self, seq):
        return seq[int(self.next() * len(seq)) % len(seq)]

    def chance(self, p: float) -> bool:
        return self.next() < p


PROVIDERS = [
    ("Brightside Supports", "51111000001"), ("Meridian Care Group", "51111000002"),
    ("Open Door Disability", "51111000003"), ("Anchor Community Services", "51111000004"),
    ("Northwind Allied Health", "51111000005"), ("Clearpath Support Co", "51111000006"),
    ("Harbour Lights Care", "51111000007"), ("Evergreen Participants", "51111000008"),
]
STATES = ["NSW", "VIC", "QLD", "WA", "SA"]
DAYS = [f"2026-05-{d:02d}" for d in range(1, 29)]


def main(argv: list[str]) -> int:
    n = int(argv[0]) if argv else 320
    rng = Rng(20260612)
    cat = catalogue_index(fetch_catalogue())
    priced = [(c, v) for c, v in cat.items()
              if v["caps"].get("NSW") and 20 < v["caps"]["NSW"] < 400]
    sat = next(((c, v) for c, v in priced if "saturday" in v["name"].lower()), priced[0])

    conn = connect()
    banned = [dict(r) for r in conn.execute(
        "SELECT name, abn FROM actions WHERE type='ER - Banning Order' AND abn != '' "
        "ORDER BY date_from DESC LIMIT 6")]

    rows = []
    seen_dupe_key = None
    for i in range(n):
        prov = rng.pick(PROVIDERS)
        state = rng.pick(STATES)
        code, item = rng.pick(priced)
        cap = item["caps"].get(state) or item["caps"]["NSW"]
        day = rng.pick(DAYS)
        qty = rng.pick([1, 1, 2, 2, 3, 4])
        worker = f"W{int(rng.next() * 40) + 1}"
        row = dict(
            participant=f"P{int(rng.next() * 800) + 1:04d}",
            provider_name=prov[0], provider_abn=prov[1], item_code=code,
            service_date=day, claim_date="2026-05-29", qty=qty,
            unit_price=round(cap * (0.88 + rng.next() * 0.1), 2), state=state,
            plan_start="2026-01-01", plan_end="2026-12-31",
            worker_id=worker, hours=qty)

        # inject fraud at ~8%
        r = rng.next()
        if r < 0.020:  # price-cap breach
            row["unit_price"] = round(cap * (1.15 + rng.next() * 0.5), 2)
        elif r < 0.032:  # invalid item
            row["item_code"] = "99_999_9999_9_9"
        elif r < 0.044:  # expired plan
            row["plan_start"], row["plan_end"] = "2024-01-01", "2024-12-31"
        elif r < 0.056:  # advance claim
            row["service_date"] = "2026-08-15"
        elif r < 0.066:  # weekend item on a weekday
            row["item_code"] = sat[0]
            row["unit_price"] = round((sat[1]["caps"].get(state) or cap) * 0.9, 2)
        elif r < 0.074 and banned:  # sanctioned provider (real name, fictional invoice)
            b = rng.pick(banned)
            row["provider_name"], row["provider_abn"] = b["name"], b["abn"]
        elif r < 0.080:  # duplicate — emit twice
            rows.append(dict(row))

        rows.append(row)

    # one guaranteed impossible-day cluster (same worker, same day, >24h)
    for k in range(4):
        rows.append(dict(
            participant=f"P09{k:02d}", provider_name="Marathon Support",
            provider_abn="51111000099", item_code=priced[0][0],
            service_date="2026-05-11", claim_date="2026-05-12", qty=9,
            unit_price=round(priced[0][1]["caps"]["NSW"] * 0.9, 2), state="NSW",
            plan_start="2026-01-01", plan_end="2026-12-31", worker_id="W99", hours=9))

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"wrote {len(rows)} invoice lines across {len(PROVIDERS) + 1} providers -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
