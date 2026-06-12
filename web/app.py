"""NDIS Provider Integrity Observatory — demo UI.

Run: uv run streamlit run web/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import connect  # noqa: E402

st.set_page_config(page_title="NDIS Provider Integrity Observatory", layout="wide",
                   page_icon="🔍")


@st.cache_resource
def db():
    return connect()


conn = db()

st.sidebar.title("🔍 NDIS Integrity Observatory")
st.sidebar.caption(
    "Built entirely from public government data: the NDIS Commission compliance "
    "register (data.gov.au), the ABN Bulk Extract (ABR), and the NDIS Support "
    "Catalogue. Every fact links to its source. Inferences are questions for "
    "verification, not allegations.")

snap = conn.execute("SELECT MIN(snapshot_date) a, MAX(snapshot_date) b, COUNT(*) n "
                    "FROM snapshots").fetchone()
total = conn.execute("SELECT COUNT(*) c FROM actions").fetchone()["c"]
st.sidebar.metric("Enforcement actions tracked", f"{total:,}")
st.sidebar.metric("Register snapshots", f"{snap['n']} ({snap['a']} → {snap['b']})")
phx = conn.execute("SELECT COUNT(DISTINCT action_id) c FROM matches "
                   "WHERE post_ban_registration=1").fetchone()["c"]
st.sidebar.metric("Post-sanction ABN candidates", f"{phx:,}")

tab_overview, tab_register, tab_phoenix, tab_typology, tab_diff, tab_claims = st.tabs(
    ["Overview", "Register explorer", "Phoenix watch", "Typologies",
     "Register diff", "Claims lab"])

# ---------------------------------------------------------------- Overview
with tab_overview:
    st.header("The enforcement landscape")
    col1, col2, col3, col4 = st.columns(4)
    bans = conn.execute("SELECT COUNT(*) c FROM actions WHERE type='ER - Banning Order'").fetchone()["c"]
    notices = conn.execute("SELECT COUNT(*) c FROM actions WHERE type='ER - Compliance notice'").fetchone()["c"]
    revocs = conn.execute("SELECT COUNT(*) c FROM actions WHERE type LIKE '%Revocation%'").fetchone()["c"]
    col1.metric("Banning orders", f"{bans:,}")
    col2.metric("Compliance notices", f"{notices:,}")
    col3.metric("Registration revocations", f"{revocs:,}")
    col4.metric("Phoenix candidates", f"{phx:,}")

    df = pd.read_sql_query(
        "SELECT substr(date_from,1,7) month, type, COUNT(*) n FROM actions "
        "WHERE date_from >= '2022-01' GROUP BY month, type", conn)
    if not df.empty:
        fig = px.bar(df, x="month", y="n", color="type",
                     title="Enforcement actions by month (date effective)",
                     labels={"n": "actions", "month": ""})
        fig.update_layout(legend_title="", height=420)
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        df2 = pd.read_sql_query(
            "SELECT state, type, COUNT(*) n FROM actions WHERE state != '' "
            "GROUP BY state, type", conn)
        st.plotly_chart(px.bar(df2, x="state", y="n", color="type",
                               title="Actions by state").update_layout(
            legend_title="", height=380), use_container_width=True)
    with right:
        df3 = pd.read_sql_query("""
            SELECT postcode || ' ' || MAX(city) AS location, COUNT(*) n
            FROM actions WHERE postcode != '' GROUP BY postcode
            ORDER BY n DESC LIMIT 15""", conn)
        st.plotly_chart(px.bar(df3, x="n", y="location", orientation="h",
                               title="Hotspot postcodes (action count)").update_layout(
            height=380, yaxis=dict(autorange="reversed")), use_container_width=True)

# ---------------------------------------------------------------- Register explorer
with tab_register:
    st.header("Search the enforcement register, with history")
    q = st.text_input("Provider or person name", placeholder="e.g. Touch & Care, MADUT, Aussie Life")
    if q:
        rows = pd.read_sql_query(
            "SELECT type, name, abn, city, state, postcode, date_from, date_to, "
            "first_seen, last_seen, detail FROM actions WHERE name LIKE ? OR abn LIKE ? "
            "ORDER BY date_from DESC", conn, params=(f"%{q}%", f"%{q}%"))
        st.caption(f"{len(rows)} actions matched")
        for _, r in rows.iterrows():
            badge = "🔴" if "Banning" in r["type"] else ("🟠" if "Revocation" in r["type"] else "🟡")
            with st.expander(f"{badge} {r['type'][5:]} — {r['name']} ({r['state']}, "
                             f"effective {r['date_from']})"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**ABN:** {r['abn'] or '—'}")
                c2.markdown(f"**Location:** {r['city']} {r['postcode']}")
                c3.markdown(f"**In force until:** {r['date_to'] or 'ongoing'}")
                st.markdown(f"**Register text:** {r['detail'] or '*no detail published*'}")
                st.caption(f"First seen in snapshot {r['first_seen']}, last seen {r['last_seen']} "
                           f"· Source: NDIS Commission compliance register via data.gov.au")
                links = pd.read_sql_query(
                    "SELECT m.abn, m.match_type, m.score, m.post_ban_registration, m.note "
                    "FROM matches m JOIN actions a USING(action_id) "
                    "WHERE a.name = ? ORDER BY m.post_ban_registration DESC",
                    conn, params=(r["name"],))
                if not links.empty:
                    st.markdown("**Linked ABNs (ABR):**")
                    for _, l in links.iterrows():
                        flag = " ⚠️ **became active after this sanction**" if l["post_ban_registration"] else ""
                        st.markdown(f"- `{l['abn']}` ({l['match_type']}, {l['score']:.0f}) "
                                    f"{l['note']}{flag}")

# ---------------------------------------------------------------- Phoenix watch
with tab_phoenix:
    st.header("Phoenix watch — sanctioned, yet an ABN is active")
    st.caption(
        "Entities subject to a banning order / revocation whose exact-or-matched name "
        "or ABN shows an **active ABN with a status date after the sanction**. "
        "Common names can collide — every row is a question for verification, "
        "not an allegation. Matching: exact ABN > exact normalised name > fuzzy (persons, ≥90).")
    min_score = st.slider("Minimum match confidence", 80, 100, 100)
    only_distinct = st.checkbox("Hide common-name risks (require ≥3 name tokens)", value=False)
    df = pd.read_sql_query("""
        SELECT a.name, a.type, a.date_from sanction_date, a.city, a.state,
               m.abn, m.match_type, m.score, m.note
        FROM matches m JOIN actions a USING(action_id)
        WHERE m.post_ban_registration = 1 AND m.score >= ?
        ORDER BY a.date_from DESC""", conn, params=(min_score,))
    if only_distinct:
        df = df[df["name"].str.split().str.len() >= 3]
    st.metric("Candidates", len(df))
    st.dataframe(df, use_container_width=True, height=520)
    st.download_button("Download candidates CSV", df.to_csv(index=False),
                       "phoenix_candidates.csv")

# ---------------------------------------------------------------- Typologies
with tab_typology:
    st.header("What is the conduct? — LLM-classified, quote-verified")
    st.caption(
        "Each enforcement action's free text is classified into a conduct typology. "
        "A classification only counts if its supporting quote appears verbatim in the "
        "register text (quote_verified=1). Unverified rows are shown as unclassified.")
    n_class = conn.execute("SELECT COUNT(*) c FROM typologies").fetchone()["c"]
    n_ver = conn.execute("SELECT COUNT(*) c FROM typologies WHERE quote_verified=1").fetchone()["c"]
    st.metric("Classified", f"{n_class:,} ({n_ver:,} quote-verified)")
    if n_class:
        df = pd.read_sql_query("""
            SELECT t.typology, a.type, COUNT(*) n FROM typologies t
            JOIN actions a USING(action_id) WHERE t.quote_verified=1
            GROUP BY t.typology, a.type ORDER BY n DESC""", conn)
        st.plotly_chart(px.bar(df, y="typology", x="n", color="type", orientation="h",
                               title="Verified conduct typologies").update_layout(
            height=520, legend_title="", yaxis=dict(autorange="reversed")),
            use_container_width=True)
        pick = st.selectbox("Inspect a typology", sorted(df["typology"].unique()))
        sample = pd.read_sql_query("""
            SELECT a.name, a.type, a.date_from, t.quote, a.detail FROM typologies t
            JOIN actions a USING(action_id)
            WHERE t.typology = ? AND t.quote_verified=1 ORDER BY a.date_from DESC LIMIT 10""",
            conn, params=(pick,))
        for _, r in sample.iterrows():
            st.markdown(f"- **{r['name']}** ({r['type'][5:]}, {r['date_from']}) — "
                        f"“{r['quote']}”")

# ---------------------------------------------------------------- Register diff
with tab_diff:
    st.header("Register changes between snapshots")
    snaps = [r["snapshot_date"] for r in
             conn.execute("SELECT snapshot_date FROM snapshots ORDER BY 1")]
    if len(snaps) >= 2:
        c1, c2 = st.columns(2)
        a = c1.selectbox("From snapshot", snaps, index=len(snaps) - 2)
        b = c2.selectbox("To snapshot", snaps, index=len(snaps) - 1)
        new = pd.read_sql_query(
            "SELECT type, name, state, date_from FROM actions WHERE first_seen > ? "
            "AND first_seen <= ? ORDER BY date_from DESC", conn, params=(a, b))
        gone = pd.read_sql_query(
            "SELECT type, name, state, date_from, last_seen FROM actions "
            "WHERE last_seen >= ? AND last_seen < ? ORDER BY last_seen DESC",
            conn, params=(a, b))
        left, right = st.columns(2)
        with left:
            st.subheader(f"➕ New on register ({len(new)})")
            st.dataframe(new, use_container_width=True, height=420)
        with right:
            st.subheader(f"➖ Removed from register ({len(gone)})")
            st.caption("Actions present in earlier snapshots that no longer appear — "
                       "expiries, successful appeals, or silent removals.")
            st.dataframe(gone, use_container_width=True, height=420)

# ---------------------------------------------------------------- Claims lab
with tab_claims:
    st.header("Claims lab — invoice screening against the rules")
    st.caption(
        "Deterministic screening of invoice batches against the NDIS Support Catalogue "
        "2025-26 price caps, the NDIA's own fraud typologies, and the live enforcement "
        "register. Upload a CSV or use the synthetic demo batch (every fraud type seeded).")
    from app.claims import (catalogue_index, fetch_catalogue, load_invoices,
                            sanctioned_providers, screen)

    upload = st.file_uploader("Invoice CSV", type="csv")
    src = upload if upload is not None else ROOT / "data" / "synthetic_invoices.csv"
    if upload is not None or (ROOT / "data" / "synthetic_invoices.csv").exists():
        invoices = load_invoices(src)
        cat = catalogue_index(fetch_catalogue())
        findings = screen(invoices, cat, sanctioned_providers(conn))
        c1, c2, c3 = st.columns(3)
        c1.metric("Invoice lines", len(invoices))
        c2.metric("Breaches", sum(1 for f in findings if f.severity == "breach"))
        c3.metric("Warnings", sum(1 for f in findings if f.severity == "warning"))
        rows = pd.DataFrame([{
            "line": f.invoice_line, "rule": f.rule, "severity": f.severity,
            "detail": f.detail, "citation": f.citation} for f in findings])
        st.dataframe(rows, use_container_width=True, height=380)
        st.subheader("Invoice batch")
        st.dataframe(pd.read_csv(src), use_container_width=True, height=300)
