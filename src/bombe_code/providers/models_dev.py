from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from ..config.paths import get_paths
from ..storage.kv import read_json, write_json

TTL_SECONDS = 300.0
MODELS_URL = "https://models.dev/api.json"


def _cache_path() -> Path:
    return get_paths().cache / "models.json"


def _fetch_remote() -> dict:
    response = httpx.get(MODELS_URL, timeout=30.0)
    response.raise_for_status()
    return response.json()


def get_models(
    fetch: Callable[[], dict] | None = None,
    now: Callable[[], float] | None = None,
) -> dict[str, Any]:
    fetcher = fetch or _fetch_remote
    clock = now or time.time
    path = _cache_path()
    cached = read_json(path) if path.is_file() else None

    if cached is not None and (clock() - cached["fetched_at"]) < TTL_SECONDS:
        return cached["models"]

    try:
        models = fetcher()
    except Exception:
        if cached is not None:
            return cached["models"]
        raise

    write_json(path, {"fetched_at": clock(), "models": models})
    return models
