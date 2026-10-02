"""Integration tests for F10 sdk-python against live server."""

import threading
import time
from pathlib import Path

import pytest
import uvicorn

from bombe_code.permissions.rules import PermissionService, Rule
from bombe_code.sdk.client import BombeSDK
from bombe_code.sdk.models import PromptResult, SessionModel
from bombe_code.server.app import create_app

pytestmark = pytest.mark.integration


class ScriptedAdapter:
    provider = "openai"
    model = "scripted/sdk"

    def stream(self, messages, tools, system):
        return iter([
            {"type": "text-delta", "text": "Resposta SDK tipada"},
            {"type": "finish", "reason": "stop"},
        ])


@pytest.fixture()
def sdk_live_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    permissive = PermissionService(
        rules=[Rule(permission="*", pattern="*", action="allow")], approved=[]
    )
    app = create_app(
        adapter=ScriptedAdapter(),
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
    assert port is not None

    password = (
        (tmp_path / "state" / "bombe-code" / "server-auth")
        .read_text(encoding="utf-8")
        .strip()
    )
    base = f"http://127.0.0.1:{port}"
    try:
        yield {"base": base, "auth": ("bombe", password)}
    finally:
        server.should_exit = True
        thread.join(timeout=3)


@pytest.mark.anyio
async def test_sdk_crud_and_events(sdk_live_server):
    sdk = BombeSDK(base_url=sdk_live_server["base"], auth=sdk_live_server["auth"])

    # 1. Create Session
    session = await sdk.create_session(title="Test SDK")
    assert isinstance(session, SessionModel)
    assert session.id.startswith("ses_")
    assert session.title == "Test SDK"

    # 2. List Sessions
    sessions = await sdk.list_sessions()
    assert any(s.id == session.id for s in sessions)

    # 3. Send Prompt
    result = await sdk.send_prompt(session.id, "Teste prompt via SDK")
    assert isinstance(result, PromptResult)
    assert result.status == "completed"
    assert "Resposta SDK tipada" in result.text


@pytest.mark.anyio
async def test_sdk_stream_events(sdk_live_server):
    sdk = BombeSDK(base_url=sdk_live_server["base"], auth=sdk_live_server["auth"])
    session = await sdk.create_session(title="Stream Test")

    # Envia prompt
    await sdk.send_prompt(session.id, "Olá")

    # Lê eventos SSE tipados
    events = []
    async for ev in sdk.stream_events(session.id):
        events.append(ev)
        if ev.type == "prompt.finished":
            break

    assert any(e.type == "prompt.started" for e in events)
    assert any(e.type == "text-delta" for e in events)
    assert any(e.type == "prompt.finished" for e in events)
