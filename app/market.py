"""M2b: Market data — quarterly active-provider aggregates from dataresearch.ndis.gov.au.

Pulls the Active Providers CSV (count of active providers by quarter, state,
support class, registration status etc.) and stores it for anomaly charts.

CLI: python -m app.market
"""
from __future__ import annotations

import io
import sys

import httpx
import pandas as pd

from .db import DB_PATH

# Active providers quarterly CSV (provider counts; latest snapshot includes history)
ACTIVE_PROVIDERS_URLS = [
    # discovered via dataresearch.ndis.gov.au "Provider datasets" page
    "https://dataresearch.ndis.gov.au/media/4156/download",  # rotated ids; try several
    "https://dataresearch.ndis.gov.au/media/4106/download",
]
PAGE = "https://dataresearch.ndis.gov.au/datasets/provider-datasets"


def discover_csv_url() -> str | None:
    """Scrape the provider datasets page for the Active providers CSV link."""
    try:
        html = httpx.get(PAGE, timeout=60, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"}).text
    except Exception:
        return None
    import re
    # links look like /media/<id>/download with surrounding 'Active providers' text
    for m in re.finditer(r'href="(/media/\d+/download[^"]*)"', html):
        return "https://dataresearch.ndis.gov.au" + m.group(1)
    return None


def load() -> pd.DataFrame | None:
    urls = []
    u = discover_csv_url()
    if u:
        urls.append(u)
    urls += ACTIVE_PROVIDERS_URLS
    for url in urls:
        try:
            r = httpx.get(url, timeout=120, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and (b"," in r.content[:200]):
                df = pd.read_csv(io.BytesIO(r.content))
                if len(df.columns) >= 3:
                    return df
        except Exception:
            continue
    return None


def main() -> int:
    df = load()
    if df is None:
        print("could not fetch active providers CSV (page layout may have changed)",
              file=sys.stderr)
        return 1
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("market_active_providers", conn, if_exists="replace", index=False)
    print(f"loaded {len(df)} rows, columns: {list(df.columns)[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
