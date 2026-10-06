"""Testes unitários para TemplateMatcher e Ferramentas de Starter (ST-042)."""

import json
from pathlib import Path

from bombe_code.starters.matcher import TemplateMatcher
from bombe_code.tools.base import ToolContext
from bombe_code.tools.builtin.template_tools import (
    TEMPLATE_APPLY_TOOL,
    TEMPLATE_INSPECT_TOOL,
    TEMPLATE_MATCH_TOOL,
)


def test_template_matcher_python_mono_fullstack():
    matcher = TemplateMatcher()
    res = matcher.match(
        product_type="saas",
        backend_language="python",
        frontend_stack="react",
        multitenancy="mono",
    )
    assert res.matched is True
    assert res.starter_id == "python-mono"
    assert res.manifest is not None
    assert "users" in res.manifest.suggested_tables
    assert any("users" in g.lower() for g in res.manifest.guidelines)


def test_template_matcher_multitenancy_logical_and_physical():
    matcher = TemplateMatcher()

    # Multi-logical .NET
    res_logic = matcher.match(
        product_type="api",
        backend_language="dotnet",
        frontend_stack="none",
        multitenancy="multi-logical",
    )
    assert res_logic.matched is True
    assert res_logic.starter_id == "dotnet-multi-logical-backend"
    assert res_logic.manifest.multitenancy_type == "multi-logical"
    assert "tenants" in res_logic.manifest.suggested_tables

    # Multi-physical Go
    res_phys = matcher.match(
        product_type="saas",
        backend_language="go",
        frontend_stack="react",
        multitenancy="multi-physical",
    )
    assert res_phys.matched is True
    assert res_phys.starter_id == "go-multi-physical"
    assert res_phys.manifest.multitenancy_type == "multi-physical"
    assert "customers" in res_phys.manifest.suggested_tables


def test_template_matcher_chatbot_and_whatsapp():
    matcher = TemplateMatcher()

    # Chatbot Streamlit
    res_bot = matcher.match(
        product_type="chatbot",
        backend_language="python",
        frontend_stack="streamlit",
    )
    assert res_bot.matched is True
    assert res_bot.starter_id == "chatbot-py-streamlit"

    # WhatsApp BFF Go
    res_wa = matcher.match(
        product_type="whatsapp",
        backend_language="go",
    )
    assert res_wa.matched is True
    assert res_wa.starter_id == "whatsapp-bff-go"


def test_template_tools_execution(tmp_path: Path):
    ctx = ToolContext(session_id="s1", project_dir=str(tmp_path))

    # 1. Match tool
    match_out = json.loads(
        TEMPLATE_MATCH_TOOL.execute(
            {
                "product_type": "saas",
                "backend_language": "python",
                "frontend_stack": "react",
                "multitenancy": "mono",
            },
            ctx,
        )
    )
    assert match_out["matched"] is True
    assert match_out["starter_id"] == "python-mono"
    assert "manifest" in match_out

    # 2. Inspect tool
    inspect_out = json.loads(TEMPLATE_INSPECT_TOOL.execute({"starter_id": "python-mono"}, ctx))
    assert inspect_out["name"] == "python-mono"
    assert "composition" in inspect_out
    assert "react-portal" in inspect_out["composition"]

    # 3. Apply tool
    target = tmp_path / "app_scaffold"
    apply_out = json.loads(
        TEMPLATE_APPLY_TOOL.execute(
            {
                "starter_id": "python-mono",
                "target_dir": str(target),
                "project_name": "AppScaffold",
            },
            ctx,
        )
    )
    assert apply_out["success"] is True
    assert (target / ".bombeconfig").is_file()
    assert (target / "src" / "backend" / "main.py").is_file()
