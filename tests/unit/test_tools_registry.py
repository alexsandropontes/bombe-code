"""Unit: contrato do registry de tools (PRD F5: RN1, RN3, RN4, CA1, CA2)."""

import pytest
from pydantic import BaseModel

from bombe_code.tools.base import InvalidArgumentsError, ToolContext, ToolDef, truncate
from bombe_code.tools.registry import builtin_registry


class _Args(BaseModel):
    path: str


def _echo_tool() -> ToolDef:
    def execute(args: dict, ctx: ToolContext) -> str:
        return f"lido:{args['path']}"

    return ToolDef(
        id="read_echo",
        description="eco",
        parameters=_Args,
        execute=execute,
    )


def test_execute_valido_retorna_output():
    registry = builtin_registry()
    registry.register(_echo_tool())
    out = registry.execute("read_echo", {"path": "a.py"}, ToolContext())
    assert out == "lido:a.py"


def test_arg_invalido_levanta_invalid_arguments():
    registry = builtin_registry()
    registry.register(_echo_tool())
    with pytest.raises(InvalidArgumentsError):
        registry.execute("read_echo", {"errado": 1}, ToolContext())


def test_invalid_tool_devolve_feedback_para_llm():
    registry = builtin_registry()
    out = registry.execute(
        "invalid",
        {"error": "nome de ferramenta desconhecida: frobnicate"},
        ToolContext(),
    )
    assert "frobnicate" in out
    assert "desconhecida" in out


def test_output_longo_e_truncado_com_marcador():
    result = truncate("x" * 50_000)
    assert "[output truncated" in result
    assert len(result) < 50_000


def test_gpt_filtra_edit_write_mantem_apply_patch():
    registry = builtin_registry()
    gpt_ids = {t.id for t in registry.tools_for_model("openai/gpt-4o")}
    assert "edit" not in gpt_ids
    assert "write" not in gpt_ids
    assert "apply_patch" in gpt_ids
    assert "read" in gpt_ids

    claude_ids = {t.id for t in registry.tools_for_model("anthropic/claude-sonnet-4")}
    assert "edit" in claude_ids
    assert "write" in claude_ids


def test_desabilitadas_sao_excluidas():
    registry = builtin_registry()
    ids = {t.id for t in registry.tools_for_model("anthropic/claude", disabled={"shell"})}
    assert "shell" not in ids


def test_json_schema_gerado_do_modelo():
    registry = builtin_registry()
    schema = registry.get("read").json_schema()
    assert "path" in schema["properties"]


def test_ctx_cumpre_contrato_rn1_abort_e_messages():
    ctx = ToolContext()
    assert ctx.abort() is False
    assert ctx.messages == []
    assert ctx.metadata() == {}


def test_todos_os_14_builtins_registrados():
    registry = builtin_registry()
    esperados = {
        "invalid",
        "question",
        "shell",
        "read",
        "glob",
        "grep",
        "edit",
        "write",
        "task",
        "webfetch",
        "todowrite",
        "websearch",
        "skill",
        "apply_patch",
    }
    assert esperados <= {t.id for t in registry.list()}
