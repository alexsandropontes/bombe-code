"""Integration tests for F13 plugins system."""

from pathlib import Path

import pytest

from bombe_code.plugins.manager import PluginManager
from bombe_code.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


def test_plugin_loader_and_hooks(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Cria plugin de teste
    plugin_code = """
events = []

def on_init(ctx):
    events.append("init_called")

def register_tools(registry):
    from bombe_code.tools.base import ToolDef
    from pydantic import BaseModel
    class Empty(BaseModel): pass
    def dummy_exec(args, ctx): return "plugin output"
    registry.register(ToolDef(id="plugin_tool", description="teste", parameters=Empty, execute=dummy_exec))
"""
    (plugins_dir / "my_plugin.py").write_text(plugin_code, encoding="utf-8")

    registry = ToolRegistry()
    mgr = PluginManager()
    loaded = mgr.load_from_dir(plugins_dir, registry=registry)

    assert "my_plugin" in loaded
    # Hook on_init
    ctx = {"app": "test"}
    mgr.emit("on_init", ctx)

    # Tool registrada
    tool = registry.get("plugin_tool")
    assert tool is not None
    assert tool.description == "teste"
