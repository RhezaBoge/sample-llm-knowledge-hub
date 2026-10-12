"""
A tiny client for any "OpenAI-compatible" chat API.

Works with Ollama (free, runs on your own computer), Groq, OpenRouter,
Google Gemini's OpenAI endpoint, LM Studio, OpenAI, ...

We call the API with plain HTTP (httpx) instead of an SDK, so you can see
exactly what is sent to the model and what comes back.
"""

import json
import re

import httpx

from . import config


class LLMError(Exception):
    def __init__(self, message: str, status_code: int = 502, raw_output: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.raw_output = raw_output


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    return headers


def chat_json(system: str, user: str) -> tuple[dict, str]:
    """Send one question to the model and return (parsed JSON, raw text answer)."""
    payload = {
        "model": config.LLM_MODEL,
        "temperature": 0,  # 0 = as predictable as possible, good for extraction
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        # Ask the server to force valid JSON (supported by Ollama, Groq, OpenAI, ...)
        "response_format": {"type": "json_object"},
    }
    url = f"{config.LLM_BASE_URL}/chat/completions"

    try:
        with httpx.Client(timeout=config.LLM_TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload, headers=_headers())
            if response.status_code == 400:
                # Some providers don't support response_format - try once without it
                payload.pop("response_format")
                response = client.post(url, json=payload, headers=_headers())
    except httpx.ConnectError:
        raise LLMError(
            f"Cannot connect to the AI model at {config.LLM_BASE_URL}. Is it running? "
            "Meanwhile you can try the 'Simple rules' method.", 503)
    except httpx.TimeoutException:
        raise LLMError("The AI model took too long to answer. Try a shorter document or a smaller model.", 504)

    if response.status_code == 404:
        raise LLMError(
            f"Model '{config.LLM_MODEL}' was not found. With Ollama, run: "
            f"docker compose exec ollama ollama pull {config.LLM_MODEL}", 502)
    if response.status_code in (401, 403):
        raise LLMError("The AI service rejected the API key. Check LLM_API_KEY in your .env file.", 502)
    if response.status_code == 429:
        raise LLMError("The free AI service limit was reached. Wait a minute and try again.", 429)
    if response.status_code >= 400:
        raise LLMError(f"The AI service returned an error ({response.status_code}): {response.text[:300]}", 502)

    content = response.json()["choices"][0]["message"].get("content") or ""
    return parse_json(content), content


def parse_json(text: str) -> dict:
    """Models sometimes wrap JSON in ```json fences or add a sentence - strip that."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise LLMError("The AI model did not return JSON. Try again or use a bigger model.", raw_output=text)
    try:
        data = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"The AI model returned broken JSON ({e.msg}). Try again.", raw_output=text)
    if not isinstance(data, dict):
        raise LLMError("The AI model returned JSON, but not an object.", raw_output=text)
    return data


def status() -> dict:
    """Quick check used by the header of the web app."""
    info = {"base_url": config.LLM_BASE_URL, "model": config.LLM_MODEL, "reachable": False, "model_available": None}
    try:
        response = httpx.get(f"{config.LLM_BASE_URL}/models", headers=_headers(), timeout=3)
    except httpx.HTTPError:
        return info
    info["reachable"] = response.status_code < 500
    if response.status_code == 200:
        try:
            ids = [m.get("id") for m in response.json().get("data", [])]
            info["model_available"] = any(i == config.LLM_MODEL or (i or "").endswith("/" + config.LLM_MODEL) for i in ids)
        except (ValueError, AttributeError):
            pass
    return info
