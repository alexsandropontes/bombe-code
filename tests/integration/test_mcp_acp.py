"""Integration tests for F14 mcp-acp."""

import sys
from pathlib import Path

import pytest

from bombe_code.acp.adapter import ACPAdapter
from bombe_code.mcp.client import MCPClient, register_mcp_tools
from bombe_code.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration


def test_mcp_stdio_client_and_tools_registration(tmp_path: Path):
    # Cria um servidor MCP stdio fake em python usando stdin/stdout JSON-RPC
    server_script = tmp_path / "mock_mcp_server.py"
    server_script.write_text(
        """
import sys, json

for line in sys.stdin:
    if not line.strip(): continue
    req = json.loads(line)
    method = req.get("method")
    msg_id = req.get("id")
    if method == "initialize":
        res = {"jsonrpc": "2.0", "id": msg_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {}}}
    elif method == "tools/list":
        res = {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "tools": [
                    {"name": "mcp_echo", "description": "Echo tool via MCP", "inputSchema": {"type": "object", "properties": {"msg": {"type": "string"}}}}
                ]
            }
        }
    elif method == "tools/call":
        params = req.get("params", {})
        msg = params.get("arguments", {}).get("msg", "")
        res = {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": f"echo: {msg}"}]}}
    else:
        res = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
    sys.stdout.write(json.dumps(res) + "\\n")
    sys.stdout.flush()
""",
        encoding="utf-8",
    )

    client = MCPClient(command=sys.executable, args=[str(server_script)])
    client.start()
    try:
        init_res = client.initialize()
        assert init_res.get("protocolVersion") == "2024-11-05"

        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "mcp_echo"

        # Registrar no ToolRegistry
        registry = ToolRegistry()
        register_mcp_tools(registry, client)
        tool = registry.get("mcp_echo")
        assert tool is not None
        assert tool.description == "Echo tool via MCP"

        # Executa tool
        from bombe_code.tools.base import ToolContext

        ctx = ToolContext(
            session_id="ses_1", agent="build", project_dir=".", messages=[], ask=lambda *a: "allow"
        )
        out = registry.execute("mcp_echo", {"msg": "bombe"}, ctx)
        assert "echo: bombe" in out
    finally:
        client.stop()


def test_acp_adapter_format():
    adapter = ACPAdapter()
    msg = adapter.format_message(role="user", content="Executar tarefa")
    assert msg["role"] == "user"
    assert msg["content"] == "Executar tarefa"
