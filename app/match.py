"""M1b: Phoenix detector — link enforcement entities to ABNs and flag risk patterns.

Match tiers (all stored with confidence score):
- exact-abn:   register row carries the ABN
- exact-name:  normalised name equality
- fuzzy-name:  rapidfuzz token_sort_ratio >= 90 within same state (or no state)

Phoenix flag: matched ABN whose status-from date is AFTER the ban/revocation
effective date — i.e. an entity that became active after the subject was
sanctioned. These are published as questions, not assertions.

CLI: python -m app.match
"""
from __future__ import annotations

import sys

from rapidfuzz import fuzz, process

from .db import connect

SANCTION_TYPES = ("ER - Banning Order", "ER - Revocation of registration",
                  "ER - Refusal to re-register", "ER - Suspension of registration")


def iso(abr_date: str) -> str:
    """ABR dates are yyyymmdd; normalise to ISO for comparison."""
    d = (abr_date or "").strip()
    if len(d) == 8 and d.isdigit():
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return d


def run(conn) -> dict:
    conn.execute("DELETE FROM matches")
    abn_rows = conn.execute("SELECT * FROM abns WHERE norm_name != ''").fetchall()
    by_norm: dict[str, list] = {}
    for a in abn_rows:
        by_norm.setdefault(a["norm_name"], []).append(a)
    choices = list(by_norm.keys())

    stats = {"exact-abn": 0, "exact-name": 0, "fuzzy-name": 0, "phoenix": 0}
    actions = conn.execute("SELECT * FROM actions").fetchall()
    for act in actions:
        seen_abns = set()

        def add(abn_row, mtype, score):
            if abn_row["abn"] in seen_abns:
                return
            seen_abns.add(abn_row["abn"])
            post_ban = 0
            if (act["type"] in SANCTION_TYPES and act["date_from"]
                    and abn_row["status_date"] and abn_row["abn_status"] == "ACT"
                    and iso(abn_row["status_date"]) > act["date_from"]):
                post_ban = 1
                stats["phoenix"] += 1
            conn.execute(
                "INSERT OR REPLACE INTO matches (action_id, abn, match_type, score, "
                "post_ban_registration, note) VALUES (?,?,?,?,?,?)",
                (act["action_id"], abn_row["abn"], mtype, score, post_ban,
                 f"{abn_row['legal_name']} | {abn_row['abn_status']} from "
                 f"{iso(abn_row['status_date'])} | {abn_row['state']} {abn_row['postcode']}"))
            stats[mtype] += 1

        if act["abn"]:
            row = conn.execute("SELECT * FROM abns WHERE abn=?", (act["abn"],)).fetchone()
            if row:
                add(row, "exact-abn", 100.0)
        for a in by_norm.get(act["norm_name"], []):
            add(a, "exact-name", 100.0)
        # fuzzy pass only for persons (orgs share too much boilerplate vocabulary)
        if act["is_person"] and act["norm_name"]:
            for cand, score, _ in process.extract(
                    act["norm_name"], choices, scorer=fuzz.token_sort_ratio, limit=5):
                if score >= 90 and cand != act["norm_name"]:
                    for a in by_norm[cand]:
                        if not act["state"] or not a["state"] or a["state"] == act["state"]:
                            add(a, "fuzzy-name", float(score))
    conn.commit()
    return stats


def main() -> int:
    conn = connect()
    stats = run(conn)
    print("match stats:", stats)
    rows = conn.execute("""
        SELECT a.name, a.type, a.date_from, m.abn, m.note, m.match_type, m.score
        FROM matches m JOIN actions a USING(action_id)
        WHERE m.post_ban_registration = 1 ORDER BY a.date_from DESC LIMIT 15""").fetchall()
    print(f"\ntop post-sanction active-ABN candidates ({len(rows)} shown):")
    for r in rows:
        print(f"  {r['name'][:35]} [{r['type'][5:]} {r['date_from']}] -> "
              f"ABN {r['abn']} ({r['match_type']} {r['score']:.0f}) {r['note'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
