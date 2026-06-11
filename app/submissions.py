"""SubmissionsAnalyser.

Works from the public submissions summary inside the assessment report (full
objection letters are generally not public). For seed cases the themes are
loaded from the reviewed facts.json; LLM clustering of pasted submissions
arrives in M4.
"""
from __future__ import annotations

from .models import Citation, SubmissionIssue


CLUSTER_SYSTEM = """You analyse public submissions on a NSW development application
for a council planner. Cluster the issues raised into themes. Redact and ignore all
submitter names and addresses — work at the level of issues only. For each theme
return: theme, count (submissions raising it), head_of_consideration (one of the
s4.15(1) heads, e.g. "4.15(1)(b) likely impacts — traffic"), and quote (a short
verbatim excerpt, with any personal details removed). Do NOT draft responses to
issues — that requires the planning assessment. Return JSON {"themes": [...]}."""


def cluster_text(submissions_text: str) -> list[SubmissionIssue]:
    """Cluster pasted submission letters into themes (for councils that have them)."""
    from .llm import complete
    data = complete(CLUSTER_SYSTEM, submissions_text[:24000], json_object=True)
    return [SubmissionIssue(
        theme=t["theme"], count=int(t.get("count", 1)),
        head_of_consideration=t.get("head_of_consideration", "4.15(1)(d) submissions"),
        draft_response="[NEEDS PLANNER INPUT: response grounded in the controls]",
        citations=[Citation(claim=t["theme"], source_type="submission",
                            source_ref="pasted submissions", quote=t.get("quote"))],
    ) for t in data.get("themes", [])]


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
