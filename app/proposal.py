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


EXTRACT_SYSTEM = """You extract development proposal facts from NSW DA documents
(Statement of Environmental Effects, assessment reports). Return JSON with keys:
development_type, storeys, proposed_height_m, gfa_m2, fsr, site_area_m2,
dwelling_count, affordable_gfa_m2, landscaped_area_m2, setbacks (object).
Use null for anything not stated in the text — NEVER guess or compute a value
that is not written in the document. Also return "evidence": an object mapping
each non-null key to a short verbatim quote supporting it."""


def extract_from_text(text: str, source_name: str = "document") -> dict:
    """LLM extraction of ProposalFacts from document text, with per-field evidence.

    Fields whose evidence quote is not found verbatim in the text are nulled —
    the model cannot invent a number that survives this check.
    """
    from .llm import complete
    data = complete(EXTRACT_SYSTEM, text[:24000], json_object=True)
    evidence = data.pop("evidence", {}) or {}
    hay = " ".join(text.split()).lower()
    for k, quote in list(evidence.items()):
        if data.get(k) is not None:
            q = " ".join(str(quote).split()).lower()
            if not q or q not in hay:
                data[k] = None
                evidence[k] = f"[UNGROUNDED, dropped] {quote}"
    data["extracted_from"] = [f"{source_name}: {k} — \"{v}\"" for k, v in evidence.items()]
    return data
