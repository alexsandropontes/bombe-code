"""Testes unitários para o módulo de tratamento elegante de erros (errors.py)."""

from pathlib import Path

import pytest
from rich.panel import Panel

from bombe_code.errors import format_error_panel, is_debug_mode, record_exception


def test_is_debug_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOMBE_DEBUG", raising=False)
    assert not is_debug_mode()

    monkeypatch.setenv("BOMBE_DEBUG", "1")
    assert is_debug_mode()


def test_record_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))

    try:
        raise ValueError("Teste de falha controlada")
    except ValueError as exc:
        log_file = record_exception(exc, context="Unit Test")

    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "ERRO INESPERADO (Contexto: Unit Test)" in content
    assert "ValueError" in content
    assert "Teste de falha controlada" in content
    assert "Traceback:" in content


def test_format_error_panel(tmp_path: Path) -> None:
    fake_log = tmp_path / "error.log"
    exc = RuntimeError("Falha de teste")

    panel = format_error_panel(exc, fake_log)
    assert isinstance(panel, Panel)
    # Renderiza o painel para texto simples
    from rich.console import Console

    console = Console(record=True, width=80)
    console.print(panel)
    output = console.export_text()

    assert "Ocorreu um erro inesperado no Bombe Code." in output
    assert "Falha de teste" in output
    assert str(fake_log) in output
    assert "BOMBE_DEBUG=1" in output


def test_format_error_panel_with_empty_message(tmp_path: Path) -> None:
    import httpx

    fake_log = tmp_path / "error.log"
    # httpx.ReadTimeout tem representação de string vazia por padrão
    exc = httpx.ReadTimeout("")
    panel = format_error_panel(exc, fake_log)

    from rich.console import Console

    console = Console(record=True, width=80)
    console.print(panel)
    output = console.export_text()

    assert "Ocorreu um erro inesperado no Bombe Code." in output
    assert "ReadTimeout" in output
