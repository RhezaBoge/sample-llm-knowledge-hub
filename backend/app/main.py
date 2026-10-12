"""
Project Knowledge Hub - API

The pipeline:
  template (which fields?) -> document -> text -> extractor (LLM or rules)
  -> normalize -> locate on map -> human review -> SQL database -> map, search, download

Open http://localhost:8000/docs to try every endpoint in the browser.
"""

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import config, llm, template
from .database import Base, SessionLocal, engine, get_db
from .extractor import build_prompt, extract_with_llm, extract_with_rules
from .locator import locate
from .models import Project
from .text_reader import read_document

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "sample_documents"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # create the tables on first start
    with SessionLocal() as db:
        template.seed_defaults(db)    # ...and the default template
    yield


app = FastAPI(title="Project Knowledge Hub API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------

class TemplateBody(BaseModel):
    fields: list[dict]
    separator: str = template.DEFAULT_SEPARATOR


class ExtractRequest(BaseModel):
    text: str
    method: Literal["llm", "rules"] = "llm"
    filename: str | None = None


class PreviewRequest(BaseModel):
    record: dict


class SaveRequest(BaseModel):
    record: dict
    source_text: str | None = None
    source_filename: str | None = None
    extraction_method: str = "manual"
    model: str | None = None
    extracted_at: str | None = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source(document, method, model, extracted_at, reviewed: bool) -> dict:
    return {"document": document, "extraction_method": method, "model": model,
            "extracted_at": extracted_at, "reviewed_by_human": reviewed}


def _template(db: Session) -> tuple[list[dict], str]:
    return template.get_fields(db), template.get_separator(db)


def _summary(p: Project) -> dict:
    return {
        "id": p.id, "code": p.code, "title": p.title, "country": p.country,
        "record": p.record, "locations": p.locations,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _detail(p: Project) -> dict:
    return {
        **_summary(p),
        "geojson": p.geojson,
        "source_filename": p.source_filename,
        "source_text": p.source_text,
        "extraction_method": p.extraction_method,
        "model": p.model,
        "extracted_at": p.extracted_at,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def _apply(project: Project, body: SaveRequest, db: Session) -> None:
    fields, separator = _template(db)
    record, _ = template.normalize(body.record, fields, separator)
    locations, _ = locate(record, separator)
    countries = template.split_values(record.get("country"), separator)

    project.title = template.display_title(record, fields)
    project.country = countries[0] if countries else None
    project.search_text = template.search_text(record)
    project.record = record
    project.locations = locations
    project.source_text = body.source_text
    project.source_filename = body.source_filename
    project.extraction_method = body.extraction_method
    project.model = body.model
    project.extracted_at = body.extracted_at
    if project.geojson is None:
        project.geojson = {}
    db.flush()  # gives a new project its id, which we need for the project code
    project.geojson = template.to_geojson(record, fields, locations, project.code, _source(
        body.source_filename, body.extraction_method, body.model, body.extracted_at, reviewed=True))


def _filtered(q: str | None, country: str | None):
    stmt = select(Project).order_by(Project.updated_at.desc())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Project.search_text.ilike(like), Project.source_text.ilike(like),
                              Project.source_filename.ilike(like)))
    if country:
        stmt = stmt.where(Project.country == country)
    return stmt


# --------------------------------------------------------------------------
# Info
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "llm": llm.status(), "geocoder": config.GEOCODER_ENABLED}


@app.get("/api/samples")
def list_samples():
    return [p.name for p in sorted(SAMPLES_DIR.glob("*.txt"))]


@app.get("/api/samples/{name}")
def get_sample(name: str):
    if name not in list_samples():
        raise HTTPException(404, "Sample not found")
    return {"filename": name, "text": (SAMPLES_DIR / name).read_text(encoding="utf-8")}


# --------------------------------------------------------------------------
# Step 0: the template ("Set up your fields")
# --------------------------------------------------------------------------

@app.get("/api/template")
def get_template(db: Session = Depends(get_db)):
    fields, separator = _template(db)
    return {"fields": fields, "separator": separator, "map_keys": sorted(template.MAP_KEYS),
            "types": template.FIELD_TYPES, "projects": db.scalar(select(func.count(Project.id)))}


@app.put("/api/template")
def put_template(body: TemplateBody, db: Session = Depends(get_db)):
    try:
        template.save(db, body.fields, body.separator)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return get_template(db)


@app.post("/api/template/reset")
def reset_template(db: Session = Depends(get_db)):
    template.reset(db)
    return get_template(db)


