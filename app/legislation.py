"""LEP text access: Land Use Table parsing and Part 4 standards clause text.

legislation.nsw.gov.au sits behind a TLS-fingerprinting WAF that blocks
scripted fetches, so LEP text is captured once via a browser session into
data/lep/<slug>.json (keys: zone sections like "r4", plus cl41/cl43/cl44/cl46)
and parsed from there. The Standard Instrument structure makes the section
shapes consistent across councils.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LEP_DIR = Path(__file__).resolve().parent.parent / "data" / "lep"

# LEP name -> (cache slug, source URL)
KNOWN_LEPS = {
    "Ku-ring-gai Local Environmental Plan 2015": (
        "klep-2015",
        "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2015-0134",
    ),
}


def load_lep(lep_name: str) -> tuple[dict, str] | None:
    """Return (sections dict, source URL) for a cached LEP, or None."""
    entry = KNOWN_LEPS.get(lep_name)
    if not entry:
        return None
    slug, url = entry
    path = LEP_DIR / f"{slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text()), url


def parse_land_use_table(zone_section: str) -> dict:
    """Parse a Standard Instrument zone section into its land use lists."""
    def between(a: str, b: str | None) -> str:
        m = re.search(rf"\d\s+{a}\s*\n(.*?)(?=\n\d\s+{b}|\Z)" if b else rf"\d\s+{a}\s*\n(.*)",
                      zone_section, re.S)
        return m.group(1).strip() if m else ""

    def uses(text: str) -> list[str]:
        return [u.strip() for u in re.split(r"[;\n]", text) if u.strip()]

    return {
        "objectives": between("Objectives of zone", "Permitted without consent"),
        "permitted_without_consent": uses(between("Permitted without consent", "Permitted with consent")),
        "permitted_with_consent": uses(between("Permitted with consent", "Prohibited")),
        "prohibited": uses(between("Prohibited", None)),
    }


def land_use_table(lep_name: str, zone_code: str) -> dict | None:
    """Land use table for a zone, with source URL. None if LEP not cached."""
    loaded = load_lep(lep_name)
    if not loaded:
        return None
    sections, url = loaded
    section = sections.get(zone_code.lower())
    if not section:
        return None
    table = parse_land_use_table(section)
    table["source"] = url
    return table


def is_permissible(lep_name: str, zone_code: str, land_use: str) -> bool | None:
    """True/False if determinable from the Land Use Table, None if LEP/zone not cached.

    Standard Instrument zones with closed prohibition ("Any other development
    not specified...") make the with/without-consent lists exhaustive.
    """
    table = land_use_table(lep_name, zone_code)
    if not table:
        return None
    target = land_use.lower().rstrip("s")
    listed = [u.lower().rstrip("s") for u in
              table["permitted_with_consent"] + table["permitted_without_consent"]]
    if any(target == u or target in u for u in listed):
        return True
    prohibited = [u.lower() for u in table["prohibited"]]
    if any("any other development" in u for u in prohibited):
        return False
    return None


def clause_text(lep_name: str, clause: str) -> tuple[str, str] | None:
    """Return (text, source URL) for a cached standards clause like '4.3'."""
    loaded = load_lep(lep_name)
    if not loaded:
        return None
    sections, url = loaded
    key = "cl" + clause.replace(".", "")
    text = sections.get(key)
    return (text, url) if text else None
