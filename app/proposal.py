"""ProposalExtractor.

For seed cases the facts are extracted from the council assessment report's
proposal/site sections and stored as a reviewed facts.json next to the PDF
(LLM/vision extraction from SoEE and plans arrives in M3).
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import ProposalFacts


def load_seed(seed_dir: str | Path) -> dict:
    """Load a seed case: returns {'case', 'proposal': ProposalFacts, 'effective_standards'}."""
    data = json.loads((Path(seed_dir) / "facts.json").read_text())
    p = data["proposal"]
    facts = ProposalFacts(**{k: v for k, v in p.items()
                             if k in ProposalFacts.model_fields})
    return {"case": data["case"], "proposal": facts, "raw_proposal": p,
            "effective_standards": data["effective_standards"], "raw": data}
