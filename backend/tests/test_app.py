import os

os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
os.environ["GEOCODER"] = "none"  # tests must not call the internet

import pytest
from fastapi.testclient import TestClient

from app import config, extractor, llm, locator, template
from app.database import Base, engine
from app.main import app
from app.template import DEFAULT_FIELDS, DEFAULT_SEPARATOR, normalize, to_geojson


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:
        yield c


# --- Cleaning values ---------------------------------------------------------

def test_normalize_splits_multiple_values_and_cleans_types():
    record, warnings = normalize({
        "title": "Water project",
        "organization": "Tirta Lestari; Village Committee ; Tirta Lestari",
        "country": ["Indonesia"],
        "start_date": "March 2022",
        "end_date": "28 February 2025",
        "keywords": "water, hygiene",
        "summary": "<summary>",
    }, DEFAULT_FIELDS, DEFAULT_SEPARATOR)
    assert record["organization"] == ["Tirta Lestari", "Village Committee"]  # split, trimmed, de-duplicated
    assert record["country"] == ["Indonesia"]
    assert record["start_date"] == "2022-03"
    assert record["end_date"] == "2025-02-28"
    assert record["keywords"] == ["water, hygiene"]  # only ';' separates values
    assert record["summary"] is None  # placeholder copied by a small model
    assert any("Not found in the document: City, Summary, SDGs" in w for w in warnings)


def test_single_valued_field_with_several_values_warns():
    record, warnings = normalize({"title": ["A", "B"]}, DEFAULT_FIELDS, ";")
    assert record["title"] == "A; B"
    assert any("Project title should have one value" in w for w in warnings)


def test_bad_date_and_number_warn():
    fields = [{"key": "budget", "label": "Budget", "type": "number", "multiple": False, "prompt": "x"},
              {"key": "start_date", "label": "Start", "type": "date", "multiple": False, "prompt": "x"}]
    record, warnings = normalize({"budget": "USD 1.5 million", "start_date": "soon"}, fields, ";")
    assert record["budget"] == 1_500_000
    assert record["start_date"] is None
    assert any("could not understand the date 'soon'" in w for w in warnings)


def test_geojson_geometry_types():
    one = [{"name": "P", "latitude": 1, "longitude": 2}]
    two = one + [{"name": "Q", "latitude": 3, "longitude": 4}]
    assert to_geojson({}, [], one)["geometry"] == {"type": "Point", "coordinates": [2, 1]}  # [lon, lat]!
    assert to_geojson({}, [], two)["geometry"]["type"] == "MultiPoint"
    assert to_geojson({}, [], [])["geometry"] is None


def test_llm_json_parsing_handles_code_fences():
    assert llm.parse_json('Sure!\n```json\n{"title": "A"}\n```') == {"title": "A"}
    with pytest.raises(llm.LLMError):
        llm.parse_json("I could not find anything.")


# --- The template API ----------------------------------------------------------

def test_default_template_is_seeded(client):
    t = client.get("/api/template").json()
    assert [f["key"] for f in t["fields"]] == [f["key"] for f in DEFAULT_FIELDS]
    assert t["separator"] == ";"


def test_template_can_be_changed_and_reset(client):
    t = client.get("/api/template").json()
    fields = t["fields"][:3] + [{"label": "Donor", "prompt": "Who funds the project?", "type": "text", "multiple": True}]
    saved = client.put("/api/template", json={"fields": fields, "separator": "|"}).json()
    assert [f["key"] for f in saved["fields"]] == ["title", "organization", "country", "donor"]  # key made from label
    assert saved["separator"] == "|"

    bad = client.put("/api/template", json={"fields": fields + [{"label": "Donor", "prompt": "x"}], "separator": ";"})
    assert bad.status_code == 400 and "used twice" in bad.json()["detail"]

    prompt = client.post("/api/template/prompt", json={"fields": fields, "separator": "|"}).json()
    assert "- donor (Donor): Who funds the project?" in prompt["user"]

    reset = client.post("/api/template/reset").json()
    assert len(reset["fields"]) == len(DEFAULT_FIELDS) and reset["separator"] == ";"


# --- Extraction ----------------------------------------------------------------

def test_rules_extraction_on_sample(client):
    text = client.get("/api/samples/01_clean_water_east_sumba.txt").json()["text"]
    record = client.post("/api/extract", json={"text": text, "method": "rules"}).json()["record"]
    assert record["title"] == "Community Water Access and Hygiene for East Sumba"
    assert record["organization"] == ["Tirta Lestari Foundation"]
    assert record["country"] == ["Indonesia"]
    assert record["start_date"] == "2022" and record["end_date"] == "2025"


def test_llm_extraction_uses_template_and_locates_places(client, monkeypatch):
    fake = {"title": "Mangrove Demak", "country": "Indonesia", "city": ["Bedono", "Timbulsloko"], "start_date": "next year"}
    captured = {}

    def fake_chat(system, user):
        captured["user"] = user
        return fake, "{}"

    monkeypatch.setattr(extractor.llm, "chat_json", fake_chat)
    monkeypatch.setattr(config, "GEOCODER_ENABLED", True)
    monkeypatch.setattr(locator.geocoder, "geocode",
                        lambda name, admin, country: {"latitude": -6.9, "longitude": 110.5, "display_name": f"{name}, {country}"})

    result = client.post("/api/extract", json={"text": "some document", "method": "llm"}).json()
    assert "- city (City):" in captured["user"]  # the prompt is built from the template
    assert result["record"]["city"] == ["Bedono", "Timbulsloko"]
    assert result["geojson"]["geometry"]["type"] == "MultiPoint"
    assert any("2 place(s) were located" in w for w in result["warnings"])
    assert any("Start date: could not understand" in w for w in result["warnings"])


def test_save_list_search_and_download(client):
    record = {"title": "Girls Education Karnali", "organization": "Himalayan Learning Network",
              "country": "Nepal", "city": "Jumla; Kalikot", "keywords": "education; girls"}
    saved = client.post("/api/projects", json={"record": record, "extraction_method": "llm"}).json()
    assert saved["code"] == "PRJ-0001"
    assert saved["record"]["city"] == ["Jumla", "Kalikot"]
    assert saved["geojson"]["properties"]["source"]["reviewed_by_human"] is True

    assert len(client.get("/api/projects", params={"q": "kalikot"}).json()) == 1
    assert client.get("/api/projects", params={"country": "Kenya"}).json() == []
    assert client.get("/api/stats").json()["countries"] == [{"name": "Nepal", "count": 1}]

    collection = client.get("/api/geojson").json()
    assert collection["type"] == "FeatureCollection" and len(collection["features"]) == 1

    assert client.delete(f"/api/projects/{saved['id']}").status_code == 204
    assert client.get("/api/projects").json() == []
