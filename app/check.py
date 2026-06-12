"""Provider Check — the Phase 2 API hook.

Given a provider name or ABN, return a structured integrity verdict from the
enforcement register and the phoenix graph. This is what a plan manager would
call before paying an invoice. Pure lookup over the public data already loaded.

CLI: python -m app.check "Touch & Care"  |  python -m app.check 27697188444
"""
from __future__ import annotations

import json
import sys

from .db import connect
from .ingest import norm_name

ACTIVE_SANCTIONS = ("ER - Banning Order", "ER - Revocation of registration",
                    "ER - Suspension of registration", "ER - Refusal to re-register")


def check(query: str) -> dict:
    conn = connect()
    digits = "".join(c for c in query if c.isdigit())
    nn = norm_name(query)

    if len(digits) == 11:
        actions = conn.execute(
            "SELECT * FROM actions WHERE abn=? ORDER BY date_from DESC", (digits,)).fetchall()
    else:
        actions = conn.execute(
            "SELECT * FROM actions WHERE norm_name=? OR name LIKE ? ORDER BY date_from DESC",
            (nn, f"%{query}%")).fetchall()

    sanctions = [a for a in actions if a["type"] in ACTIVE_SANCTIONS]
    notices = [a for a in actions if a["type"] == "ER - Compliance notice"]

    # phoenix links: ABNs that activated after a sanction against THIS entity.
    # Match on the entity's own action ids, not a bare ABN string (empty ABN
    # would otherwise match every register row with a blank ABN).
    action_ids = [a["action_id"] for a in actions]
    phoenix = []
    if action_ids:
        ph = ",".join("?" * len(action_ids))
        phoenix = conn.execute(f"""
            SELECT m.abn, m.confidence, m.tier, m.name_freq, m.geo, m.note, a.name,
                   a.type, a.date_from
            FROM matches m JOIN actions a USING(action_id)
            WHERE m.post_ban_registration=1 AND m.action_id IN ({ph})
            ORDER BY m.confidence DESC""", action_ids).fetchall()

    if any("permanent" in (a["detail"] or "").lower() for a in sanctions):
        verdict, risk = "DO NOT ENGAGE — permanent sanction on record", "critical"
    elif sanctions:
        verdict, risk = "SANCTIONED — active banning/revocation on record", "critical"
    elif notices:
        verdict, risk = "CAUTION — compliance notice(s) on record", "elevated"
    elif phoenix:
        verdict, risk = "REVIEW — linked to a post-sanction ABN", "elevated"
    else:
        verdict, risk = "No enforcement record found", "clear"

    return {
        "query": query,
        "verdict": verdict,
        "risk": risk,
        "sanctions": [dict(a) for a in sanctions],
        "compliance_notices": [dict(a) for a in notices],
        "phoenix_links": [dict(p) for p in phoenix],
        "disclaimer": "Based on public NDIS Commission register + ABR. A clear result "
                      "is not endorsement; absence from the register is not proof of good "
                      "standing. Phoenix links are leads for verification, not allegations.",
    }


def main(argv: list[str]) -> int:
    if not argv:
        print('usage: python -m app.check "<name or ABN>"', file=sys.stderr)
        return 2
    res = check(" ".join(argv))
    print(f"\n  {res['query']}\n  → {res['verdict']}  [{res['risk'].upper()}]")
    for s in res["sanctions"]:
        print(f"    • {s['type'][5:]} effective {s['date_from']}: {(s['detail'] or '')[:90]}")
    for n in res["compliance_notices"][:3]:
        print(f"    • notice {n['date_from']}: {(n['detail'] or '')[:90]}")
    for p in res["phoenix_links"][:5]:
        print(f"    • phoenix lead (conf {p['confidence']:.0f}): ABN {p['abn']} "
              f"namesakes {p['name_freq']}, {p['geo']} — {p['note'][:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
