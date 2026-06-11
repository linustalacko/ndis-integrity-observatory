"""ComplianceEngine: deterministic numeric checks, proposed vs permitted.

Numbers are computed in code, never generated. Each finding carries a citation
to where its requirement comes from.

CLI: python -m app.compliance data/seeds/mcintyre
"""
from __future__ import annotations

import json
import sys

from .models import Citation, ComplianceFinding
from .proposal import load_seed


def _pct_over(proposed: float, permitted: float) -> float:
    return (proposed - permitted) / permitted * 100


def evaluate_seed(seed: dict) -> list[ComplianceFinding]:
    p = seed["raw_proposal"]
    std = seed["effective_standards"]
    report = seed["case"]["source_report"]
    findings: list[ComplianceFinding] = []

    def cite(claim: str, ref: str) -> Citation:
        return Citation(claim=claim, source_type="document", source_ref=ref)

    site = p["site_area_m2"]

    # Floor space ratio (SEPP Housing s16 / KLEP cl 4.4 context)
    fsr_exact = p["gfa_m2"] / site
    fsr_proposed = round(fsr_exact, 2)
    fsr_base = std["fsr_base"]
    ok = fsr_exact <= fsr_base
    findings.append(ComplianceFinding(
        control="Floor Space Ratio",
        requirement=f"{fsr_base}:1 (base; uplift only with qualifying affordable housing)",
        proposed=f"{fsr_proposed}:1 ({p['gfa_m2']} m2 GFA / {site} m2 site)",
        complies=ok,
        breach_magnitude=None if ok else f"+{_pct_over(fsr_exact, fsr_base):.2f}% above base FSR",
        citation=cite(f"FSR standard {fsr_base}:1", f"{report} p18"),
    ))

    # Affordable housing percentage (gates any s16 bonus)
    aff_pct = round(p["affordable_gfa_m2"] / p["gfa_m2"] * 100, 1)
    min_pct = std["affordable_min_pct_for_bonus"]
    ok = aff_pct >= min_pct
    findings.append(ComplianceFinding(
        control="Affordable housing component (SEPP Housing s16(2))",
        requirement=f">= {min_pct}% of total GFA to access any FSR/height bonus",
        proposed=f"{aff_pct}% ({p['affordable_gfa_m2']} m2 of {p['gfa_m2']} m2)",
        complies=ok,
        breach_magnitude=None if ok else f"{min_pct - aff_pct:.1f} percentage points below minimum",
        citation=cite(f"s16(2) minimum {min_pct}%", f"{report} p18"),
    ))

    # Height of building
    h_prop, h_perm = p["proposed_height_m"], std["height_permitted_m"]
    ok = h_prop <= h_perm
    findings.append(ComplianceFinding(
        control="Height of Building",
        requirement=f"{h_perm} m (base {std['height_base_m']} m incl 20% bonus)",
        proposed=f"{h_prop} m ({p['storeys']} storeys)",
        complies=ok,
        breach_magnitude=None if ok else f"+{h_prop - h_perm:.2f} m ({_pct_over(h_prop, h_perm):.1f}%)",
        citation=cite(f"Permitted height {h_perm} m", f"{report} p19"),
    ))

    # Non-discretionary: site area
    ok = site >= std["site_area_min_m2"]
    findings.append(ComplianceFinding(
        control="Site area (SEPP Housing s19, non-discretionary)",
        requirement=f">= {std['site_area_min_m2']} m2",
        proposed=f"{site} m2",
        complies=ok,
        breach_magnitude=None,
        citation=cite("s19 minimum site area", f"{report} p17"),
    ))

    # Non-discretionary: landscaped area — lesser of 35 m2/dwelling or 30% of site
    landscape_req = round(min(35 * p["dwelling_count"], 0.30 * site), 1)
    ok = p["landscaped_area_m2"] >= landscape_req
    findings.append(ComplianceFinding(
        control="Minimum landscaped area (SEPP Housing s19, non-discretionary)",
        requirement=f">= {landscape_req} m2 ({std['landscape_min_rule']})",
        proposed=f"{p['landscaped_area_m2']} m2",
        complies=ok,
        breach_magnitude=None if ok else f"{landscape_req - p['landscaped_area_m2']:.1f} m2 short",
        citation=cite("s19 minimum landscaped area", f"{report} p17"),
    ))

    return findings


def render_table(findings: list[ComplianceFinding]) -> str:
    rows = ["| Control | Requirement | Proposed | Complies | Breach | Source |",
            "|---|---|---|---|---|---|"]
    for f in findings:
        c = {True: "YES", False: "NO", None: "REVIEW"}[f.complies]
        rows.append(f"| {f.control} | {f.requirement} | {f.proposed} | {c} | "
                    f"{f.breach_magnitude or '—'} | {f.citation.source_ref} |")
    return "\n".join(rows)


def main(argv: list[str]) -> int:
    seed_dir = argv[0] if argv else "data/seeds/mcintyre"
    seed = load_seed(seed_dir)
    findings = evaluate_seed(seed)
    print(f"# Compliance table — {seed['case']['da_ref']}, {seed['case']['address']}\n")
    print(render_table(findings))
    print()
    print(json.dumps([f.model_dump() for f in findings], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
