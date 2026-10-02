from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..config.paths import get_paths
from ..storage.kv import read_json, write_json

AUTH_MODE = 0o600


def _auth_path() -> Path:
    return get_paths().data / "auth.json"


def load_auth() -> dict:
    data = read_json(_auth_path())
    return data if isinstance(data, dict) else {}


def _save_entry(provider: str, field: str, value: Any) -> None:
    path = _auth_path()
    auth = load_auth()
    auth.setdefault(provider, {})[field] = value
    write_json(path, auth)
    os.chmod(path, AUTH_MODE)


def save_api_key(provider: str, key: str) -> None:
    _save_entry(provider, "api_key", key)


def save_provider_url(provider: str, url: str) -> None:
    _save_entry(provider, "base_url", url)


def save_oauth_token(provider: str, token: dict) -> None:
    _save_entry(provider, "oauth", token)
