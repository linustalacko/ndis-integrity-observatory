"""Evaluator: score the draft against the real council report (seed gold).

CLI: python -m app.evaluate data/seeds/mcintyre
"""
from __future__ import annotations

import sys

from .compliance import evaluate_seed
from .proposal import load_seed
from .report import _recommendation, compose
from .submissions import analyse_seed


def score(seed_dir: str) -> dict:
    seed = load_seed(seed_dir)
    gold = seed["raw"]["gold"]
    findings = evaluate_seed(seed)
    submissions = analyse_seed(seed)
    draft = compose(seed, findings, submissions).lower()
    rec, _ = _recommendation(findings)

    # An issue counts as identified if any of its alias phrases appears in the draft.
    aliases = {
        "gross floor area": ["gross floor area", "floor space ratio", "gfa"],
        "building height": ["building height", "height of building"],
        "clause 4.6": ["clause 4.6", "cl 4.6", "4.6 variation", "exceptions to development standards"],
    }
    def hit(issue: str) -> bool:
        return any(a in draft for a in aliases.get(issue, [issue.lower()]))

    issue_hits = [i for i in gold["issues"] if hit(i)]
    refusal_breaches = {f.control for f in findings if f.complies is False}

    return {
        "recommendation": {"draft": rec, "gold": gold["recommendation"],
                           "agree": rec == gold["recommendation"]},
        "issue_recall": {"hit": len(issue_hits), "total": len(gold["issues"]),
                         "hits": issue_hits,
                         "missed": [i for i in gold["issues"] if not hit(i)]},
        "numeric_breaches_flagged": sorted(refusal_breaches),
        "gold_refusal_reason_count": len(gold["refusal_reasons"]),
    }


def main(argv: list[str]) -> int:
    seed_dir = argv[0] if argv else "data/seeds/mcintyre"
    s = score(seed_dir)
    rec = s["recommendation"]
    print(f"Recommendation: draft={rec['draft']} gold={rec['gold']} -> "
          f"{'AGREE' if rec['agree'] else 'DISAGREE'}")
    ir = s["issue_recall"]
    print(f"Issue recall: {ir['hit']}/{ir['total']}")
    print(f"  missed: {ir['missed']}")
    print(f"Numeric breaches flagged: {s['numeric_breaches_flagged']}")
    print(f"Gold refusal reasons (count): {s['gold_refusal_reason_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
