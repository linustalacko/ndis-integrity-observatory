"""M1a: ABN Bulk Extract loader.

Streams the ABR XML parts and loads a slim subset into SQLite:
- every ABN whose normalised legal/main name matches an enforcement entity name, OR
- whose ABN appears in the enforcement register.

The full extract is ~10GB of XML across 20 files; we never hold it in memory.

CLI: python -m app.abr
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.etree.ElementTree import iterparse

from .db import connect
from .ingest import norm_name

ABR_DIR = Path(__file__).resolve().parent.parent / "data" / "abr"


def target_sets(conn) -> tuple[set[str], set[str]]:
    names = {r["norm_name"] for r in conn.execute("SELECT DISTINCT norm_name FROM actions")}
    # also index person names by 'first+last' token pair to survive middle names
    abns = {r["abn"] for r in conn.execute(
        "SELECT DISTINCT abn FROM actions WHERE abn != ''")}
    return names, abns


def name_keys(norm: str) -> set[str]:
    """Match keys for a normalised name: full string + first/last token pair."""
    toks = norm.split()
    keys = {norm}
    if 2 <= len(toks) <= 5:
        keys.add(f"{toks[0]} {toks[-1]}")
    return keys


def load(conn, zip_paths: list[Path]) -> int:
    names, abns = target_sets(conn)
    keys = set()
    for n in names:
        keys |= name_keys(n)
    print(f"matching against {len(keys)} name keys, {len(abns)} ABNs")
    inserted = 0
    for zp in zip_paths:
        with zipfile.ZipFile(zp) as z:
            for member in z.namelist():
                if not member.endswith(".xml"):
                    continue
                print(f"  scanning {member} ...", flush=True)
                with z.open(member) as f:
                    for _, elem in iterparse(f, events=("end",)):
                        if elem.tag != "ABR":
                            continue
                        abn_el = elem.find("ABN")
                        abn = (abn_el.text or "") if abn_el is not None else ""
                        status = abn_el.get("status", "") if abn_el is not None else ""
                        status_date = abn_el.get("ABNStatusFromDate", "") if abn_el is not None else ""
                        # main name: organisation or individual
                        name = ""
                        mn = elem.find("MainEntity/NonIndividualName/NonIndividualNameText")
                        if mn is not None and mn.text:
                            name = mn.text
                        else:
                            le = elem.find("LegalEntity/IndividualName")
                            if le is not None:
                                parts = [x.text or "" for x in le.findall("GivenName")]
                                fam = le.find("FamilyName")
                                if fam is not None:
                                    parts.append(fam.text or "")
                                name = " ".join(p for p in parts if p)
                        ent_type_el = elem.find("EntityType/EntityTypeInd")
                        ent_type = ent_type_el.text if ent_type_el is not None else ""
                        addr = elem.find("MainEntity/BusinessAddress/AddressDetails") \
                            if elem.find("MainEntity") is not None \
                            else elem.find("LegalEntity/BusinessAddress/AddressDetails")
                        state = pc = ""
                        if addr is not None:
                            st = addr.find("State"); p = addr.find("Postcode")
                            state = st.text or "" if st is not None else ""
                            pc = p.text or "" if p is not None else ""
                        nn = norm_name(name) if name else ""
                        # also hit on trading/other names so renamed entities surface
                        others = [o.text or "" for o in elem.findall(
                            "OtherEntity/NonIndividualName/NonIndividualNameText")]
                        other_norms = {norm_name(o) for o in others if o}
                        hit = (abn in abns or bool(nn and (name_keys(nn) & keys))
                               or bool(other_norms and any(
                                   name_keys(o) & keys for o in other_norms)))
                        if hit:
                            gst = elem.find("GST")
                            asic_el = elem.find("ASICNumber")
                            conn.execute(
                                "INSERT OR REPLACE INTO abns (abn, legal_name, entity_type, "
                                "abn_status, status_date, gst_status, state, postcode, "
                                "norm_name, asic_number, other_names, gst_from) "
                                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                (abn, name, ent_type, status, status_date,
                                 gst.get("status", "") if gst is not None else "",
                                 state, pc, nn,
                                 (asic_el.text or "") if asic_el is not None else "",
                                 " | ".join(o for o in others if o)[:500],
                                 gst.get("GSTStatusFromDate", "") if gst is not None else ""))
                            inserted += 1
                        elem.clear()
                conn.commit()
    return inserted


def main() -> int:
    conn = connect()
    zips = sorted(ABR_DIR.glob("part*.zip"))
    if not zips:
        print("no ABR zips found in data/abr/", file=sys.stderr)
        return 1
    n = load(conn, zips)
    print(f"\n{n} ABR records matched into abns table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
