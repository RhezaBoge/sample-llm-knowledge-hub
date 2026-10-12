"""All settings come from environment variables (see .env.example)."""

import os

# Any "OpenAI-compatible" chat API works: Ollama (default, free & local), Groq,
# OpenRouter, Google Gemini's OpenAI endpoint, LM Studio, ...
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://ollama:11434/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))

# Small models have a small "context window", so very long documents are cut.
MAX_DOCUMENT_CHARS = int(os.getenv("MAX_DOCUMENT_CHARS", "12000"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/knowledge.db")

# Look up real coordinates for place names on OpenStreetMap (set GEOCODER=none to turn off).
GEOCODER_ENABLED = os.getenv("GEOCODER", "nominatim").lower() != "none"
GEOCODER_URL = os.getenv("GEOCODER_URL", "https://nominatim.openstreetmap.org/search")
GEOCODER_USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "project-knowledge-hub/0.2")
