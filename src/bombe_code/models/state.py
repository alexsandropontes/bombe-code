"""Gerenciamento de estado de modelos (recentes e favoritos) com persistência local."""

from __future__ import annotations

from pathlib import Path

from ..config.paths import get_paths
from ..storage.kv import read_json, write_json

MAX_RECENT_MODELS = 10


def _model_state_path() -> Path:
    return get_paths().state / "model.json"


def _load_model_state() -> dict:
    path = _model_state_path()
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def _save_model_state(state: dict) -> None:
    path = _model_state_path()
    write_json(path, state)


def get_recent_models() -> list[str]:
    """Retorna a lista de modelos recentemente utilizados (mais recentes primeiro)."""
    state = _load_model_state()
    recents = state.get("recent", [])
    return [str(m) for m in recents if isinstance(m, str)]


def add_recent_model(model_name: str) -> None:
    """Adiciona um modelo ao topo do histórico recente, deduplicando."""
    if not model_name:
        return
    model_name = model_name.strip()
    state = _load_model_state()
    recents: list[str] = [m for m in state.get("recent", []) if isinstance(m, str) and m != model_name]
    recents.insert(0, model_name)
    state["recent"] = recents[:MAX_RECENT_MODELS]
    _save_model_state(state)


def get_favorite_models() -> list[str]:
    """Retorna os modelos marcados como favoritos."""
    state = _load_model_state()
    favs = state.get("favorite", [])
    return [str(m) for m in favs if isinstance(m, str)]


def toggle_favorite_model(model_name: str) -> None:
    """Alterna o status de favorito de um modelo."""
    if not model_name:
        return
    model_name = model_name.strip()
    state = _load_model_state()
    favs: list[str] = [m for m in state.get("favorite", []) if isinstance(m, str)]
    if model_name in favs:
        favs = [m for m in favs if m != model_name]
    else:
        favs.append(model_name)
    state["favorite"] = favs
    _save_model_state(state)
