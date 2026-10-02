from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..config.paths import get_paths
from ..storage.kv import read_json, write_json

AUTH_MODE = 0o600


def _auth_path() -> Path:
    return get_paths().data / "auth.json"


def _load_env_file() -> None:
    """Carrega variáveis de ambiente de um arquivo .env se presente no diretório de trabalho."""
    cwd = Path.cwd()
    env_file = cwd / ".env"
    if not env_file.is_file():
        return
    try:
        content = env_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            key = k.strip()
            val = v.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:  # noqa: BLE001, S110
        pass


def load_auth() -> dict:
    _load_env_file()
    data = read_json(_auth_path())
    result = data if isinstance(data, dict) else {}

    # Procura arquivos auth.json locais no projeto (.bombe/auth.json ou auth.json)
    cwd = Path.cwd()
    for local_path in (cwd / ".bombe" / "auth.json", cwd / "auth.json"):
        if local_path.is_file():
            local_data = read_json(local_path)
            if isinstance(local_data, dict):
                for k, v in local_data.items():
                    if isinstance(v, dict) and isinstance(result.get(k), dict):
                        result[k].update(v)
                    else:
                        result[k] = v
            break

    return result


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
