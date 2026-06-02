from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REQUIRED_YOUTUBE_MODES = {
    "analyze",
    "summary",
    "keyword",
    "topics",
    "emotion",
    "video_content",
    "criticism",
    "timeline",
}

REQUIRED_OLLAMA_MODES = {
    "analyze",
    "video_content",
}

PLACEHOLDER_VALUES = {
    "",
    "YOUR_YOUTUBE_API",
    "YOUR_API_KEY",
    "YOUR_YOUTUBE_API_KEY",
}


class DependencyError(RuntimeError):
    pass


def _env_value(name: str) -> str:
    return str(os.getenv(name, "")).strip()


def _check_youtube_api_key(errors: list[str]) -> None:
    api_key = _env_value("API_KEY")
    if api_key in PLACEHOLDER_VALUES:
        errors.append("API_KEY is missing or still using the .env.template placeholder.")


def _ollama_tags_url(host: str) -> str:
    return f"{host.rstrip('/')}/api/tags"


def _check_ollama(errors: list[str]) -> None:
    host = _env_value("OLLAMA_HOST") or "http://host.docker.internal:11434"
    model = _env_value("OLLAMA_MODEL") or "gemma3:12b"

    try:
        request = Request(_ollama_tags_url(host), method="GET")
        with urlopen(request, timeout=3) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw or "{}")
    except HTTPError as exc:
        errors.append(f"OLLAMA_HOST is reachable but returned HTTP {exc.code}: {host}")
        return
    except (OSError, URLError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot reach Ollama at OLLAMA_HOST={host}: {type(exc).__name__}: {exc}")
        return

    models = data.get("models", [])
    model_names = {
        str(item.get("name") or item.get("model") or "")
        for item in models
        if isinstance(item, dict)
    }

    if model and model not in model_names:
        available = ", ".join(sorted(name for name in model_names if name)) or "none"
        errors.append(f"OLLAMA_MODEL={model} is not available on {host}. Available models: {available}.")


def check_analysis_dependencies(mode: str) -> None:
    normalized_mode = str(mode or "analyze").strip()
    errors: list[str] = []

    if normalized_mode in REQUIRED_YOUTUBE_MODES:
        _check_youtube_api_key(errors)

    if normalized_mode in REQUIRED_OLLAMA_MODES:
        _check_ollama(errors)

    if errors:
        raise DependencyError("Dependency check failed before analysis: " + " | ".join(errors))
