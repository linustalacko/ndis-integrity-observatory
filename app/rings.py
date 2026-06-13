"""Entity-network detection — syndicate signatures from public data.

The public ABN extract gives state + postcode (not street address), so we detect
the two network patterns that ARE visible and that the case law shows matter:

  multi-ABN operators  one sanctioned person linked to several active ABNs — the
                       "one operator, 50 ABNs" syndicate signature.
  family / associate   2+ distinct sanctioned people sharing a surname AND a
  clusters             postcode — the family-network signature (e.g. two brothers
                       both permanently banned at one address, each with an ABN).

Leads to verify, not proof. Shared surname+postcode can be coincidence.

CLI: python -m app.rings
"""
from __future__ import annotations

import json

from .db import connect


def multi_abn_operators(conn, min_abns: int = 2) -> list[dict]:
    # Only count confidence-scored links (exact-ABN or rare-name); common-name
    # collisions ('Muhammad Ali' -> 219 ABNs) are excluded by the tier filter.
    rows = conn.execute("""
        SELECT a.name, a.type, a.date_from, a.state, a.postcode,
               COUNT(DISTINCT m.abn) n_abns,
               SUM(CASE WHEN m.post_ban_registration=1 THEN 1 ELSE 0 END) n_post_ban,
               GROUP_CONCAT(DISTINCT m.abn) abns
        FROM actions a JOIN matches m USING(action_id)
        WHERE a.is_person=1 AND m.tier IN ('high','medium')
        GROUP BY a.action_id HAVING n_abns >= ?
        ORDER BY n_abns DESC, n_post_ban DESC""", (min_abns,)).fetchall()
    out = []
    for r in rows:
        sanctioned = r["type"] in (
            "ER - Banning Order", "ER - Revocation of registration",
            "ER - Suspension of registration", "ER - Refusal to re-register")
        out.append({
            "name": r["name"], "type": r["type"], "date_from": r["date_from"],
            "state": r["state"], "postcode": r["postcode"],
            "n_abns": r["n_abns"], "n_post_ban": r["n_post_ban"],
            "abns": (r["abns"] or "").split(","), "sanctioned": sanctioned,
        })
    return out


def surname(norm_name: str) -> str:
    toks = norm_name.split()
    return toks[-1] if toks else ""


def family_clusters(conn) -> list[dict]:
    """2+ distinct people sharing surname + postcode, ≥1 under a sanction."""
    people = conn.execute(
        "SELECT action_id, name, norm_name, type, postcode, state, date_from "
        "FROM actions WHERE is_person=1 AND postcode != ''").fetchall()
    groups: dict[tuple, list] = {}
    for p in people:
        key = (surname(p["norm_name"]), p["postcode"])
        if not key[0] or len(key[0]) < 3:
            continue
        groups.setdefault(key, []).append(p)
    SANCTIONS = ("ER - Banning Order", "ER - Revocation of registration",
                 "ER - Suspension of registration", "ER - Refusal to re-register")
    out = []
    for (sname, pc), members in groups.items():
        names = {m["norm_name"] for m in members}
        # collapse near-duplicate parses ('ASHPREET KAUR' vs 'ASHPREET KAUR ASHPREET
        # KAUR') — keep only names that aren't a superset of a shorter member name
        distinct = {n for n in names
                    if not any(o != n and o in n for o in names)}
        if len(distinct) < 2:
            continue
        sanctioned = [m for m in members if m["type"] in SANCTIONS]
        if not sanctioned:
            continue
        keep = [m for m in members if m["norm_name"] in distinct]
        out.append({
            "surname": sname, "postcode": pc, "state": members[0]["state"],
            "people": sorted(distinct), "n_people": len(distinct),
            "n_sanctioned": len({m["norm_name"] for m in sanctioned
                                 if m["norm_name"] in distinct}),
            "members": [{"name": m["name"], "type": m["type"], "date_from": m["date_from"]}
                        for m in keep],
        })
    return sorted(out, key=lambda x: (-x["n_sanctioned"], -x["n_people"]))


def persist(conn) -> None:
    conn.execute("DELETE FROM rings")
    for i, op in enumerate(multi_abn_operators(conn, 2)):
        conn.execute(
            "INSERT OR REPLACE INTO rings (ring_id, address_key, state, postcode, "
            "abn_count, sanctioned_count, abns, score) VALUES (?,?,?,?,?,?,?,?)",
            (f"op{i}", op["name"], op["state"], op["postcode"], op["n_abns"],
             1 if op["sanctioned"] else 0, json.dumps(op["abns"]),
             op["n_abns"] * 10 + op["n_post_ban"] * 20))
    conn.commit()


def main() -> int:
    conn = connect()
    ops = multi_abn_operators(conn, 3)
    print(f"operators linked to 3+ ABNs: {len(ops)}")
    for o in ops[:12]:
        flag = " [SANCTIONED]" if o["sanctioned"] else ""
        print(f"  {o['name'][:32]:32} {o['n_abns']} ABNs "
              f"({o['n_post_ban']} post-ban){flag}  {o['state']} {o['postcode']}")
    fam = family_clusters(conn)
    print(f"\nfamily/associate clusters (surname+postcode, ≥1 sanctioned): {len(fam)}")
    for c in fam[:12]:
        print(f"  {c['surname']} @ {c['postcode']} {c['state']}: {c['n_people']} people, "
              f"{c['n_sanctioned']} sanctioned — {', '.join(c['people'])[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
