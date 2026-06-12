"""M0: Register time machine.

Discovers every 'NDIS Commission Compliance Actions' snapshot on data.gov.au,
downloads the CSVs, and folds them into a deduplicated actions table with
first_seen / last_seen snapshot dates.

CLI: python -m app.ingest
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import sys

import httpx

from .db import connect

CKAN = "https://data.gov.au/data/api/3/action/package_search"
QUERY = '"NDIS Commission Compliance Actions"'

# Title like 'NDIS Commission Compliance Actions - 04.06.2026'
DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")

ORG_TOKENS = re.compile(
    r"\b(pty|ltd|limited|inc|incorporated|group|services?|care|australia|"
    r"company|co|corp|trust|foundation|association|disability|support)\b", re.I)


def norm_name(name: str) -> str:
    """Normalise for matching: uppercase, 'SURNAME, First' -> 'FIRST SURNAME',
    strip punctuation and whitespace runs."""
    n = name.strip()
    if "," in n and not ORG_TOKENS.search(n):
        last, _, first = n.partition(",")
        n = f"{first.strip()} {last.strip()}"
    n = re.sub(r"[^\w\s]", " ", n.upper())
    return re.sub(r"\s+", " ", n).strip()


def looks_person(name: str) -> bool:
    return ("," in name or len(name.split()) <= 4) and not ORG_TOKENS.search(name)


def discover() -> list[tuple[str, str, str]]:
    """Return [(snapshot_date_iso, title, csv_url)] sorted by date."""
    r = httpx.get(CKAN, params={"q": QUERY, "rows": 200}, timeout=60)
    r.raise_for_status()
    out = []
    for pkg in r.json()["result"]["results"]:
        if "compliance actions" not in pkg["title"].lower():
            continue
        m = DATE_RE.search(pkg["title"])
        if not m:
            continue
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        for res in pkg.get("resources", []):
            if res["format"].upper() == "CSV":
                out.append((date, pkg["title"], res["url"]))
                break
    # dedupe by date (CKAN can list a snapshot twice)
    seen, uniq = set(), []
    for d, t, u in sorted(out):
        if d not in seen:
            seen.add(d)
            uniq.append((d, t, u))
    return uniq


def parse_date(value: str) -> str:
    """Normalise the register's two date formats to an ISO date.

    '24/01/2024 18:00' (local) and '2024-01-24T07:00:00' (UTC) refer to the
    same day; we keep the date component only.
    """
    v = (value or "").strip()
    if not v:
        return ""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", v)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
    return m.group(1) if m else v


def action_id(row: dict) -> str:
    key = "|".join([row.get("Type", ""), row.get("Name", "").strip().upper(),
                    parse_date(row.get("Date effective from", ""))])
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def ingest_snapshot(conn, date: str, title: str, url: str) -> int:
    text = httpx.get(url, timeout=120, follow_redirects=True).text
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
    for row in rows:
        aid = action_id(row)
        name = row.get("Name", "").strip()
        cur = conn.execute("SELECT first_seen, last_seen FROM actions WHERE action_id=?",
                           (aid,)).fetchone()
        if cur:
            conn.execute(
                "UPDATE actions SET first_seen=MIN(first_seen,?), last_seen=MAX(last_seen,?), "
                "date_to=?, detail=? WHERE action_id=?",
                (date, date, parse_date(row.get("Date no longer in force", "")),
                 row.get("Relevant information", ""), aid))
        else:
            conn.execute(
                "INSERT INTO actions (action_id, type, name, abn, city, state, postcode, "
                "provider_number, date_from, date_to, registration_groups, detail, "
                "first_seen, last_seen, is_person, norm_name) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (aid, row.get("Type", ""), name,
                 re.sub(r"\D", "", row.get("ABN", "") or ""),
                 row.get("City", ""), row.get("State", ""), row.get("Postcode", ""),
                 row.get("Provider Number", ""), parse_date(row.get("Date effective from", "")),
                 parse_date(row.get("Date no longer in force", "")),
                 row.get("Registration Groups", ""), row.get("Relevant information", ""),
                 date, date, int(looks_person(name)), norm_name(name)))
    conn.execute("INSERT OR REPLACE INTO snapshots (snapshot_date, dataset_title, url, "
                 "record_count) VALUES (?,?,?,?)", (date, title, url, len(rows)))
    conn.commit()
    return len(rows)


def main() -> int:
    conn = connect()
    snaps = discover()
    print(f"{len(snaps)} snapshots discovered")
    for date, title, url in snaps:
        n = ingest_snapshot(conn, date, title, url)
        print(f"  {date}: {n} records")
    total = conn.execute("SELECT COUNT(*) c FROM actions").fetchone()["c"]
    by_type = conn.execute(
        "SELECT type, COUNT(*) c FROM actions GROUP BY type ORDER BY c DESC").fetchall()
    print(f"\n{total} unique actions across all snapshots:")
    for r in by_type:
        print(f"  {r['type']}: {r['c']}")
    # The time-machine payoff: actions that appeared/disappeared between snapshots
    new_last = conn.execute(
        "SELECT COUNT(*) c FROM actions WHERE first_seen = (SELECT MAX(snapshot_date) FROM snapshots)"
    ).fetchone()["c"]
    gone = conn.execute(
        "SELECT COUNT(*) c FROM actions WHERE last_seen < (SELECT MAX(snapshot_date) FROM snapshots)"
    ).fetchone()["c"]
    print(f"\nnew in latest snapshot: {new_last} | dropped from register since first appearance: {gone}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
