"""ReportComposer: assemble a draft section 4.15 assessment report from the case file.

Deterministic templating from validated structured data. Every number comes
from a ComplianceFinding or a cited fact; anything ungrounded is emitted as a
[NEEDS PLANNER INPUT: ...] marker, never asserted. An LLM polish pass over the
prose (constrained to these facts) is a later milestone.

CLI: python -m app.report data/seeds/mcintyre [--live-controls]
"""
from __future__ import annotations

import sys
from pathlib import Path

from .compliance import evaluate_seed, render_table
from .models import ComplianceFinding, SubmissionIssue
from .proposal import load_seed
from .submissions import analyse_seed

DISCLAIMER = (
    "> **DRAFT — prepared by Den Assessment Copilot.** This document is a draft for a "
    "planning officer to review, edit and own. It is not a determination. Every factual "
    "claim is cited to its source; items marked **[NEEDS PLANNER INPUT]** require "
    "professional judgement.\n"
)


def _recommendation(findings: list[ComplianceFinding]) -> tuple[str, list[str]]:
    breaches = [f for f in findings if f.complies is False]
    if not breaches:
        return "approval", []
    reasons = [
        f"{i}. {f.control} does not comply: proposed {f.proposed} against a requirement of "
        f"{f.requirement} ({f.breach_magnitude or 'non-compliant'}). Source: {f.citation.source_ref}."
        for i, f in enumerate(breaches, 1)
    ]
    return "refusal", reasons


def compose(seed: dict, findings: list[ComplianceFinding],
            submissions: list[SubmissionIssue]) -> str:
    case = seed["case"]
    p = seed["raw_proposal"]
    std = seed["effective_standards"]
    rec, reasons = _recommendation(findings)
    rec_line = ("Refusal, for the reasons set out in this report." if rec == "refusal"
                else "Approval, subject to conditions.")

    sub_rows = "\n".join(
        f"| {s.theme} | {s.count} | {s.head_of_consideration} | {s.draft_response} "
        f"| {s.citations[0].source_ref} |" for s in submissions)

    impact_themes = [s for s in submissions if "4.15(1)(b)" in s.head_of_consideration]
    impacts_md = "\n".join(
        f"- **{s.theme}** — {s.draft_response} ({s.citations[0].source_ref})"
        for s in impact_themes) or "[NEEDS PLANNER INPUT: likely impacts assessment]"

    reasons_md = ("\n".join(reasons) if rec == "refusal"
                  else "[NEEDS PLANNER INPUT: draft conditions of consent]")

    return f"""# Development Assessment Report (DRAFT)

{DISCLAIMER}

## 1. Application details

| | |
|---|---|
| Application No | {case['da_ref']} |
| Address | {case['address']} |
| Proposal | {case['description']} |
| Council | {case['council']} |
| Lodged | {case['lodged']} |
| Submissions | {case['submissions']} |
| Recommendation | **{rec_line}** |

## 2. Executive summary

The application seeks consent for {case['description'].lower()}. Assessment against the
applicable planning controls identifies {sum(1 for f in findings if f.complies is False)}
non-compliances with development standards (see Section 6). The draft recommendation is
**{rec}**. [NEEDS PLANNER INPUT: confirm executive summary emphasis]

## 3. Site and locality

The site has an area of {p['site_area_m2']} m2 ({seed['raw']['case'].get('source_report')} —
survey). [NEEDS PLANNER INPUT: site description, surrounding development, constraints]

## 4. The proposal

{p['development_type'].capitalize()}: {p['storeys']} storeys, {p['dwelling_count']} dwellings,
{p['gfa_m2']} m2 GFA, maximum height {p['proposed_height_m']} m.
Sources: {'; '.join(p['extracted_from'])}.

## 5. Background

[NEEDS PLANNER INPUT: application history, pre-lodgement, RFIs]

## 6. Section 4.15(1)(a) — environmental planning instruments

**Effective standards.** {std['note']}

### Development standards compliance table

{render_table(findings)}

### DCP compliance

[NEEDS PLANNER INPUT: DCP controls table — arrives with the DCP retriever (M3)]

## 7. Section 4.15(1)(b) — likely impacts

{impacts_md}

[NEEDS PLANNER INPUT: solar access, privacy, visual bulk, stormwater, ecology]

## 8. Section 4.15(1)(c) — suitability of the site

[NEEDS PLANNER INPUT: site suitability conclusion]

## 9. Section 4.15(1)(d) — submissions

{case['submissions']} submissions were received. Issues raised and draft responses:

| Issue | Count | Head of consideration | Draft response | Source |
|---|---|---|---|---|
{sub_rows}

## 10. Section 4.15(1)(e) — public interest

The public interest is served by the consistent application of the relevant environmental
planning instruments. [NEEDS PLANNER INPUT: confirm]

## 11. {'Reasons for refusal (draft)' if rec == 'refusal' else 'Conditions of consent (draft)'}

{reasons_md}

## 12. Conclusion

Having regard to section 4.15 of the Environmental Planning and Assessment Act 1979, the
draft assessment supports **{rec}**. A planning officer must review every section before
this assessment is relied upon.
"""


def main(argv: list[str]) -> int:
    seed_dir = argv[0] if argv else "data/seeds/mcintyre"
    seed = load_seed(seed_dir)
    findings = evaluate_seed(seed)
    submissions = analyse_seed(seed)
    md = compose(seed, findings, submissions)
    out = Path(seed_dir) / "draft_report.md"
    out.write_text(md)
    print(md)
    print(f"\n[written to {out}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
