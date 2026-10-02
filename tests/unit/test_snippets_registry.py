"""Testes unitários para o SnippetRegistry do Bombe Code (ST-025).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path

from bombe_code.snippets.registry import SnippetRegistry


def test_list_snippets():
    registry = SnippetRegistry()
    snippets = registry.list_snippets()
    assert len(snippets) >= 6

    names = [s["name"] for s in snippets]
    assert "validar-cpf" in names
    assert "validar-cnpj" in names
    assert "format-phone" in names
    assert "hash-password" in names


def test_search_snippets_with_platform_filter():
    registry = SnippetRegistry()

    # Busca sem filtro de plataforma
    res_all = registry.search("cpf")
    assert len(res_all) >= 1

    # Busca com filtro python
    res_py = registry.search("cpf", platform="python")
    assert len(res_py) >= 1
    assert all(s["platform"] == "python" for s in res_py)


def test_get_snippet_details():
    registry = SnippetRegistry()
    snip = registry.get_snippet("validar-cpf", platform="python")
    assert snip is not None
    assert snip["name"] == "validar-cpf"
    assert "code" in snip
    assert "def validar_cpf" in snip["code"]
    assert "tests" in snip


def test_copy_snippet_to_project(tmp_path: Path):
    registry = SnippetRegistry()
    dest = tmp_path / "src" / "utils"

    result = registry.copy_snippet("validar-cpf", to_dir=str(dest), platform="python")
    assert result["success"] is True

    # Verifica se os arquivos foram copiados
    assert (dest / "validar_cpf.py").is_file()
    assert (dest / "test_validar_cpf.py").is_file()
