"""Den DA Assessment Copilot — three-pane demo UI.

Run: uv run streamlit run web/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.compliance import evaluate_seed, render_table  # noqa: E402
from app.evaluate import score  # noqa: E402
from app.export import md_to_docx  # noqa: E402
from app.proposal import load_seed  # noqa: E402
from app.report import compose  # noqa: E402
from app.submissions import analyse_seed  # noqa: E402

st.set_page_config(page_title="Den DA Assessment Copilot", layout="wide")

SEEDS = {"26-30 McIntyre Street, Gordon (eDA0371/25, refused)": "data/seeds/mcintyre"}

with st.sidebar:
    st.title("Den DA Copilot")
    st.caption("The machine drafts, the planner decides. Every claim is cited.")
    mode = st.radio("Input", ["Seed case", "Any NSW address (controls only)"])
    if mode == "Seed case":
        seed_label = st.selectbox("Case", list(SEEDS))
        run = st.button("Draft assessment report", type="primary")
    else:
        address = st.text_input("NSW address", "74 Ridge Street, Gordon NSW 2072")
        run = st.button("Retrieve planning controls", type="primary")

if mode == "Any NSW address (controls only)":
    if run and address:
        from app.controls import retrieve
        from app.property import resolve
        with st.status("Resolving property and querying ePlanning layers..."):
            prop = resolve(address)
            ctx = retrieve(prop)
        st.subheader(f"{prop.address} — {', '.join(prop.lots)} ({prop.lga})")
        st.markdown(f"**Zone:** {ctx.zone_code} {ctx.zone_class} — *{ctx.lep_name}*")
        cols = st.columns(len(ctx.standards) or 1)
        for col, s in zip(cols, ctx.standards):
            col.metric(s.name, f"{s.value} {s.unit or ''}")
        if ctx.permitted_uses:
            st.markdown("**Permitted with consent:** " + "; ".join(ctx.permitted_uses))
        with st.expander("Audit log — every claim and its source", expanded=True):
            for c in ctx.citations:
                st.markdown(f"- **{c.claim}** — [{c.source_type}]({c.source_ref}) `{c.quote or ''}`")
else:
    seed_dir = SEEDS[seed_label]
    seed = load_seed(seed_dir)
    findings = evaluate_seed(seed)
    submissions = analyse_seed(seed)
    draft = compose(seed, findings, submissions, seed_dir)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Draft assessment report")
        st.caption("DRAFT — for planner review. Yellow rows need professional judgement.")
        breaches = [f for f in findings if f.complies is False]
        ok = [f for f in findings if f.complies is True]
        review = [f for f in findings if f.complies is None]
        c1, c2, c3 = st.columns(3)
        c1.metric("Non-compliances", len(breaches))
        c2.metric("Compliant", len(ok))
        c3.metric("Needs planner review", len(review))
        st.markdown(render_table(findings))
        edited = st.text_area("Edit the draft", draft, height=600)
        out_docx = Path(seed_dir) / "draft_report.docx"
        md_to_docx(edited, out_docx)
        st.download_button("Download .docx", out_docx.read_bytes(),
                           file_name="draft_assessment_report.docx")
        with st.expander("Audit log"):
            for f in findings:
                st.markdown(f"- **{f.control}** — `{f.citation.source_ref}`")
    with right:
        st.subheader("Side-by-side: the real council report")
        s = score(seed_dir)
        rec = s["recommendation"]
        st.metric("Recommendation agreement",
                  "AGREE" if rec["agree"] else "DISAGREE",
                  f"draft: {rec['draft']} / council: {rec['gold']}")
        ir = s["issue_recall"]
        st.metric("Issue recall", f"{ir['hit']}/{ir['total']}")
        if ir["missed"]:
            st.caption("Missed (qualitative design issues, pending LLM stage): "
                       + ", ".join(ir["missed"]))
        st.markdown("**Numeric breaches both reports flag:**")
        for b in s["numeric_breaches_flagged"]:
            st.markdown(f"- {b}")
        report_pdf = Path(seed_dir) / "assessment_report.pdf"
        if report_pdf.exists():
            st.download_button("Open the real KLPP report (PDF)",
                               report_pdf.read_bytes(),
                               file_name="KLPP_assessment_report.pdf")
        st.caption("Gold source: Ku-ring-gai LPP 15 Dec 2025, item GB.2 — public papers.")
