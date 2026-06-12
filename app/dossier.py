"""Lead dossier generator.

Compiles everything known about a sanctioned entity into one cited evidence
pack: register history, the conduct typology, every matched ABN (with ASIC
number, trading names, GST timing), the phoenix rationale, and any media
release naming them. Built for a human to verify before relying on it.

CLI: python -m app.dossier "Krista Vegter"
     python -m app.dossier --all-high     # dossiers for every high-confidence lead
"""
from __future__ import annotations

import sys

from .db import connect
from .ingest import norm_name


def build(conn, name_or_abn: str) -> str:
    digits = "".join(c for c in name_or_abn if c.isdigit())
    nn = norm_name(name_or_abn)
    if len(digits) == 11:
        actions = conn.execute("SELECT * FROM actions WHERE abn=? ORDER BY date_from",
                               (digits,)).fetchall()
    else:
        actions = conn.execute(
            "SELECT * FROM actions WHERE norm_name=? OR name LIKE ? ORDER BY date_from",
            (nn, f"%{name_or_abn}%")).fetchall()
    if not actions:
        return f"# No register entry for {name_or_abn!r}\n"

    display = actions[0]["name"]
    out = [f"# Lead dossier — {display}", "",
           "> Compiled from public data (NDIS Commission compliance register, "
           "ABN Bulk Extract, AFP media releases). **Leads for verification, not "
           "allegations.** A person may lawfully hold an ABN after an NDIS ban; the "
           "concern is only NDIS-funded activity.", ""]

    out.append("## 1. Enforcement history")
    for a in actions:
        out.append(f"\n**{a['type'][5:]}** — effective {a['date_from']}"
                   f"{', no longer in force ' + a['date_to'] if a['date_to'] else ''}")
        out.append(f"- Location on register: {a['city']} {a['state']} {a['postcode']}"
                   f" · ABN on register: {a['abn'] or '—'} · Provider no: {a['provider_number'] or '—'}")
        out.append(f"- Tracked across snapshots {a['first_seen']} → {a['last_seen']}")
        typ = conn.execute("SELECT typology, quote, quote_verified FROM typologies "
                          "WHERE action_id=?", (a["action_id"],)).fetchone()
        if typ:
            v = "✓verbatim" if typ["quote_verified"] else "unverified"
            out.append(f"- Conduct typology: **{typ['typology']}** "
                      f"(quote [{v}]: “{typ['quote']}”)")
        if a["detail"]:
            out.append(f"- Register text: {a['detail']}")
        out.append(f"- Source: NDIS Commission compliance register via data.gov.au")

    out.append("\n## 2. Linked ABNs (Australian Business Register)")
    links = conn.execute("""
        SELECT DISTINCT m.abn, m.confidence, m.tier, m.match_type, m.name_freq, m.geo,
               m.post_ban_registration, b.legal_name, b.entity_type, b.abn_status,
               b.status_date, b.gst_status, b.gst_from, b.state, b.postcode,
               b.asic_number, b.other_names
        FROM matches m JOIN actions a USING(action_id)
        LEFT JOIN abns b ON b.abn = m.abn
        WHERE a.norm_name=? OR a.abn=?
        ORDER BY m.post_ban_registration DESC, m.confidence DESC""",
        (nn, digits or "\x00")).fetchall()
    if not links:
        out.append("\n*No ABN links found.*")
    for l in links:
        flag = " ⚠️ **ACTIVE, registered AFTER the sanction**" if l["post_ban_registration"] else ""
        out.append(f"\n**ABN {l['abn']}** — {l['legal_name']}{flag}")
        out.append(f"- Status: {l['abn_status']} from {l['status_date']} · "
                  f"GST: {l['gst_status']} from {l['gst_from'] or '—'} · "
                  f"Type: {l['entity_type']} · {l['state']} {l['postcode']}")
        if l["asic_number"]:
            out.append(f"- ASIC number: {l['asic_number']} "
                      f"(→ cross-check directors via ASIC company register)")
        if l["other_names"]:
            out.append(f"- Other/trading names: {l['other_names']}")
        out.append(f"- Match: {l['match_type']} · confidence **{l['confidence']:.0f}/100** "
                  f"({l['tier']}) · namesakes in ABR: {l['name_freq']} · geo: {l['geo']}")
        out.append("- Source: ABN Bulk Extract (Australian Business Register, data.gov.au)")

    out.append("\n## 3. Confidence rationale")
    hi = [l for l in links if l["post_ban_registration"]]
    if hi:
        best = hi[0]
        out.append(f"- Strongest lead scores **{best['confidence']:.0f}/100** ({best['tier']}).")
        out.append(f"- Name shared by **{best['name_freq']}** ABR entit"
                  f"{'y' if best['name_freq'] == 1 else 'ies'} → "
                  f"{'very low' if best['name_freq'] <= 1 else 'some'} collision risk.")
        out.append(f"- Geography: ABN vs sanction location = **{best['geo']}**.")
        out.append(f"- Match basis: **{best['match_type']}**.")
    else:
        out.append("- No post-sanction active ABN identified for this entity.")

    out.append("\n## 4. Media / public record")
    arts = conn.execute("""
        SELECT DISTINCT ar.title, ar.published, ar.url FROM article_matches m
        JOIN actions a USING(action_id) JOIN articles ar ON ar.url=m.url
        WHERE a.norm_name=?""", (nn,)).fetchall()
    if arts:
        for ar in arts:
            out.append(f"- [{ar['published']}] {ar['title']} — {ar['url']}")
    else:
        out.append("- No matched media release. (Most banning orders are not "
                  "individually reported; absence here is expected.)")

    out.append("\n## 5. Recommended verification steps")
    out += [
        "1. Confirm identity: match date of birth / address via ASIC extract "
        "(paid) for any company ABN above.",
        "2. Check the live NDIS provider register for current registration status.",
        "3. If plan-managed invoices exist for any linked ABN, screen them in the "
        "Claims lab against the sanction date.",
        "4. Do not publish as an allegation until identity is confirmed.",
    ]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    conn = connect()
    if "--all-high" in argv:
        from pathlib import Path
        out_dir = Path(__file__).resolve().parent.parent / "data" / "dossiers"
        out_dir.mkdir(parents=True, exist_ok=True)
        names = conn.execute("""
            SELECT DISTINCT a.name FROM matches m JOIN actions a USING(action_id)
            WHERE m.post_ban_registration=1 AND m.tier='high'""").fetchall()
        for r in names:
            md = build(conn, r["name"])
            safe = "".join(ch if ch.isalnum() else "_" for ch in r["name"])[:50]
            (out_dir / f"{safe}.md").write_text(md)
        print(f"wrote {len(names)} dossiers to {out_dir}")
        return 0
    if not argv:
        print('usage: python -m app.dossier "<name or ABN>" | --all-high', file=sys.stderr)
        return 2
    print(build(conn, " ".join(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
