"""ArcGIS REST client with mapprod host fallback and disk caching."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

EPLANNING_HOSTS = [
    "mapprod3.environment.nsw.gov.au",
    "mapprod1.environment.nsw.gov.au",
    "mapprod2.environment.nsw.gov.au",
]
PRINCIPAL_PATH = "/arcgis/rest/services/ePlanning/Planning_Portal_Principal_Planning/MapServer"
SEPP_PATH = "/arcgis/rest/services/ePlanning/Planning_Portal_SEPP/MapServer"


def _cache_path(url: str, params: dict) -> Path:
    key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:24]
    return CACHE_DIR / f"{key}.json"


def get_json(url: str, params: dict, *, use_cache: bool = True, timeout: float = 30.0) -> dict:
    """GET with disk cache. Raises on HTTP or ArcGIS-level errors."""
    cp = _cache_path(url, params)
    if use_cache and cp.exists():
        return json.loads(cp.read_text())
    resp = httpx.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"ArcGIS error from {url}: {data['error']}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(data))
    return data


def query_point(service_path: str, layer_id: int, lon: float, lat: float,
                out_fields: str = "*", return_geometry: bool = False) -> tuple[list[dict], str]:
    """Query an ePlanning layer by point, trying each mapprod host.

    Returns (features, layer_url_used).
    """
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": json.dumps(return_geometry),
        "f": "json",
    }
    last_err: Exception | None = None
    for host in EPLANNING_HOSTS:
        url = f"https://{host}{service_path}/{layer_id}/query"
        try:
            data = get_json(url, params)
            return data.get("features", []), f"https://{host}{service_path}/{layer_id}"
        except Exception as e:  # try next host
            last_err = e
    raise RuntimeError(f"All ePlanning hosts failed for layer {layer_id}: {last_err}")


def query_url(url: str, params: dict) -> dict:
    """Generic cached query against any ArcGIS endpoint (e.g. SIX cadastre, addressing)."""
    return get_json(url, {**params, "f": "json"})
