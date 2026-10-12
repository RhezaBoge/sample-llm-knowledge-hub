"""
The data template
=================

Which fields does every project have? That is decided by people, not by the
AI, on the "Set up your fields" page. The template is stored in the database
so it can be changed without touching code.

Each field has:
  key       machine name used in JSON and GeoJSON, e.g. "start_date"
  label     name shown to people, e.g. "Start date"
  prompt    the instruction given to the AI for this field
  type      text | date | number
  multiple  True if the field may hold several values (separated by ";")

This file also does the "cleaning": `normalize()` takes whatever the AI (or a
person) typed and turns it into predictable values, with warnings.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Setting, TemplateField

FIELD_TYPES = ["text", "date", "number"]
DEFAULT_SEPARATOR = ";"

DEFAULT_FIELDS = [
    {"key": "title", "label": "Project title", "type": "text", "multiple": False,
     "prompt": "The name of the project, exactly as written in the document."},
    {"key": "organization", "label": "Implementing organization", "type": "text", "multiple": True,
     "prompt": "The organization or organizations that implement the project. Do not include the donor."},
    {"key": "country", "label": "Country", "type": "text", "multiple": True,
     "prompt": "The country or countries where the project takes place. Use the English name."},
    {"key": "city", "label": "City", "type": "text", "multiple": True,
     "prompt": "The cities, towns, districts or villages where the project activities take place."},
    {"key": "start_date", "label": "Start date", "type": "date", "multiple": False,
     "prompt": "When the project started or will start."},
    {"key": "end_date", "label": "End date", "type": "date", "multiple": False,
     "prompt": "When the project ended or will end."},
    {"key": "summary", "label": "Summary", "type": "text", "multiple": False,
     "prompt": "What the project does and for whom, in at most two sentences, in English."},
    {"key": "keywords", "label": "Keywords", "type": "text", "multiple": True,
     "prompt": "Three to six short keywords that describe the themes of the project, in English."},
]

# Fields with these keys have a special job: they place the project on the map.
MAP_KEYS = {"country", "city"}

KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


# --------------------------------------------------------------------------
# Reading and writing the template
# --------------------------------------------------------------------------

def get_fields(db: Session) -> list[dict]:
    rows = db.scalars(select(TemplateField).order_by(TemplateField.position, TemplateField.id)).all()
    return [row.as_dict() for row in rows]


def get_separator(db: Session) -> str:
    row = db.get(Setting, "separator")
    return row.value if row and row.value else DEFAULT_SEPARATOR


def seed_defaults(db: Session) -> None:
    """Fill the template with the default fields if the table is empty."""
    if db.scalar(select(TemplateField.id).limit(1)) is None:
        save(db, DEFAULT_FIELDS, DEFAULT_SEPARATOR)


def reset(db: Session) -> None:
    db.execute(delete(TemplateField))
    save(db, DEFAULT_FIELDS, DEFAULT_SEPARATOR)


def slugify(label: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:40]
    if not key or not key[0].isalpha():
        key = "f_" + key
    return key[:40]


def validate(fields: list[dict], separator: str) -> list[dict]:
    """Check what the web page sent. Raises ValueError with a message for people."""
    if not fields:
        raise ValueError("The template needs at least one field.")
    if not separator.strip() or len(separator.strip()) > 3:
        raise ValueError("The separator must be 1 to 3 characters, for example ; or |")

    clean, seen = [], set()
    for i, f in enumerate(fields, start=1):
        label = (f.get("label") or "").strip()
        if not label:
            raise ValueError(f"Field {i} has no name.")
        key = (f.get("key") or "").strip() or slugify(label)
        if not KEY_RE.match(key):
            raise ValueError(f"'{key}' is not a valid key. Use lowercase letters, numbers and _ (start with a letter).")
        if key in seen:
            raise ValueError(f"The key '{key}' is used twice. Every field needs a different key.")
        seen.add(key)
        prompt = (f.get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"'{label}' needs an instruction for the AI.")
        ftype = f.get("type") or "text"
        if ftype not in FIELD_TYPES:
            raise ValueError(f"'{label}' has an unknown type '{ftype}'.")
        clean.append({"key": key, "label": label, "prompt": prompt, "type": ftype, "multiple": bool(f.get("multiple"))})
    return clean


def save(db: Session, fields: list[dict], separator: str) -> None:
    """Replace the whole template (order = order of the list)."""
    clean = validate(fields, separator)
    existing = {row.key: row for row in db.scalars(select(TemplateField)).all()}
    for position, f in enumerate(clean):
        row = existing.pop(f["key"], None) or TemplateField(key=f["key"])
        row.label, row.prompt, row.type, row.multiple, row.position = f["label"], f["prompt"], f["type"], f["multiple"], position
        db.add(row)
    for row in existing.values():  # fields that were removed on the page
        db.delete(row)
    setting = db.get(Setting, "separator") or Setting(key="separator")
    setting.value = separator.strip()
    db.add(setting)
    db.commit()


# --------------------------------------------------------------------------
# Cleaning values
# --------------------------------------------------------------------------

_EMPTY = {"", "null", "none", "n/a", "na", "unknown", "not specified", "not mentioned", "not available", "not stated", "-"}

_MULTIPLIERS = {
    "k": 1e3, "thousand": 1e3, "ribu": 1e3,
    "m": 1e6, "mn": 1e6, "million": 1e6, "juta": 1e6,
    "bn": 1e9, "billion": 1e9, "miliar": 1e9, "milyar": 1e9,
}

_DATE_FORMATS = {
    "%Y-%m-%d": "%Y-%m-%d", "%Y/%m/%d": "%Y-%m-%d", "%d/%m/%Y": "%Y-%m-%d", "%d-%m-%Y": "%Y-%m-%d",
    "%d %B %Y": "%Y-%m-%d", "%d %b %Y": "%Y-%m-%d", "%B %d, %Y": "%Y-%m-%d", "%B %d %Y": "%Y-%m-%d",
    "%Y-%m": "%Y-%m", "%B %Y": "%Y-%m", "%b %Y": "%Y-%m", "%m/%Y": "%Y-%m",
}


def _text(value) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    # Small models sometimes copy the placeholder, e.g. "<project name>"
    if s.lower() in _EMPTY or (s.startswith("<") and s.endswith(">")):
        return None
    return s


def _number(value: str) -> float | None:
    s = value.lower().replace(",", "").strip()
    if s.count(".") > 1:  # "1.850.000" (Indonesian/European thousands separator)
        s = s.replace(".", "")
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*([a-z]+)?", s)
    if not match:
        return None
    number = float(match.group(1)) * _MULTIPLIERS.get(match.group(2) or "", 1)
    return int(number) if number.is_integer() else number


def _date(value: str) -> str | None:
    if re.fullmatch(r"\d{4}", value):
        return value
    for in_fmt, out_fmt in _DATE_FORMATS.items():
        try:
            return datetime.strptime(value, in_fmt).strftime(out_fmt)
        except ValueError:
            continue
    year = re.search(r"\b(19|20)\d{2}\b", value)
    return year.group(0) if year else None


def _date_before(a: str, b: str) -> bool:
    """True if partial ISO date `a` is clearly before `b` ("2024" vs "2024-06" is not)."""
    n = min(len(a), len(b))
    return a[:n] < b[:n]


def split_values(value, separator: str) -> list[str]:
    """Anything -> a clean list of strings. 'a; b' -> ['a', 'b'], ['a', 'a'] -> ['a']."""
    if value is None:
        return []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if not isinstance(value, list):
        value = [value]
    result, seen = [], set()
    for item in value:
        text = _text(item)
        if text is None:
            continue
        for part in (text.split(separator) if separator else [text]):
            part = part.strip()
            if part and part.lower() not in seen:
                seen.add(part.lower())
                result.append(part)
    return result


def normalize(raw: dict, fields: list[dict], separator: str) -> tuple[dict, list[str]]:
    """Messy dict (from the AI or a form) -> clean record {key: value} + warnings."""
    raw = raw if isinstance(raw, dict) else {}
    record: dict = {}
    warnings: list[str] = []

    for f in fields:
        key, label, ftype = f["key"], f["label"], f["type"]
        values: list = []
        for text in split_values(raw.get(key), separator):
            if ftype == "date":
                value = _date(text)
                if value is None:
                    warnings.append(f"{label}: could not understand the date '{text}'.")
            elif ftype == "number":
                value = _number(text)
                if value is None:
                    warnings.append(f"{label}: '{text}' is not a number.")
            else:
                value = text
            if value is not None:
                values.append(value)

        if f["multiple"]:
            record[key] = values
        elif not values:
            record[key] = None
        else:
            if len(values) > 1:
                warnings.append(f"{label} should have one value but {len(values)} were found - please keep only one.")
            record[key] = f"{separator} ".join(str(v) for v in values) if ftype == "text" else values[0]

    start, end = record.get("start_date"), record.get("end_date")
    if isinstance(start, str) and isinstance(end, str) and _date_before(end, start):
        warnings.append("End date is before start date - please check.")

    if "title" in record and not record["title"]:
        warnings.insert(0, "No project title found - please add one.")
    missing = [f["label"] for f in fields if f["key"] != "title" and record.get(f["key"]) in (None, [], "")]
    if missing:
        warnings.append("Not found in the document: " + ", ".join(missing) + ".")
    return record, warnings


def display_title(record: dict, fields: list[dict]) -> str:
    """The text shown in lists: the 'title' field, or else the first field."""
    keys = ["title"] + [f["key"] for f in fields]
    for key in keys:
        value = record.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        if value not in (None, ""):
            return str(value)[:300]
    return "Untitled project"


def search_text(record: dict) -> str:
    parts = []
    for value in record.values():
        parts.extend(str(v) for v in (value if isinstance(value, list) else [value]) if v not in (None, ""))
    return "\n".join(parts)


# --------------------------------------------------------------------------
# GeoJSON
# --------------------------------------------------------------------------

def to_geojson(record: dict, fields: list[dict], locations: list[dict],
               project_id: str | None = None, source: dict | None = None) -> dict:
    # GeoJSON order is [longitude, latitude] - the opposite of what most people say out loud!
    points = [[loc["longitude"], loc["latitude"]] for loc in locations]
    if not points:
        geometry = None  # allowed by GeoJSON: a feature without a known place
    elif len(points) == 1:
        geometry = {"type": "Point", "coordinates": points[0]}
    else:
        geometry = {"type": "MultiPoint", "coordinates": points}

    feature: dict = {"type": "Feature"}
    if project_id:
        feature["id"] = project_id
    feature["geometry"] = geometry
    feature["properties"] = {
        "project_id": project_id,
        **{f["key"]: record.get(f["key"]) for f in fields},
        "locations": locations,
        "source": source or {},
    }
    return feature
