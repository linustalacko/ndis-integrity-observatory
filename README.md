# Den DA Assessment Copilot — prototype

Drafts a NSW section 4.15 development assessment report from public data,
citation-checked against the real council report. The machine drafts, the
planner decides; every factual claim is cited or flagged `[NEEDS PLANNER INPUT]`.

## Status

- **M0 ✅** Open-data spine: address → lot (SIX cadastre) → cited planning
  controls (ePlanning ArcGIS: zone, HOB, FSR, lot size, heritage), with
  mapprod host fallback and disk caching.
  `uv run python -m app.controls "26-30 McIntyre Street, Gordon NSW 2072"`
- **M1 ✅** Deterministic compliance engine agrees with the real Ku-ring-gai
  KLPP report (eDA0371/25) on every numeric row, including breach magnitudes
  (FSR +23.29%, height +4.08 m, affordable housing 9.6% < 10%).
  `uv run python -m app.compliance data/seeds/mcintyre` · check: `uv run python eval/m1_check.py`
- **M2 ✅ (deterministic core)** Full §4.15 draft report composed from the case
  file with inline citations, submissions table, draft refusal reasons, and an
  evaluator that diffs against the gold report (recommendation agrees;
  numeric/statutory issues recalled; qualitative ADG/design issues await the
  LLM + DCP retrieval stage).
  `uv run python -m app.report data/seeds/mcintyre` · `uv run python -m app.evaluate data/seeds/mcintyre`
- **M3 ✅** Generalised intake (any NSW address, verified on 74 Ridge Street,
  Gordon → Lot A//DP328175, R2, 9.5 m / 0.3:1 / 930 m², matching the real GB.3
  report); LEP Land Use Table parser + permissibility check (KLEP 2015 cached
  in `data/lep/` — legislation.nsw.gov.au WAF blocks scripted fetch, captured
  via browser); DCP retriever over KDCP Part 7 (residential flat buildings)
  with section-aware chunking and a DCP compliance table (catches the 52.3 m
  vs 36 m building-length breach the real report flags).
  `uv run python -m app.dcp`
- **M4 ✅ (no-LLM core)** Three-pane Streamlit demo with seed side-by-side
  scorecard, editable draft, audit log, and .docx export.
  `uv run streamlit run web/app.py` · `uv run python -m app.export`
- **LLM stages ✅** (`app/llm.py`, OpenRouter key in `.env`, model override via
  `DEN_LLM_MODEL`): qualitative ADG/DCP design assessment (`app/impacts.py`)
  grounded in the applicant's own clause 4.6 request + DCP controls, with a
  verifier that drops any claim whose quote isn't found verbatim in the inputs
  — **issue recall now 14/14**, recommendation agreement maintained;
  document extraction (`app.proposal.extract_from_text`) with per-field
  evidence quotes and ungrounded-value nulling; submissions clustering with
  PII redaction (`app.submissions.cluster_text`).
  `uv run python -m app.impacts`
- **Remaining stretch** plan-figure vision extraction from architectural
  drawings; LLM prose polish of report sections; condition library;
  multi-council DCP adapters.

## Seed case

Ku-ring-gai LPP 15 Dec 2025, item GB.2 — 26-30 McIntyre Street, Gordon
(eDA0371/25), refused. Assessment report committed at
`data/seeds/mcintyre/assessment_report.pdf` (attachment group 16884; note the
build-plan's original mapping was wrong: 16802 = Tulkiyan/707 Pacific Hwy,
16872 = 74 Ridge St).

Known provenance wrinkle: today's ePlanning map shows HOB 29 m / FSR 1.8:1
(April 2026 TOD-alternative LEP amendment), while the December 2025 assessment
ran under SEPP (Housing) 2021 Ch 2/6 standards (base 22 m / 2.2:1 plus bonus
provisions). Effective standards for the seed are pinned, with citations, in
`data/seeds/mcintyre/facts.json`.

## Layout

See the build plan (Section 13). `app/` pipeline stages, `data/seeds/` gold
cases, `data/cache/` cached API responses (gitignored), `eval/` acceptance
checks.
