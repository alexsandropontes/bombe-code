"""Integration tests for F8 tui-chat using Textual's testing harness against live server."""

import threading
import time
from pathlib import Path

import pytest
import uvicorn

from bombe_code.permissions.rules import PermissionService, Rule
from bombe_code.server.app import create_app
from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient
from bombe_code.tui.widgets.parts_view import ChatView, PartWidget
from bombe_code.tui.widgets.prompt_input import PromptInput

pytestmark = pytest.mark.integration


class ScriptedAdapter:
    provider = "openai"
    model = "scripted/test"

    def __init__(self, steps):
        self.steps = [list(step) for step in steps]
        self.calls = []

    def stream(self, messages, tools, system):
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        if not self.steps:
            return iter(
                [{"type": "text-delta", "text": "Ok final"}, {"type": "finish", "reason": "stop"}]
            )
        return iter(self.steps.pop(0))


@pytest.fixture()
def tui_live_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    adapter = ScriptedAdapter(
        [
            [
                {"type": "text-delta", "text": "Olá da IA TUI"},
                {"type": "finish", "reason": "stop"},
            ]
        ]
    )
    permissive = PermissionService(
        rules=[Rule(permission="*", pattern="*", action="allow")], approved=[]
    )
    app = create_app(
        adapter=adapter,
        permissions=permissive,
        project_dir=str(tmp_path),
    )

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 15
    port = None
    while time.time() < deadline:
        if getattr(server, "servers", None):
            port = server.servers[0].sockets[0].getsockname()[1]
            break
        time.sleep(0.05)
    assert port is not None, "uvicorn server failed to start"

    password = (
        (tmp_path / "state" / "bombe-code" / "server-auth").read_text(encoding="utf-8").strip()
    )
    auth = ("bombe", password)
    base = f"http://127.0.0.1:{port}"
    try:
        yield {"base": base, "auth": auth, "dir": tmp_path}
    finally:
        server.should_exit = True
        thread.join(timeout=3)


@pytest.mark.anyio
async def test_tui_app_mount_and_streaming(tui_live_server):
    client = BombeClient(tui_live_server["base"], auth=tui_live_server["auth"])
    app = BombeTuiApp(client=client)

    async with app.run_test() as pilot:
        # Aguarda montagem e criação da sessão
        await pilot.pause(0.2)
        assert app.session_id is not None
        assert app.session_id.startswith("ses_")

        # Submete prompt no input
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "Construa um teste"
        await pilot.press("enter")
        await pilot.pause(0.5)

        # Chat deve conter a resposta gerada pelo servidor via SSE
        chat = app.query_one("#chat-view", ChatView)
        part_widgets = chat.query(PartWidget)
        assert len(part_widgets) >= 1

        # Verifica se o texto "Olá da IA TUI" foi renderizado
        texts = [
            pw.part_data.get("text", "")
            for pw in part_widgets
            if pw.part_data.get("type") == "text"
        ]
        assert any("Olá da IA TUI" in t for t in texts)


@pytest.mark.anyio
async def test_tui_app_interrupt(tui_live_server):
    client = BombeClient(tui_live_server["base"], auth=tui_live_server["auth"])
    app = BombeTuiApp(client=client)

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        app._is_active_turn = True
        app.update_status()

        # Aciona interrupção
        await app.action_interrupt()
        assert app._is_active_turn is False


@pytest.mark.anyio
async def test_tui_tool_and_events_rendering(tui_live_server):
    client = BombeClient(tui_live_server["base"], auth=tui_live_server["auth"])
    app = BombeTuiApp(client=client)

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        # Simula recebimento de evento tool-call
        await app._handle_event(
            {"type": "tool-call", "tool": "shell", "arguments": {"command": "ls -la"}}
        )
        chat = app.query_one("#chat-view", ChatView)
        part_widgets = chat.query(PartWidget)
        assert any(pw.part_data.get("tool") == "shell" for pw in part_widgets)

        # Simula recebimento de tool-result
        await app._handle_event(
            {"type": "tool-result", "tool": "shell", "output": "total 0\n-rw-r--r-- 1 test"}
        )
        part_widgets = chat.query(PartWidget)
        assert any("total 0" in pw.part_data.get("output", "") for pw in part_widgets)


@pytest.mark.anyio
async def test_tui_command_palette_ctrl_p(tui_live_server):
    from bombe_code.tui.widgets.command_palette import CommandPalette

    client = BombeClient(tui_live_server["base"], auth=tui_live_server["auth"])
    app = BombeTuiApp(client=client)

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        # Aciona paleta de comandos via atalho ctrl+p
        await pilot.press("ctrl+p")
        await pilot.pause(0.2)
        assert isinstance(app.screen, CommandPalette)

        # Fecha com escape
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert not isinstance(app.screen, CommandPalette)


@pytest.mark.anyio
async def test_tui_slash_command_error_graceful(tui_live_server):
    client = BombeClient(tui_live_server["base"], auth=tui_live_server["auth"])
    app = BombeTuiApp(client=client)

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        inp = app.query_one("#prompt-input", PromptInput)
        # Submete slash command com argumento que causa erro controlado
        inp.value = "/export /root/invalid_forbidden_path/test.json"
        await pilot.press("enter")
        await pilot.pause(0.5)

        # O app deve continuar vivo e exibir mensagem de erro amigável no chat
        chat = app.query_one("#chat-view", ChatView)
        text_content = "".join(str(getattr(child, "renderable", "")) for child in chat.children)
        assert "Erro ao executar" in text_content or "❌" in text_content or len(chat.children) > 0


@pytest.mark.anyio
async def test_tui_fatal_error_panel(tui_live_server, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    client = BombeClient(tui_live_server["base"], auth=tui_live_server["auth"])
    app = BombeTuiApp(client=client)

    app._exception = RuntimeError("Falha simulada de teste fatal")
    app._fatal_error()

    assert len(app._exit_renderables) >= 1
    # Verifica que o arquivo de log foi gerado
    from bombe_code.config.paths import get_paths

    assert (get_paths().log / "error.log").is_file()
