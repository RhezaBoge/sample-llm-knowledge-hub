# How Project Knowledge Hub is built

This document explains the architecture, the data flow and the main design decisions.
It is meant for people who want to understand, adapt or extend the system.

**Contents:** [Purpose](#1-purpose) · [Architecture](#2-architecture) · [Containers](#3-containers) ·
[Processing pipeline](#4-processing-pipeline) · [Data model](#5-data-model) · [API](#6-api) ·
[Frontend](#7-frontend) · [Configuration](#8-configuration) · [Design decisions](#9-design-decisions-and-limitations) ·
[Tests and CI](#10-tests-and-ci) · [Extending](#11-extending-the-system)

---

## 1. Purpose

Organizations keep most of their project knowledge in documents: proposals, reports, meeting
notes. These are hard to search, compare or map. The system shows a simple pattern for using a
**local language model (LLM)** to turn such documents into **structured records**:

1. People define *which* facts to collect – the **template**.
2. The LLM reads a document and proposes values for each field.
3. Deterministic code cleans the values and finds the places on a map.
4. A person reviews and corrects the record.
5. The record is stored in a SQL database and exported as **GeoJSON**.

The LLM is used for the one thing it is good at – reading unstructured text – and nothing else.
Everything that must be exact (formats, coordinates, storage) is done by ordinary code.

---

## 2. Architecture

```
 ┌──────────────────────── the user's computer (Docker) ─────────────────────────┐
 │                                                                               │
 │   Browser ──► frontend (Vite + React)  ──/api/*──►  backend (FastAPI)          │
 │   :5173        serves the web app        proxy       :8000                     │
 │                                                        │      │                │
 │                                          SQLAlchemy ◄──┘      └──► ollama      │
 │                                          data/knowledge.db        (local LLM,  │
 │                                          (SQLite file)             OpenAI API) │
 └──────────────────────────────────────────────────────────┬────────────────────┘
                                                            │ place names only
                                         Internet ──────────┼──────────────────────
                                                            ▼
                                   OpenStreetMap Nominatim (geocoding)
                                   OpenStreetMap tiles (map background, from the browser)
```

| Layer | Technology | Code |
|---|---|---|
| Web app | React 19, Vite, Leaflet / react-leaflet | `frontend/src/` |
| API | FastAPI, Pydantic | `backend/app/main.py` |
| Storage | SQLAlchemy 2 + SQLite (any SQLAlchemy database works) | `backend/app/models.py`, `database.py` |
| Language model | Ollama running `qwen2.5:3b` by default, called through the OpenAI-compatible API | `backend/app/llm.py` |
| Geocoding | OpenStreetMap Nominatim | `backend/app/geocoder.py`, `locator.py` |
| File reading | pypdf, python-docx | `backend/app/text_reader.py` |
| Packaging | Docker Compose, start/stop scripts | `docker-compose.yml`, `start.*`, `stop.*` |

---

## 3. Containers

`docker-compose.yml` defines four services:

| Service | Image | Purpose | Port on the host |
|---|---|---|---|
| `frontend` | built from `frontend/Dockerfile` (Node 22) | Vite dev server; forwards `/api/*` to the backend | `127.0.0.1:5173` (`APP_PORT`) |
| `backend` | built from `backend/Dockerfile` (Python 3.12) | FastAPI with `uvicorn --reload` | `127.0.0.1:8000` (`API_PORT`) |
| `ollama` | `ollama/ollama` | runs the language model on the CPU | none (internal only) |
| `ollama-pull` | `ollama/ollama` | one-off job that downloads the model; profile `setup` | none |

Choices made for running on personal laptops:

- **`restart: "no"`** on every service – nothing starts when the computer boots.
- **Ports bound to `127.0.0.1`** – the app is not reachable from other devices on the network.
  `APP_PORT` and `API_PORT` in `.env` change the host ports when 5173 or 8000 are already in use.
  Ollama has no published port at all; only the backend can reach it.
- **`OLLAMA_KEEP_ALIVE=5m`** – the model is unloaded from memory 5 minutes after the last request.
- **`OLLAMA_CONTEXT_LENGTH=8192`** – enough context for a document of about 12,000 characters plus the prompt.
- **Volumes:** `./data` holds the SQLite file; the named volume `ollama_models` holds the model;
  `backend/app` and `frontend/src` are mounted so code changes reload immediately.

`start.sh` / `start.bat` check that Docker is running, create `.env` from `.env.example`, start
`backend` and `frontend`, start `ollama` and run `ollama-pull` only when the model is missing,
wait for `/api/health`, and open the browser. `stop.*` runs `docker compose --profile setup down`.

---

## 4. Processing pipeline

### 4.1 Template

The template is the list of fields every project has. It lives in the database
(table `template_fields`, plus the separator in `settings`) and is edited on the
*Set up your fields* page. On first start `template.seed_defaults()` inserts nine fields:

| Key | Label | Type | Several values |
|---|---|---|---|
| `title` | Project title | text | no |
| `organization` | Implementing organization | text | yes |
| `country` | Country | text | yes |
| `city` | City | text | yes |
| `start_date` | Start date | date | no |
| `end_date` | End date | date | no |
| `summary` | Summary | text | no |
| `keywords` | Keywords | text | yes |
| `sdgs` | SDGs | text | yes |

Each field also has a **prompt** – its instruction for the LLM. `template.validate()` checks the
template before saving: every field needs a label and a prompt; keys must match
`^[a-z][a-z0-9_]{0,39}$` and be unique; the separator is 1–3 characters. A missing key is generated
from the label (`"Donor name"` → `donor_name`).

### 4.2 Reading the document

`text_reader.read_document()` turns an upload into plain text: `.md` / `.txt` are decoded as UTF-8,
`.pdf` uses pypdf, `.docx` uses python-docx (paragraphs and tables). Scanned PDFs contain no text
layer and are rejected with a clear message. Markdown is recommended because it keeps headings,
lists and tables as clean text; Google Docs can export it directly.

### 4.3 Building the prompt

`extractor.build_prompt()` builds the prompt **from the template**, so changing a field's
instruction on the web page changes what the model is asked. For the default template the user
message looks like this (shortened):

```
Extract the project information from the document below.

Return JSON with exactly these keys:
{
  "title": "<project title>",
  "organization": ["<implementing organization>"],
  ...
}

What each key means:
- title (Project title): The name of the project, exactly as written in the document. One value only.
- organization (Implementing organization): The organization or organizations that implement
  the project. Do not include the donor. Several values are allowed - return a JSON list.
- start_date (Start date): When the project started or will start. One value only.
  Format: YYYY-MM-DD, YYYY-MM or YYYY.
...

DOCUMENT:
"""<the first 12,000 characters of the document>"""
```

The system message tells the model to use only information from the document, to answer `null`
when a value is missing, to write in English, and to return one JSON object. The *Show the AI
prompt* button on the template page displays the exact text (`POST /api/template/prompt`).

### 4.4 Calling the model

`llm.chat_json()` sends one request to `{LLM_BASE_URL}/chat/completions` with plain `httpx`:

- `temperature: 0` for the most repeatable output;
- `response_format: {"type": "json_object"}` to force valid JSON (retried once without it if the
  provider answers HTTP 400);
- errors are translated into readable messages (cannot connect, model not found, invalid key,
  rate limit, timeout).

`llm.parse_json()` removes Markdown code fences and any text around the JSON object before parsing.
Because only the OpenAI-compatible endpoint is used, the same code works with Ollama, Groq,
OpenRouter, Google Gemini, LM Studio or OpenAI by changing three settings.

**Alternative without AI:** `extractor.extract_with_rules()` uses regular expressions – lines such as
`Field label: value`, years for dates, a list of country names, frequent words as keywords. It is
fast and predictable but misses most information in free text or other languages. It exists for
comparison and as a fallback when no model is available.

### 4.5 Cleaning and validation

`template.normalize()` turns the raw model output into a predictable record and a list of warnings:

- `split_values()` accepts a string, a list or a number, splits on the separator (`;` by default),
  trims and removes duplicates;
- placeholder answers such as `null`, `n/a`, `not mentioned` or a copied `<project title>` become empty;
- **date** fields are converted to ISO 8601 (`March 2022` → `2022-03`, `28 February 2025` → `2025-02-28`);
- **number** fields understand thousands separators and words (`1.850.000`, `USD 1.5 million`);
- *several values* fields are stored as JSON lists; single-value fields as one value
  (with a warning if the model returned more than one);
- warnings are added for an end date before the start date and for every field that was not found.

### 4.6 Placing the project on the map

Language models are unreliable with coordinates: in tests a 7B model placed villages hundreds of
kilometres away and gave different villages identical coordinates. So the model only extracts
**place names**, and `locator.locate()` looks them up:

1. Take the values of the `city` field; if there are none, use the `country` values.
2. For each name, `geocoder.geocode()` queries Nominatim with `name, country` and takes the best match.
   Administrative words that hurt matching (`Desa`, `Kabupaten`, `District`, `County`, …) are removed first.
3. Requests are limited to one per second and cached in memory, following the
   [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/).
4. Places that are not found are listed as warnings.

Only the place names are sent to Nominatim – never the document. Set `GEOCODER=none` to disable it.

### 4.7 GeoJSON

`template.to_geojson()` produces one GeoJSON `Feature` per project:

- `geometry` is `null` (no places), a `Point` (one place) or a `MultiPoint` (several), with
  coordinates in GeoJSON order `[longitude, latitude]`;
- `properties` contains `project_id`, every template field, the `locations` list
  (name, latitude, longitude, matched OpenStreetMap name) and `source`
  (document name, extraction method, model, time, `reviewed_by_human`).

`GET /api/geojson` returns all projects as a `FeatureCollection`, which opens directly in QGIS,
ArcGIS, Google Earth or geojson.io.

### 4.8 Review and save

The extraction result is never saved automatically. The review form shows every field; while the
user edits, the frontend calls `POST /api/preview` (debounced 1.2 s) to re-run normalization,
geocoding and GeoJSON generation, so warnings and the map stay current. Saving requires ticking
*"I have checked this data against the document"*.

On save, `main._apply()` normalizes the record again on the server, geocodes it, copies the title
and first country into indexed columns, builds a search text from all values, assigns the project
code `PRJ-0001`, `PRJ-0002`, … and stores the GeoJSON with `reviewed_by_human: true`.

---

## 5. Data model

**`template_fields`**

| Column | Type | Notes |
|---|---|---|
| `id` | integer | primary key |
| `key` | text, unique | JSON property name |
| `label` | text | shown in the app |
| `prompt` | text | instruction for the model |
| `type` | text | `text`, `date` or `number` |
| `multiple` | boolean | several values allowed |
| `position` | integer | display and prompt order |

**`settings`** – key/value pairs; currently only `separator`.

**`projects`**

| Column | Type | Notes |
|---|---|---|
| `id` | integer | primary key; the project code is `PRJ-` + id |
| `title` | text | display title (the `title` field, or the first filled field) |
| `country` | text, indexed | first country, for filtering and statistics |
| `search_text` | text | all values joined, for full-text `LIKE` search |
| `record` | JSON | `{field key: value}` exactly as defined by the template |
| `locations` | JSON | geocoded places |
| `geojson` | JSON | the complete GeoJSON Feature |
| `source_filename`, `source_text` | text | the original document, kept for review and search |
| `extraction_method`, `model`, `extracted_at` | text | provenance |
| `created_at`, `updated_at` | timestamp | |

Changing the template does not rewrite existing projects: removed fields stay in old records,
new fields are empty until a project is edited and saved again.

---

## 6. API

Interactive documentation is available at <http://localhost:8000/docs> while the app runs.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | model reachability, model downloaded, geocoder on/off |
| GET | `/api/template` | fields, separator, number of saved projects |
| PUT | `/api/template` | replace the whole template |
| POST | `/api/template/reset` | restore the 9 default fields |
| POST | `/api/template/prompt` | the prompt the model would receive |
| GET | `/api/samples`, `/api/samples/{name}` | sample documents |
| POST | `/api/read-file` | upload → plain text |
| POST | `/api/extract` | text → record, warnings, locations, GeoJSON, raw model output (`method`: `llm` or `rules`) |
| POST | `/api/preview` | re-validate an edited record |
| GET | `/api/projects?q=&country=` | list and search |
| POST | `/api/projects` | create |
| GET / PUT / DELETE | `/api/projects/{id}` | read, update, delete |
| GET | `/api/projects/{id}/geojson` | download one Feature |
| GET | `/api/geojson?q=&country=` | download a FeatureCollection |
| GET | `/api/stats` | counts per country, number of mapped places |

---

## 7. Frontend

A single-page React app without a router; the current page is kept in the URL hash
(`#setup`, `#add`, `#kb`).

| File | Responsibility |
|---|---|
| `App.jsx` | header, navigation, model status (polled every 15 s), loads the template |
| `pages/TemplateSetup.jsx` | edit, reorder, add and remove fields; separator; prompt preview |
| `pages/AddProject.jsx` | upload or sample → extract → review form + map / GeoJSON / document / raw answer → save |
| `pages/KnowledgeBase.jsx` | statistics, search, country filter, map of all projects, table, detail panel |
| `components/RecordForm.jsx` | review form generated from the template |
| `components/ProjectMap.jsx` | Leaflet map with OpenStreetMap tiles |
| `components/Common.jsx` | warnings, code block with copy, tabs, inline confirm button |
| `api.js` | all HTTP calls |
| `styles.css` | design tokens (colours, spacing) and all styles; light theme only |

Values with several items are shown and edited as text joined by the separator
(`Lodwar; Kakuma`) and split again by the backend.

---

## 8. Configuration

All settings are environment variables, read from `.env` (copied from `.env.example` on first start).

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `http://ollama:11434/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `qwen2.5:3b` | model name |
| `LLM_API_KEY` | empty | for cloud providers |
| `LLM_TIMEOUT_SECONDS` | `300` | maximum time per extraction |
| `MAX_DOCUMENT_CHARS` | `12000` | longer documents are cut (with a warning) |
| `GEOCODER` | `nominatim` | `none` disables place lookup |
| `GEOCODER_URL` | Nominatim search URL | e.g. a self-hosted Nominatim |
| `APP_PORT` | `5173` | host port of the web app |
| `API_PORT` | `8000` | host port of the API |
| `DATABASE_URL` | `sqlite:///./data/knowledge.db` | any SQLAlchemy URL |

---

## 9. Design decisions and limitations

- **LLM for reading only.** The model proposes values; code enforces formats; geocoding uses a
  gazetteer; a person approves. This keeps errors visible and the data trustworthy.
- **Template in the database, prompt generated from it.** Non-programmers can change what is
  collected and how the model is asked, without touching code.
- **Local model by default.** Documents never leave the computer. A 3B model is a compromise
  between quality and laptop resources; a 7B model is noticeably better if 16 GB RAM is available.
- **SQLite.** One file, no server, easy to back up. For several users, switch `DATABASE_URL` to PostgreSQL.
- **No user accounts.** The app is designed for one person on their own computer and only listens on
  `localhost`. It is **not** hardened for a shared server: there is no authentication, and it runs
  the Vite and uvicorn development servers so code changes reload instantly.
- **Context limit.** Only the first `MAX_DOCUMENT_CHARS` characters are read. Long documents would
  need chunking (extract per section, then merge).
- **Geocoding ambiguity.** Places with the same name in one country can be confused. Adding the
  region to the City value (`Lewa, East Sumba`) helps; the map review catches the rest.
- **Language.** Prompts ask for English values; small models are weaker in some languages.

---

## 10. Tests and CI

`backend/tests/test_app.py` (pytest) covers value normalization, multi-value splitting, date and
number parsing, GeoJSON geometry types, JSON parsing of model output, the template API (save,
validation, prompt preview, reset), extraction with a fake model and fake geocoder, and the
project lifecycle (create, search, filter, statistics, export, delete). Tests set `GEOCODER=none`
and never call the internet or a real model.

`.github/workflows/ci.yml` runs on every push and pull request: backend tests, frontend production
build, and a Docker build of both images.

---

## 11. Extending the system

| Goal | Where to change |
|---|---|
| New default fields | `DEFAULT_FIELDS` in `backend/app/template.py` |
| New field type (e.g. `url`, `email`) | `FIELD_TYPES` and `normalize()` in `template.py`, `TYPE_HINTS` in `extractor.py` and `RecordForm.jsx` |
| Better prompts (examples, stricter rules) | `SYSTEM_PROMPT` and `build_prompt()` in `extractor.py` |
| Another LLM provider | `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in `.env` |
| Long documents | split the text in `main.extract()` and merge the per-chunk records |
| PostgreSQL / PostGIS | add a `db` service to `docker-compose.yml`, set `DATABASE_URL`, add `psycopg` to `requirements.txt` |
| Batch import of a folder | a script that calls `/api/extract` and `/api/projects` per file, saving with `reviewed_by_human: false` |
| Deploy for a team | add authentication, build the frontend (`npm run build`) and serve it with a web server, run uvicorn without `--reload`, use PostgreSQL |
