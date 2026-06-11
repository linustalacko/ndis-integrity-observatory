"""ControlsRetriever: query ePlanning layers for a property and emit a cited ControlsContext.

CLI: python -m app.controls "26-30 McIntyre Street, Gordon NSW 2072"
"""
from __future__ import annotations

import datetime
import json
import sys

from .arcgis import PRINCIPAL_PATH, query_point
from .models import Citation, Control, ControlsContext, PropertyContext
from .property import resolve

# Principal Planning MapServer layer ids
LAYER_ZONING = 19
LAYER_HOB = 14
LAYER_FSR = 11
LAYER_LOT_SIZE = 22
LAYER_HERITAGE = 16
LAYER_SHR = 221
LAYER_LAND_RESERVATION = 24

STANDARD_LAYERS = [
    # (layer id, control name, value field, unit, LEP clause)
    (LAYER_HOB, "Height of Building", "MAX_B_H", "m", "cl 4.3"),
    (LAYER_FSR, "Floor Space Ratio", "FSR", ":1", "cl 4.4"),
    (LAYER_LOT_SIZE, "Minimum Lot Size", "LOT_SIZE", "m2", "cl 4.1"),
]


def _date(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).date().isoformat()


def retrieve(prop: PropertyContext) -> ControlsContext:
    ctx = ControlsContext()
    lon, lat = prop.lon, prop.lat

    zone_feats, zone_url = query_point(PRINCIPAL_PATH, LAYER_ZONING, lon, lat)
    if zone_feats:
        a = zone_feats[0]["attributes"]
        ctx.zone_code = a.get("SYM_CODE")
        ctx.zone_class = a.get("LAY_CLASS")
        ctx.lep_name = a.get("EPI_NAME")
        prop.lga = a.get("LGA_NAME")
        ctx.citations.append(Citation(
            claim=f"Zone {ctx.zone_code} ({ctx.zone_class}) under {ctx.lep_name}",
            source_type="arcgis", source_ref=zone_url,
            quote=f"SYM_CODE={ctx.zone_code}, LAY_CLASS={a.get('LAY_CLASS')}, "
                  f"currency {_date(a.get('CURRENCY_DATE'))}",
        ))

    for layer_id, name, field, unit, clause in STANDARD_LAYERS:
        feats, url = query_point(PRINCIPAL_PATH, layer_id, lon, lat)
        if not feats:
            continue
        a = feats[0]["attributes"]
        value = a.get(field)
        ctx.standards.append(Control(
            name=name, value=value, unit=unit, source_layer=url,
            epi_name=a.get("EPI_NAME"), currency_date=_date(a.get("CURRENCY_DATE")),
        ))
        ctx.citations.append(Citation(
            claim=f"{name} = {value} {unit} ({a.get('EPI_NAME')} {clause})",
            source_type="arcgis", source_ref=url,
            quote=f"{field}={value}, currency {_date(a.get('CURRENCY_DATE'))}",
        ))

    for layer_id, label in [(LAYER_HERITAGE, "Heritage (EPI)"),
                            (LAYER_SHR, "State Heritage Register"),
                            (LAYER_LAND_RESERVATION, "Land Reservation Acquisition")]:
        feats, url = query_point(PRINCIPAL_PATH, layer_id, lon, lat)
        for f in feats:
            a = f["attributes"]
            item = {"layer": label, **{k: v for k, v in a.items() if v not in (None, "")}}
            ctx.heritage.append(item)
            ctx.citations.append(Citation(
                claim=f"{label} affectation applies",
                source_type="arcgis", source_ref=url,
                quote=json.dumps({k: a.get(k) for k in ("H_NAME", "SIG", "LAY_CLASS", "EPI_NAME")
                                  if a.get(k)}),
            ))

    return ctx


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print('usage: python -m app.controls "<NSW address>"', file=sys.stderr)
        return 2
    prop = resolve(argv[0])
    controls = retrieve(prop)
    print(json.dumps({"property": prop.model_dump(exclude={"lot_geometry"}),
                      "controls": controls.model_dump()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
