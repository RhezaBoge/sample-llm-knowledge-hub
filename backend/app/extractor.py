"""
Two ways to turn a document into a (messy) dictionary {field key: value}:

1. extract_with_llm()   - ask a language model. The prompt is BUILT FROM THE
                          TEMPLATE: every field brings its own instruction.
2. extract_with_rules() - classic keyword rules, no AI at all.

Both return a plain dict. `template.normalize()` then cleans it up.
"""

import json
import re

from . import config, llm

# --------------------------------------------------------------------------
# 1) The LLM way
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a careful data assistant for an NGO.
You read project documents and extract key facts as JSON.
Rules:
- Use ONLY information written in the document. Never invent facts.
- If a value is not in the document, use null.
- Write all values in English, even if the document is in another language.
- Return ONLY one JSON object and nothing else."""

TYPE_HINTS = {
    "text": "",
    "date": "Format: YYYY-MM-DD, YYYY-MM or YYYY.",
    "number": "A plain number without currency symbols or thousands separators.",
}


def build_prompt(text: str, fields: list[dict], separator: str) -> tuple[str, str]:
    """Turn the template into the question we ask the model."""
    template = {}
    instructions = []
    for f in fields:
        placeholder = f"<{f['label'].lower()}>"
        template[f["key"]] = [placeholder] if f["multiple"] else placeholder
        count = "Several values are allowed - return a JSON list." if f["multiple"] else "One value only."
        instructions.append(f"- {f['key']} ({f['label']}): {f['prompt']} {count} {TYPE_HINTS[f['type']]}".rstrip())

    user = (
        "Extract the project information from the document below.\n\n"
        "Return JSON with exactly these keys:\n"
        f"{json.dumps(template, indent=2)}\n\n"
        "What each key means:\n"
        f"{chr(10).join(instructions)}\n\n"
        "DOCUMENT:\n\"\"\"\n"
        f"{text[: config.MAX_DOCUMENT_CHARS]}\n\"\"\""
    )
    return SYSTEM_PROMPT, user


def extract_with_llm(text: str, fields: list[dict], separator: str) -> tuple[dict, str]:
    system, user = build_prompt(text, fields, separator)
    return llm.chat_json(system, user)


# --------------------------------------------------------------------------
# 2) The "no AI" way: hand-written rules that work for ANY template
# --------------------------------------------------------------------------

COUNTRIES = [
    "Afghanistan", "Bangladesh", "Cambodia", "Colombia", "DR Congo", "Ethiopia", "Ghana", "Guatemala",
    "Haiti", "India", "Indonesia", "Jordan", "Kenya", "Lebanon", "Madagascar", "Malawi", "Mali",
    "Mozambique", "Myanmar", "Nepal", "Niger", "Nigeria", "Pakistan", "Peru", "Philippines", "Rwanda",
    "Senegal", "Sierra Leone", "Somalia", "South Sudan", "Sri Lanka", "Sudan", "Syria", "Tanzania",
    "Timor-Leste", "Uganda", "Ukraine", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
]

_STOPWORDS = set("""the a an and or of in on for to with by from at as is are was were be been this that these those
it its into their our we they project program programme report note notes draft example fictional
total about also has have had will which who than more most each per between during year years month months""".split())


def _line_after(label: str, text: str) -> str | None:
    """'Project title: X' -> 'X'. Tries the full label, then its key words."""
    words = [w for w in re.findall(r"[a-z]+", label.lower()) if w not in _STOPWORDS]
    patterns = [re.escape(label)] + [re.escape(w) for w in words if len(w) > 3]
    for pattern in patterns:
        match = re.search(rf"^[^\n:]{{0,40}}\b{pattern}\b[^\n:]{{0,40}}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def extract_with_rules(text: str, fields: list[dict], separator: str) -> dict:
    lower = text.lower()
    years = sorted(set(re.findall(r"\b(20\d{2})\b", text)))
    first_lines = [line.strip() for line in text.splitlines() if line.strip()]
    result = {}

    for f in fields:
        key, label = f["key"], f["label"]
        value = _line_after(label, text)

        if value is None and f["type"] == "date":
            if "start" in key or "begin" in key:
                value = years[0] if years else None
            elif "end" in key or "finish" in key:
                value = years[-1] if len(years) > 1 else None
        elif value is None and key in ("country", "countries"):
            found = [c for c in COUNTRIES if c.lower() in lower]
            value = found if f["multiple"] else (found[0] if found else None)
        elif value is None and key == "title":
            value = first_lines[0][:150] if first_lines else None
        elif value is None and key == "keywords":
            words = re.findall(r"[a-z]{5,}", lower)
            counts: dict[str, int] = {}
            for w in words:
                if w not in _STOPWORDS:
                    counts[w] = counts.get(w, 0) + 1
            value = [w for w, _ in sorted(counts.items(), key=lambda x: -x[1])[:5]]

        if isinstance(value, str) and f["multiple"]:
            value = [v.strip() for v in re.split(rf"{re.escape(separator)}|,", value) if v.strip()]
        result[key] = value
    return result
