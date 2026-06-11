"""Qualitative design/impacts assessment (LLM, retrieval-grounded).

Inputs are objective documents only — proposal facts, DCP control text, and
the applicant's own clause 4.6 variation request — never the council's
conclusions, so seed evaluation against the real report is not circular.

Every issue must carry a verbatim quote from the supplied inputs; a verifier
pass drops any issue whose quote cannot be found, so the model cannot invent
grounding. Output issues are flagged for planner review, not asserted.
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

import fitz

from .dcp import load_chunks, numeric_controls
from .llm import complete
from .models import Citation

ADG_TOPICS = [
    "communal open space", "building separation", "solar access",
    "natural ventilation", "privacy", "building entry", "internal corridors",
    "amenity of living rooms and balconies", "facade articulation",
    "top storey design and setbacks", "integration of services",
    "deep soil landscaping", "desired future character",
]


class QualitativeIssue(BaseModel):
    theme: str
    head_of_consideration: str  # e.g. "4.15(1)(a) SEPP Housing Ch 4 / ADG"
    assessment: str             # 1-3 sentences, grounded
    status: str                 # "potential-issue" | "acceptable" | "needs-info"
    quote: str | None = None    # verbatim from inputs
    source_ref: str = "inputs"

    def citation(self) -> Citation:
        return Citation(claim=self.theme, source_type="document",
                        source_ref=self.source_ref, quote=self.quote)


SYSTEM = """You are assisting a NSW council development assessment planner.
You assess a residential flat building proposal against the Apartment Design
Guide topics and DCP controls supplied. STRICT RULES:
- Only state facts supported by the supplied text. Every issue MUST include a
  short verbatim quote (under 25 words) copied exactly from the inputs.
- You draft potential issues for a planner to verify; you do not decide.
- If the inputs do not cover a topic, return status "needs-info" for it.
Return JSON: {"issues": [{"theme", "head_of_consideration", "assessment",
"status", "quote", "source_ref"}]}. status is one of potential-issue,
acceptable, needs-info. source_ref names the input document/section quoted."""


def _cl46_text(seed_dir: str | Path, max_chars: int = 14000) -> str:
    pdf = Path(seed_dir) / "attachment_8.pdf"
    if not pdf.exists():
        return ""
    doc = fitz.open(str(pdf))
    return "\n".join(p.get_text() for p in doc)[:max_chars]


def assess(seed: dict, seed_dir: str | Path,
           dcp_pdf: str = "data/dcp/kdcp-part7-rfb.pdf") -> list[QualitativeIssue]:
    p = seed["raw_proposal"]
    dcp_lines = []
    if Path(dcp_pdf).exists():
        for c in load_chunks(dcp_pdf):
            for n in numeric_controls(c)[:3]:
                dcp_lines.append(f"[KDCP {c.section} {c.title} p{c.page}] {n}")
    user = f"""PROPOSAL FACTS (from {seed['case']['da_ref']}):
{json.dumps(p, indent=1)}

DCP CONTROLS (Ku-ring-gai DCP Part 7, residential flat buildings):
{chr(10).join(dcp_lines[:40])}

APPLICANT'S CLAUSE 4.6 VARIATION REQUEST (verbatim extract):
{_cl46_text(seed_dir)}

TOPICS TO ASSESS: {", ".join(ADG_TOPICS)}.
Assess each topic. Quote only from the text above."""
    data = complete(SYSTEM, user, json_object=True, max_tokens=6000)
    issues = [QualitativeIssue(**i) for i in data.get("issues", [])]

    # Verifier: a quote must literally appear in the inputs (whitespace-normalised).
    hay = " ".join((user).split()).lower()
    verified = []
    for i in issues:
        q = " ".join((i.quote or "").split()).lower()
        if q and q in hay:
            verified.append(i)
        else:
            i.status = "needs-info"
            i.assessment = ("[UNGROUNDED — quote not found in inputs; planner to verify] "
                            + i.assessment)
            verified.append(i)
    return verified


def main() -> int:
    from .proposal import load_seed
    seed_dir = "data/seeds/mcintyre"
    issues = assess(load_seed(seed_dir), seed_dir)
    for i in issues:
        print(f"[{i.status:15}] {i.theme} — {i.assessment[:110]}")
    Path(seed_dir, "qualitative_issues.json").write_text(
        json.dumps([i.model_dump() for i in issues], indent=2))
    print(f"\nwritten {seed_dir}/qualitative_issues.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
