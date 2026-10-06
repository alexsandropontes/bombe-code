"""Cliente MCP (Model Context Protocol) via transporte stdio."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from pydantic import create_model

from ..tools.base import ToolContext, ToolDef
from ..tools.registry import ToolRegistry


class MCPClient:
    """Comunicação JSON-RPC 2.0 com servidores MCP via stdio."""

    def __init__(self, command: str, args: list[str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self._process: subprocess.Popen | None = None
        self._next_id: int = 1

    def start(self) -> None:
        self._process = subprocess.Popen(
            [self.command, *self.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def stop(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2.0)
            except (subprocess.TimeoutExpired, OSError):
                self._process.kill()
            self._process = None

    def _call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise RuntimeError("Servidor MCP não está em execução.")

        req_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        self._process.stdin.write(json.dumps(payload) + "\n")
        self._process.stdin.flush()

        line = self._process.stdout.readline()
        if not line:
            raise RuntimeError("Servidor MCP fechou a conexão inesperadamente.")

        response = json.loads(line)
        if "error" in response:
            err = response["error"]
            raise RuntimeError(f"Erro MCP ({err.get('code')}): {err.get('message')}")
        return response.get("result", {})

    def initialize(self) -> dict[str, Any]:
        return self._call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bombe-code", "version": "0.1.0"},
            },
        )

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._call("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        result = self._call("tools/call", {"name": name, "arguments": arguments})
        contents = result.get("content", [])
        texts = [
            c.get("text", "") for c in contents if isinstance(c, dict) and c.get("type") == "text"
        ]
        return "\n".join(texts) if texts else json.dumps(result)


def register_mcp_tools(registry: ToolRegistry, client: MCPClient) -> list[str]:
    """Registra ferramentas remotas do MCP no ToolRegistry do Bombe Code."""
    tools = client.list_tools()
    registered: list[str] = []

    for t in tools:
        t_name = t.get("name")
        if not t_name:
            continue
        description = t.get("description", f"MCP Tool: {t_name}")
        schema = t.get("inputSchema", {})

        # Cria modelo Pydantic dinâmico compatível com os campos do schema
        properties = schema.get("properties", {})
        fields: dict[str, Any] = {}
        for prop_name in properties:
            fields[prop_name] = (Any, None)

        param_model = (
            create_model(f"MCPParams_{t_name}", **fields)
            if fields
            else create_model(f"MCPParams_{t_name}")
        )

        def make_executor(name: str):
            def executor(args: dict[str, Any], ctx: ToolContext) -> str:
                return client.call_tool(name, args)

            return executor

        tool_def = ToolDef(
            id=t_name,
            description=description,
            parameters=param_model,
            execute=make_executor(t_name),
        )
        registry.register(tool_def)
        registered.append(t_name)

    return registered
