"""Testes unitários para persistência de estado de modelos (recentes e favoritos)."""

from __future__ import annotations

from bombe_code.models.state import (
    add_recent_model,
    get_favorite_models,
    get_recent_models,
    toggle_favorite_model,
)


def test_recent_models_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    # Inicialmente vazio
    assert get_recent_models() == []

    # Adiciona modelos
    add_recent_model("llama.cpp/mimo-qwen-9b")
    assert get_recent_models() == ["llama.cpp/mimo-qwen-9b"]

    add_recent_model("openai/gpt-4o")
    # Mais recente deve ficar no topo
    assert get_recent_models() == ["openai/gpt-4o", "llama.cpp/mimo-qwen-9b"]

    # Re-adicionar move para o topo sem duplicar
    add_recent_model("llama.cpp/mimo-qwen-9b")
    assert get_recent_models() == ["llama.cpp/mimo-qwen-9b", "openai/gpt-4o"]


def test_favorite_models_toggle(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    assert get_favorite_models() == []

    # Favoritar
    toggle_favorite_model("llama.cpp/mimo-qwen-9b")
    assert get_favorite_models() == ["llama.cpp/mimo-qwen-9b"]

    # Desfavoritar
    toggle_favorite_model("llama.cpp/mimo-qwen-9b")
    assert get_favorite_models() == []
