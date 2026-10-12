"""
Three SQL tables:

  template_fields  - the fields every project has (editable in the web app)
  settings         - small key/value settings, e.g. the separator ";"
  projects         - the knowledge base itself
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TemplateField(Base):
    __tablename__ = "template_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)      # machine name, e.g. "start_date"
    label: Mapped[str] = mapped_column(String(100))                # shown to people, e.g. "Start date"
    prompt: Mapped[str] = mapped_column(Text)                      # instruction for the AI
    type: Mapped[str] = mapped_column(String(10), default="text")  # text | date | number
    multiple: Mapped[bool] = mapped_column(Boolean, default=False) # may hold several values
    position: Mapped[int] = mapped_column(Integer, default=0)

    def as_dict(self) -> dict:
        return {"id": self.id, "key": self.key, "label": self.label, "prompt": self.prompt,
                "type": self.type, "multiple": self.multiple}


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Copied out of `record` so SQL can search, filter and count
    title: Mapped[str] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    search_text: Mapped[str] = mapped_column(Text, default="")

    # The structured data: {field key: value}, the map points, and the GeoJSON
    record: Mapped[dict] = mapped_column(JSON)
    locations: Mapped[list] = mapped_column(JSON, default=list)
    geojson: Mapped[dict] = mapped_column(JSON)

    # Where the data came from
    source_filename: Mapped[str | None] = mapped_column(String(300))
    source_text: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(20), default="manual")
    model: Mapped[str | None] = mapped_column(String(100))
    extracted_at: Mapped[str | None] = mapped_column(String(40))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    @property
    def code(self) -> str:
        return f"PRJ-{self.id:04d}"
