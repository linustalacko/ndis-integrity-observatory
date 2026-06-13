"""Load NDIA active-provider counts and market concentration into SQLite.

Source: dataresearch.ndis.gov.au provider datasets (committed under data/market/).

CLI: python -m app.market_ingest
"""
from __future__ import annotations

import csv
import glob
import os
import re
from pathlib import Path

from .db import connect

MARKET_DIR = Path(__file__).resolve().parent.parent / "data" / "market"

PAY_BAND = re.compile(r"([\d.]+)\s*([mb])?\s*-\s*([\d.]+)\s*([mb])?", re.I)


def parse_band(text: str) -> tuple[float | None, float | None]:
    """'200m - 300m' -> (2e8, 3e8); '> 4b' / '< 1m' handled."""
    t = text.strip().lower()
    mult = {"m": 1e6, "b": 1e9, "": 1e6}
    if t.startswith(">"):
        m = re.search(r"([\d.]+)\s*([mb])?", t)
        if m:
            return float(m.group(1)) * mult[m.group(2) or "m"], None
    if t.startswith("<"):
        m = re.search(r"([\d.]+)\s*([mb])?", t)
        if m:
            return None, float(m.group(1)) * mult[m.group(2) or "m"]
    m = PAY_BAND.search(t)
    if not m:
        return None, None
    lo = float(m.group(1)) * mult[(m.group(2) or m.group(4) or "m").lower()]
    hi = float(m.group(3)) * mult[(m.group(4) or "m").lower()]
    return lo, hi


def load_providers(conn) -> int:
    n = 0
    for f in sorted(glob.glob(str(MARKET_DIR / "providers_*.csv"))):
        quarter = os.path.basename(f).replace("providers_", "").replace(".csv", "")
        rows = list(csv.reader(open(f, encoding="utf-8-sig")))
        header = rows[0]
        # expected: RprtDt, StateCd, SrvcDstrctNm, DsbltyGrpNm, AgeBnd, SuppClass, PrvdrCnt
        if header[:6] != ["RprtDt", "StateCd", "SrvcDstrctNm", "DsbltyGrpNm",
                          "AgeBnd", "SuppClass"]:
            continue  # 2024-06 file has a different schema; skip
        for r in rows[1:]:
            # keep the district-level totals across disability/age, per support class
            if r[3] != "ALL" or r[4] != "ALL":
                continue
            try:
                cnt = int(r[6])
            except (ValueError, IndexError):
                continue
            conn.execute(
                "INSERT OR REPLACE INTO provider_counts "
                "(quarter, state, district, support_class, provider_count) "
                "VALUES (?,?,?,?,?)", (quarter, r[1], r[2], r[5], cnt))
            n += 1
    conn.commit()
    return n


def load_concentration(conn) -> int:
    f = MARKET_DIR / "market_concentration.csv"
    if not f.exists():
        return 0
    rows = list(csv.reader(open(f, encoding="utf-8-sig")))
    n = 0
    for r in rows[1:]:
        dt = r[0]  # e.g. 31MAR2026
        m = re.match(r"(\d{2})([A-Z]{3})(\d{4})", dt)
        months = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05",
                  "JUN": "06", "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10",
                  "NOV": "11", "DEC": "12"}
        quarter = f"{m.group(3)}-{months[m.group(2)]}-{m.group(1)}" if m else dt
        share = None
        if r[4] and r[4].strip().endswith("%"):
            share = float(r[4].strip().rstrip("%")) / 100
        lo, hi = parse_band(r[5])
        district = r[2].split("~")[0].strip()  # 'Brimbank Melton~VIC' -> 'Brimbank Melton'
        conn.execute(
            "INSERT OR REPLACE INTO market_concentration "
            "(quarter, state, district, support_class, top10_share, payment_low, "
            "payment_high) VALUES (?,?,?,?,?,?,?)",
            (quarter, r[1], district, r[3], share, lo, hi))
        n += 1
    conn.commit()
    return n


def main() -> int:
    conn = connect()
    p = load_providers(conn)
    c = load_concentration(conn)
    print(f"loaded {p} provider-count rows, {c} concentration rows")
    quarters = [r["quarter"] for r in conn.execute(
        "SELECT DISTINCT quarter FROM provider_counts ORDER BY 1")]
    print("quarters:", quarters)
    nat = conn.execute(
        "SELECT quarter, provider_count FROM provider_counts "
        "WHERE state='ALL' AND district='ALL' AND support_class='ALL' ORDER BY quarter")
    print("national ALL providers:", [(r["quarter"], r["provider_count"]) for r in nat])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
