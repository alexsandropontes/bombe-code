"""Testes unitários para a Feature 21: code-formatters (RED phase)."""

from __future__ import annotations

from pathlib import Path

from bombe_code.formatters.runner import detect_formatter_for_file, format_code_file


def test_detect_formatter_by_extension():
    assert detect_formatter_for_file("app.py") in ("ruff", "black")
    assert detect_formatter_for_file("component.tsx") == "prettier"
    assert detect_formatter_for_file("main.go") == "gofmt"
    assert detect_formatter_for_file("styles.css") == "prettier"
    assert detect_formatter_for_file("unknown.xyz") is None


def test_format_code_file_with_ruff(tmp_path: Path):
    py_file = tmp_path / "messy.py"
    # Código Python desformatado
    py_file.write_text("def   foo( a,b ):\n  return a+b\n", encoding="utf-8")

    formatted = format_code_file(str(py_file), cwd=str(tmp_path))
    assert formatted is True

    content = py_file.read_text(encoding="utf-8")
    assert "def foo(a, b):" in content
    assert "return a + b" in content


def test_format_code_file_graceful_on_missing(tmp_path: Path):
    xyz_file = tmp_path / "test.xyz"
    xyz_file.write_text("some content", encoding="utf-8")

    # Arquivo sem formatador conhecido retorna False sem lançar exceção
    res = format_code_file(str(xyz_file), cwd=str(tmp_path))
    assert res is False
