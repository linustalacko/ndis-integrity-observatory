"""SubmissionsAnalyser.

Works from the public submissions summary inside the assessment report (full
objection letters are generally not public). For seed cases the themes are
loaded from the reviewed facts.json; LLM clustering of pasted submissions
arrives in M4.
"""
from __future__ import annotations

from .models import Citation, SubmissionIssue


def analyse_seed(seed: dict) -> list[SubmissionIssue]:
    issues = []
    for s in seed.get("raw", {}).get("submissions_summary", []):
        issues.append(SubmissionIssue(
            theme=s["theme"],
            count=s["count"],
            head_of_consideration=s["head_of_consideration"],
            draft_response=s["report_response"],
            citations=[Citation(claim=s["theme"], source_type="submission",
                                source_ref=s["source"])],
        ))
    return issues