@app.post("/api/template/prompt")
def preview_prompt(body: TemplateBody):
    """Show the exact question the AI will get for this template (for transparency)."""
    try:
        fields = template.validate(body.fields, body.separator)
    except ValueError as e:
        raise HTTPException(400, str(e))
    system, user = build_prompt("<the text of the document goes here>", fields, body.separator)
    return {"system": system, "user": user}


# --------------------------------------------------------------------------
# Steps 1-3: document -> text -> structured record -> GeoJSON preview
# --------------------------------------------------------------------------

@app.post("/api/read-file")
async def read_file(file: UploadFile = File(...)):
    try:
        text = read_document(file.filename or "", await file.read())
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not text.strip():
        raise HTTPException(400, "No text found in this file. Scanned PDFs need OCR first - try copying the text instead.")
    return {"filename": file.filename, "text": text, "characters": len(text)}


@app.post("/api/extract")
def extract(body: ExtractRequest, db: Session = Depends(get_db)):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "The document is empty.")
    fields, separator = _template(db)

    started = time.perf_counter()
    model = None
    if body.method == "rules":
        raw = extract_with_rules(text, fields, separator)
        raw_output = json.dumps(raw, indent=2, ensure_ascii=False)
    else:
        model = config.LLM_MODEL
        try:
            raw, raw_output = extract_with_llm(text, fields, separator)
        except llm.LLMError as e:
            return JSONResponse({"detail": e.message, "raw_output": e.raw_output}, status_code=e.status_code)

    record, warnings = template.normalize(raw, fields, separator)
    locations, notes = locate(record, separator)
    if len(text) > config.MAX_DOCUMENT_CHARS:
        notes.insert(0, f"The document is long, so only the first {config.MAX_DOCUMENT_CHARS:,} characters were read.")

    extracted_at = _now_iso()
    return {
        "method": body.method,
        "model": model,
        "seconds": round(time.perf_counter() - started, 1),
        "extracted_at": extracted_at,
        "raw_output": raw_output,
        "record": record,
        "warnings": notes + warnings,
        "locations": locations,
        "geojson": template.to_geojson(record, fields, locations, None,
                                       _source(body.filename, body.method, model, extracted_at, reviewed=False)),
    }


@app.post("/api/preview")
def preview(body: PreviewRequest, db: Session = Depends(get_db)):
    """Used while a person edits the form: re-check, re-locate and rebuild the GeoJSON."""
    fields, separator = _template(db)
    record, warnings = template.normalize(body.record, fields, separator)
    locations, notes = locate(record, separator)
    return {"record": record, "warnings": notes + warnings, "locations": locations,
            "geojson": template.to_geojson(record, fields, locations)}


# --------------------------------------------------------------------------
# The knowledge base (SQL)
# --------------------------------------------------------------------------

@app.get("/api/projects")
def list_projects(q: str | None = None, country: str | None = None, db: Session = Depends(get_db)):
    return [_summary(p) for p in db.scalars(_filtered(q, country))]


@app.post("/api/projects", status_code=201)
def create_project(body: SaveRequest, db: Session = Depends(get_db)):
    project = Project()
    db.add(project)
    _apply(project, body, db)
    db.commit()
    return _detail(project)


@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _detail(_get_project(db, project_id))


@app.put("/api/projects/{project_id}")
def update_project(project_id: int, body: SaveRequest, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    _apply(project, body, db)
    db.commit()
    return _detail(project)


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db.delete(_get_project(db, project_id))
    db.commit()


@app.get("/api/projects/{project_id}/geojson")
def download_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project(db, project_id)
    return JSONResponse(project.geojson, media_type="application/geo+json",
                        headers={"Content-Disposition": f'attachment; filename="{project.code}.geojson"'})


@app.get("/api/geojson")
def download_all(q: str | None = None, country: str | None = None, db: Session = Depends(get_db)):
    collection = {"type": "FeatureCollection", "features": [p.geojson for p in db.scalars(_filtered(q, country))]}
    return JSONResponse(collection, media_type="application/geo+json",
                        headers={"Content-Disposition": 'attachment; filename="projects.geojson"'})


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    """Simple SQL aggregation: COUNT and GROUP BY."""
    by_country = db.execute(
        select(Project.country, func.count()).group_by(Project.country).order_by(func.count().desc())).all()
    places = sum(len(p.locations or []) for p in db.scalars(select(Project)))
    return {
        "projects": db.scalar(select(func.count(Project.id))),
        "countries": [{"name": c, "count": n} for c, n in by_country if c],
        "places": places,
    }
