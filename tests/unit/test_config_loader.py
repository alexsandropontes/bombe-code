"""Unit: merge profundo de config (RN3 do F1 — determinístico, concat de arrays)."""

from pathlib import Path

from bombe_code.config.loader import deep_merge, load_config
from bombe_code.config.paths import discover_config


def test_merge_profundo_combina_dicts_aninhados():
    # Arrange
    base = {"server": {"port": 4096, "host": "127.0.0.1"}}
    override = {"server": {"port": 4100}}
    # Act
    merged = deep_merge(base, override)
    # Assert
    assert merged == {"server": {"port": 4100, "host": "127.0.0.1"}}


def test_merge_concatena_arrays_em_ordem():
    # Arrange
    base = {"plugin": ["a"], "tools": ["x"]}
    override = {"plugin": ["b"]}
    # Act
    merged = deep_merge(base, override)
    # Assert
    assert merged["plugin"] == ["a", "b"]
    assert merged["tools"] == ["x"]


def test_merge_e_deterministico_e_nao_muta_entradas():
    # Arrange
    base = {"a": {"b": [1]}}
    override = {"a": {"c": 2}}
    # Act
    first = deep_merge(base, override)
    second = deep_merge(base, override)
    # Assert
    assert first == second
    assert base == {"a": {"b": [1]}}
    assert override == {"a": {"c": 2}}


def test_merge_scalar_do_override_sobrescreve():
    assert deep_merge({"model": "a"}, {"model": "b"}) == {"model": "b"}


def test_merge_sem_chaves_em_comum_so_adiciona():
    assert deep_merge({"x": 1}, {"y": 2}) == {"x": 1, "y": 2}


# --- RN2: jsonc (comentários fora de strings) ---


def test_load_config_aceita_jsonc_com_comentarios(tmp_path: Path):
    # Arrange
    (tmp_path / "bombe.jsonc").write_text(
        "{\n"
        "  // comentario de linha\n"
        '  "model": "anthropic/claude",\n'
        "  /* comentario de bloco\n"
        "     multipla linhas */\n"
        '  "endpoint": "https://api.exemplo.com/v1"\n'
        "}\n",
        encoding="utf-8",
    )

    # Act
    cfg = load_config(start=tmp_path)

    # Assert — o // dentro da string NÃO pode virar comentário
    assert cfg["model"] == "anthropic/claude"
    assert cfg["endpoint"] == "https://api.exemplo.com/v1"


def test_descobre_bombe_jsonc(tmp_path: Path):
    # Arrange
    cfg = tmp_path / "bombe.jsonc"
    cfg.write_text('{"a": 1}', encoding="utf-8")

    # Act & Assert
    assert discover_config(tmp_path) == cfg
