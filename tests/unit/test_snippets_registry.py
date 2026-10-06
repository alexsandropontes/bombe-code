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


def test_list_all_55_catalog_snippets():
    """Valida se todos os 55 snippets oficiais são descobertos e carregados."""
    registry = SnippetRegistry()
    snippets = registry.list_snippets()
    assert len(snippets) >= 55

    platforms = {s["platform"] for s in snippets}
    assert "dotnet" in platforms
    assert "go" in platforms
    assert "java" in platforms
    assert "nodejs" in platforms
    assert "python" in platforms
    assert "react" in platforms

    categories = {s["category"] for s in snippets}
    assert "auth" in categories
    assert "data-validation" in categories
    assert "multitenancy" in categories
    assert "omnichannel" in categories
    assert "utils" in categories


def test_copy_dotnet_snippet(tmp_path: Path):
    """Valida cópia de snippet .NET C# para projeto."""
    registry = SnippetRegistry()
    dest = tmp_path / "src" / "Infrastructure"
    res = registry.copy_snippet("hash-password", to_dir=str(dest), platform="dotnet")
    assert res["success"] is True
    assert (dest / "PasswordHasher.cs").is_file()


def test_copy_react_snippet(tmp_path: Path):
    """Valida cópia de snippet React/TypeScript para projeto."""
    registry = SnippetRegistry()
    dest = tmp_path / "src" / "components"
    res = registry.copy_snippet("data-table", to_dir=str(dest), platform="react")
    assert res["success"] is True
    assert (dest / "DataTable.tsx").is_file()
