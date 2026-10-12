"""
From the "city" and "country" fields to points on the map.

The AI only reads place NAMES from the document. The coordinates come from
OpenStreetMap (see geocoder.py), because language models are bad at knowing
where places are.
"""

from . import config, geocoder
from .template import MAP_KEYS, split_values


def locate(record: dict, separator: str) -> tuple[list[dict], list[str]]:
    """Returns (locations, notes). Each location: {name, latitude, longitude, found}."""
    if not config.GEOCODER_ENABLED or not MAP_KEYS & set(record):
        return [], []

    cities = split_values(record.get("city"), separator)
    countries = split_values(record.get("country"), separator)
    country = countries[0] if countries else None

    # Prefer cities; if there are none, show the country itself
    targets = [(city, country) for city in cities] or [(c, None) for c in countries]

    locations, notes = [], []
    for name, in_country in targets:
        hit = geocoder.geocode(name, None, in_country)
        if hit:
            locations.append({"name": name, "latitude": hit["latitude"], "longitude": hit["longitude"],
                              "found": hit.get("display_name")})
        else:
            notes.append(f"'{name}' was not found on OpenStreetMap, so it is not on the map. "
                         "Try another spelling or add the region, e.g. 'Lewa, East Sumba'.")
    if locations:
        notes.insert(0, f"{len(locations)} place(s) were located on OpenStreetMap - check on the map that the right place was found.")
    return locations, notes
