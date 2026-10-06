"""Testes unitários para as ferramentas de Snippets da LLM (ST-026).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

import json

from bombe_code.tools.base import ToolContext
from bombe_code.tools.builtin.snippet_tools import SNIPPET_GET_TOOL, SNIPPET_SEARCH_TOOL
from bombe_code.tools.registry import builtin_registry


def test_snippet_tools_registered_in_builtin_registry():
    reg = builtin_registry()
    tools = {t.id: t for t in reg.list()}
    assert "snippet_search" in tools
    assert "snippet_get" in tools


def test_snippet_search_tool_execution():
    ctx = ToolContext(session_id="s1", project_dir=".")
    result_str = SNIPPET_SEARCH_TOOL.execute({"query": "cpf", "platform": "python"}, ctx)
    data = json.loads(result_str)

    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "validar-cpf"
    assert data[0]["platform"] == "python"


def test_snippet_get_tool_execution():
    ctx = ToolContext(session_id="s1", project_dir=".")
    result_str = SNIPPET_GET_TOOL.execute({"name": "validar-cpf", "platform": "python"}, ctx)
    data = json.loads(result_str)

    assert data["name"] == "validar-cpf"
    assert "def validar_cpf" in data["code"]
    assert "test_validar_cpf" in data["tests"]
