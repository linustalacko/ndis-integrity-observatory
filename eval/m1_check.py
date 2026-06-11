"""M1 acceptance: compliance engine agrees with the real Ku-ring-gai report.

Gold values transcribed from data/seeds/mcintyre/assessment_report.pdf
(pp 17-19): FSR 2.71:1 NO (+23.29%), affordable < 10% NO, height 30.48m vs
26.4m NO (breach 4.08m), site area YES, landscaped area YES.

Run: uv run python eval/m1_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.compliance import evaluate_seed  # noqa: E402
from app.proposal import load_seed  # noqa: E402

GOLD = {
    "Floor Space Ratio": (False, "2.71"),
    "Affordable housing component (SEPP Housing s16(2))": (False, "9.6"),
    "Height of Building": (False, "30.48"),
    "Site area (SEPP Housing s19, non-discretionary)": (True, "3360.1"),
    "Minimum landscaped area (SEPP Housing s19, non-discretionary)": (True, "1572"),
}


def main() -> int:
    findings = {f.control: f for f in evaluate_seed(load_seed("data/seeds/mcintyre"))}
    failures = []
    for control, (complies, value_substr) in GOLD.items():
        f = findings.get(control)
        if f is None:
            failures.append(f"MISSING: {control}")
        elif f.complies is not complies:
            failures.append(f"DISAGREE on complies: {control} -> {f.complies}, gold {complies}")
        elif value_substr not in f.proposed:
            failures.append(f"VALUE mismatch: {control} -> {f.proposed!r} missing {value_substr!r}")
    fsr = findings.get("Floor Space Ratio")
    if fsr and "23.29" not in (fsr.breach_magnitude or ""):
        failures.append(f"FSR breach magnitude {fsr.breach_magnitude!r}, gold +23.29%")
    hob = findings.get("Height of Building")
    if hob and "4.08" not in (hob.breach_magnitude or ""):
        failures.append(f"HOB breach magnitude {hob.breach_magnitude!r}, gold 4.08 m")
    if failures:
        print("M1 FAIL:")
        for x in failures:
            print(" -", x)
        return 1
    print(f"M1 PASS: {len(GOLD)}/{len(GOLD)} rows agree with the real report "
          "(values, pass/fail, breach magnitudes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
