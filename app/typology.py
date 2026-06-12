"""M2: Typology engine — classify enforcement free text into fraud/conduct typologies.

Every classification must carry a verbatim quote from the action's own text;
quotes that don't appear in the source are stored with quote_verified=0 and the
row is treated as 'unclassified' in dashboards. Resumable: already-classified
action_ids are skipped.

CLI: python -m app.typology [--limit N]
"""
from __future__ import annotations

import json
import sys

from .db import connect
from .llm import complete

TYPOLOGIES = [
    "phantom billing / services not provided",
    "overcharging / duplicate / inflated claims",
    "claiming outside plan or without authorisation",
    "false or misleading information / documents",
    "worker screening / clearance breach",
    "abuse, neglect or violence toward participant",
    "sexual misconduct",
    "unauthorised restrictive practices",
    "medication / care management failure",
    "conflict of interest / steering",
    "unregistered or unqualified provision",
    "record keeping / incident reporting failure",
    "financial misconduct against participant funds",
    "criminal history / character",
    "other / unclear",
]

SYSTEM = f"""You classify NDIS Commission enforcement actions for a public-interest
integrity observatory. For each numbered action you receive (type + free text),
return a JSON object: {{"results": [{{"id": <id>,
"typology": <one of: {"; ".join(TYPOLOGIES)}>,
"section_cited": <NDIS Act section cited, e.g. "73ZN(2)(a)(iii)", or "">,
"duration": <"permanent" | "<n> years" | "until further notice" | "">,
"quote": <a SHORT verbatim excerpt (max 20 words) copied EXACTLY from that
action's text that justifies the typology>}}]}}.
Rules: the quote must be copied character-for-character from the text. If the
text does not say what the conduct was, use typology "other / unclear" and quote
the most informative phrase. Never invent details."""


def classify_batch(rows) -> list[dict]:
    numbered = "\n\n".join(
        f"[{i}] TYPE: {r['type']}\nTEXT: {(r['detail'] or '')[:900]}"
        for i, r in enumerate(rows))
    data = complete(SYSTEM, numbered, json_object=True)
    return data.get("results", [])


def verify_quote(quote: str, detail: str) -> bool:
    q = " ".join((quote or "").split()).lower().strip('"“”.')
    d = " ".join((detail or "").split()).lower()
    return bool(q) and q in d


def main(argv: list[str]) -> int:
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    conn = connect()
    todo = conn.execute(
        "SELECT action_id, type, detail FROM actions WHERE action_id NOT IN "
        "(SELECT action_id FROM typologies) AND detail != '' ORDER BY date_from DESC"
    ).fetchall()
    if limit:
        todo = todo[:limit]
    print(f"{len(todo)} actions to classify")
    BATCH = 20
    done = verified = 0
    for i in range(0, len(todo), BATCH):
        rows = todo[i:i + BATCH]
        try:
            results = classify_batch(rows)
        except Exception as e:
            print(f"  batch {i // BATCH}: ERROR {e}", flush=True)
            continue
        for res in results:
            try:
                idx = int(res["id"])
                row = rows[idx]
            except (KeyError, ValueError, IndexError):
                continue
            ok = verify_quote(res.get("quote", ""), row["detail"])
            conn.execute(
                "INSERT OR REPLACE INTO typologies (action_id, typology, section_cited, "
                "duration, quote, quote_verified, model) VALUES (?,?,?,?,?,?,?)",
                (row["action_id"], res.get("typology", "other / unclear"),
                 res.get("section_cited", ""), res.get("duration", ""),
                 res.get("quote", ""), int(ok), "claude-haiku-4.5"))
            done += 1
            verified += int(ok)
        conn.commit()
        print(f"  {done}/{len(todo)} classified ({verified} quote-verified)", flush=True)
    print(f"\ndone: {done} classified, {verified} verified "
          f"({verified / max(done, 1):.0%} verification rate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
