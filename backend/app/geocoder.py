"""
Place name -> coordinates, using OpenStreetMap's free Nominatim service.

Why not just trust the LLM? Language models are good at *reading* place names
but bad at *knowing* coordinates: they often return the same point for every
village, or made-up numbers that look precise. A gazetteer (a database of
places) gives real coordinates.

Nominatim usage policy: max 1 request per second and a clear User-Agent.
https://operations.osmfoundation.org/policies/nominatim/
"""

import re
import time

import httpx

from . import config

# Words like "Desa" (village) or "Kabupaten" (regency) make OpenStreetMap searches fail
_ADMIN_WORDS = re.compile(
    r"\b(desa|kelurahan|kecamatan|kabupaten|kab\.|kota|provinsi|village|sub-district|district|"
    r"regency|county|province|municipality)\b", re.IGNORECASE)

_cache: dict[str, dict | None] = {}
_last_request = 0.0


def _search(query: str) -> dict | None:
    global _last_request
    if query in _cache:
        return _cache[query]
    wait = 1.0 - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        response = httpx.get(
            config.GEOCODER_URL,
            params={"q": query, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": config.GEOCODER_USER_AGENT},
            timeout=10,
        )
        results = response.json() if response.status_code == 200 else []
    except (httpx.HTTPError, ValueError):
        return None  # don't cache network errors
    hit = None
    if results:
        hit = {"latitude": round(float(results[0]["lat"]), 5),
               "longitude": round(float(results[0]["lon"]), 5),
               "display_name": results[0].get("display_name")}
    _cache[query] = hit
    return hit


def geocode(name: str, admin_area: str | None = None, country: str | None = None) -> dict | None:
    """Try the most precise query first, then simpler ones."""
    if not config.GEOCODER_ENABLED or not name:
        return None
    clean = lambda text: re.sub(r"\s+", " ", _ADMIN_WORDS.sub("", text or "")).strip(" ,") or None
    name, admin_area = clean(name) or name, clean(admin_area)
    queries = [
        ", ".join(p for p in (name, admin_area, country) if p),
        ", ".join(p for p in (name, country) if p),
    ]
    if admin_area:
        queries.append(", ".join(p for p in (admin_area, country) if p))
    for query in dict.fromkeys(queries):  # unique, keep order
        hit = _search(query)
        if hit:
            return {**hit, "query": query}
    return None

