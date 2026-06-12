"""Phoenix confidence scoring.

Turns raw name/ABN matches into a calibrated confidence so common-name
collisions ('Muhammad Ali', 219 namesakes) rank far below rare-name,
same-location, post-ban registrations ('MADUT', 2 namesakes, same suburb).

Signals:
  match_type   exact-abn is near-certain (the register named that ABN);
               name matches depend entirely on rarity.
  name rarity  count of ABR entries sharing the normalised name — the
               collision prior. Rare name + post-ban ABN = suspicious.
  geography    ABN registered in the same postcode / state as the sanctioned
               entity raises confidence; a different state lowers it.

Confidence is published as a tier (high / medium / low). Nothing here proves
fraud — it ranks which leads a human should verify first.

CLI: python -m app.score
"""
from __future__ import annotations

import sqlite3

from .db import connect

EXTRA_COLS = {"confidence": "REAL", "tier": "TEXT", "name_freq": "INTEGER",
              "geo": "TEXT"}


def _ensure_columns(conn: sqlite3.Connection) -> None:
    have = {r["name"] for r in conn.execute("PRAGMA table_info(matches)")}
    for col, typ in EXTRA_COLS.items():
        if col not in have:
            conn.execute(f"ALTER TABLE matches ADD COLUMN {col} {typ}")


def confidence(match_type: str, name_freq: int, geo: str, is_person: int) -> float:
    if match_type == "exact-abn":
        base = 90.0
    else:
        # name-based: rarity dominates
        if name_freq <= 1:
            base = 68.0
        elif name_freq == 2:
            base = 54.0
        elif name_freq <= 5:
            base = 38.0
        elif name_freq <= 20:
            base = 18.0
        else:
            base = 6.0
        if match_type == "fuzzy-name":
            base *= 0.7
    if geo == "postcode":
        base += 15
    elif geo == "state":
        base += 8
    elif geo == "interstate":
        base -= 8
    # organisation name matches are more reliable than personal ones
    if not is_person and match_type == "exact-name":
        base += 6
    return max(1.0, min(99.0, base))


def tier(score: float) -> str:
    return "high" if score >= 68 else ("medium" if score >= 38 else "low")


def run(conn: sqlite3.Connection) -> dict:
    _ensure_columns(conn)
    # name frequency across the matched ABR slice
    freq = {r["norm_name"]: r["c"] for r in conn.execute(
        "SELECT norm_name, COUNT(*) c FROM abns GROUP BY norm_name")}
    rows = conn.execute("""
        SELECT m.action_id, m.abn, m.match_type, m.post_ban_registration,
               a.norm_name, a.state act_state, a.postcode act_pc, a.is_person,
               b.state abn_state, b.postcode abn_pc
        FROM matches m
        JOIN actions a USING(action_id)
        LEFT JOIN abns b ON b.abn = m.abn""").fetchall()
    counts = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        nf = freq.get(r["norm_name"], 1)
        if r["act_pc"] and r["abn_pc"] and r["act_pc"] == r["abn_pc"]:
            geo = "postcode"
        elif r["act_state"] and r["abn_state"] and r["act_state"] == r["abn_state"]:
            geo = "state"
        elif r["act_state"] and r["abn_state"]:
            geo = "interstate"
        else:
            geo = "unknown"
        score = confidence(r["match_type"], nf, geo, r["is_person"])
        t = tier(score)
        conn.execute("UPDATE matches SET confidence=?, tier=?, name_freq=?, geo=? "
                     "WHERE action_id=? AND abn=?",
                     (round(score, 1), t, nf, geo, r["action_id"], r["abn"]))
        if r["post_ban_registration"]:
            counts[t] += 1
    conn.commit()
    return counts


def main() -> int:
    conn = connect()
    counts = run(conn)
    print("post-sanction candidates by confidence tier:", counts)
    print("\nhighest-confidence phoenix leads:")
    for r in conn.execute("""
            SELECT a.name, a.type, a.date_from, a.state, m.abn, m.confidence,
                   m.name_freq, m.geo, m.note
            FROM matches m JOIN actions a USING(action_id)
            WHERE m.post_ban_registration=1 AND m.tier='high'
            ORDER BY m.confidence DESC, a.date_from DESC LIMIT 15"""):
        print(f"  {r['confidence']:4.0f} {r['name'][:28]:28} [{r['type'][5:]} "
              f"{r['date_from']}] ABN {r['abn']} (namesakes:{r['name_freq']}, "
              f"geo:{r['geo']}) {r['note'][:45]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
