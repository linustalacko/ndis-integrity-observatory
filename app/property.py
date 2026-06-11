"""PropertyResolver: address -> coordinates -> lot polygon(s)."""
from __future__ import annotations

import re

from .arcgis import query_url
from .models import PropertyContext

ADDRESS_LAYER = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "NSW_Geocoded_Addressing_Theme/FeatureServer/1/query"
)
CADASTRE_LOT_LAYER = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/9/query"
)


def _normalise(address: str) -> tuple[list[str], str]:
    """Return candidate address strings in the gazetteer's format (upper, no state/postcode).

    A ranged house number like 26-30 is expanded to its even or odd components,
    since the gazetteer stores individual address points.
    """
    a = address.upper().strip()
    a = re.sub(r",?\s*NSW\b.*$", "", a)
    a = a.replace(",", " ").strip()
    a = re.sub(r"\s+", " ", a)
    m = re.match(r"^(\d+)\s*-\s*(\d+)\s+(.*)$", a)
    if not m:
        return [a], a
    lo, hi, rest = int(m.group(1)), int(m.group(2)), m.group(3)
    return [f"{n} {rest}" for n in range(lo, hi + 1, 2)], a


def geocode(address: str) -> list[dict]:
    """Geocode to one or more address points: [{'address', 'lon', 'lat'}, ...]."""
    candidates, _ = _normalise(address)
    quoted = ",".join("'" + c.replace("'", "''") + "'" for c in candidates)
    data = query_url(ADDRESS_LAYER, {
        "where": f"address IN ({quoted})",
        "outFields": "address",
        "returnGeometry": "true",
        "outSR": 4326,
    })
    return [
        {"address": f["attributes"]["address"],
         "lon": f["geometry"]["x"], "lat": f["geometry"]["y"]}
        for f in data.get("features", [])
    ]


def lot_at(lon: float, lat: float, return_geometry: bool = False) -> dict | None:
    data = query_url(CADASTRE_LOT_LAYER, {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "lotidstring,planlabel",
        "returnGeometry": "true" if return_geometry else "false",
        "outSR": 4326,
    })
    feats = data.get("features", [])
    return feats[0] if feats else None


def resolve(address: str) -> PropertyContext:
    points = geocode(address)
    if not points:
        raise ValueError(f"Could not geocode address: {address!r}")
    _, display = _normalise(address)
    lots: list[str] = []
    geom = None
    for p in points:
        lot = lot_at(p["lon"], p["lat"], return_geometry=True)
        if lot:
            lid = lot["attributes"]["lotidstring"]
            if lid not in lots:
                lots.append(lid)
            geom = geom or lot.get("geometry")
    primary = points[0]
    return PropertyContext(
        address=display,
        lot_dp=lots[0] if lots else None,
        lots=lots,
        lon=primary["lon"],
        lat=primary["lat"],
        lot_geometry=geom,
    )
