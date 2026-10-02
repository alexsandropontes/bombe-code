"""Integration F7 server-http — HTTP + SSE REAIS (uvicorn em socket local, sem mocks).

Cobre PRD F7: RN1 (rotas parity), RN2 (OpenAPI), RN3 (SSE + Last-Event-ID), RN4 (basic auth).
"""

import json
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

from bombe_code.permissions.rules import PermissionService, Rule
from bombe_code.server.app import create_app

pytestmark = pytest.mark.integration


class ScriptedAdapter:
    provider = "openai"
    model = "scripted/test"

    def __init__(self, steps):
        self.steps = [list(step) for step in steps]
        self.calls: list[dict] = []

    def stream(self, messages, tools, system):
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        if not self.steps:
            raise AssertionError("passo inesperado")
        return iter(self.steps.pop(0))


@pytest.fixture()
def live_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    adapter = ScriptedAdapter(
        [
            [
                {"type": "text-delta", "text": "Oi servidor"},
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
    assert port is not None, "uvicorn nao subiu"

    password = (
        (tmp_path / "state" / "bombe-code" / "server-auth").read_text(encoding="utf-8").strip()
    )
    auth = ("bombe", password)
    base = f"http://127.0.0.1:{port}"
    try:
        yield base, auth, adapter
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def _parse_sse(chunks: list[str]) -> list[dict]:
    events = []
    current_id = None
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("id:"):
                current_id = int(line[3:].strip())
            elif line.startswith("data:"):
                payload = json.loads(line[5:].strip())
                payload["_id"] = current_id
                events.append(payload)
    return events


def test_health_requer_basic_auth(live_server):
    base, auth, _ = live_server
    assert httpx.get(f"{base}/api/health").status_code == 401
    ok = httpx.get(f"{base}/api/health", auth=auth)
    assert ok.status_code == 200
    assert ok.json()["status"] == "ok"


def test_ca2_openapi_lista_todas_as_rotas(live_server):
    base, auth, _ = live_server
    spec = httpx.get(f"{base}/openapi.json", auth=auth).json()
    esperadas = {
        "/api/health",
        "/api/event",
        "/api/session",
        "/api/model",
        "/api/provider",
        "/api/provider/{provider_id}",
        "/api/agent",
        "/api/fs/list",
        "/api/fs/read",
        "/api/fs/find",
        "/api/permission/request",
        "/api/permission/saved",
        "/api/question/request",
        "/api/session/{session_id}/message",
        "/api/session/{session_id}/prompt",
        "/api/session/{session_id}/history",
        "/api/session/{session_id}/wait",
        "/api/session/{session_id}/interrupt",
        "/api/session/{session_id}/compact",
        "/api/session/{session_id}/event",
        "/api/session/{session_id}/revert/{message_id}",
        "/api/session/{session_id}/permission/reply",
        "/api/session/{session_id}/question/reply",
        "/api/session/{session_id}/model",
        "/api/session/{session_id}/agent",
        "/api/session/{session_id}/context",
    }
    assert esperadas <= set(spec["paths"])


def test_ca1_prompt_gera_eventos_sse_em_ordem(live_server):
    base, auth, _ = live_server
    session = httpx.post(f"{base}/api/session", auth=auth, json={"title": "s1"}).json()
    sid = session["id"]

    resp = httpx.post(f"{base}/api/session/{sid}/prompt", auth=auth, json={"text": "oi"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "Oi servidor"

    chunks: list[str] = []
    with httpx.stream(
        "GET",
        f"{base}/api/event",
        auth=auth,
        headers={"Last-Event-ID": "0"},
        timeout=10.0,
    ) as stream:
        for line in stream.iter_lines():
            chunks.append(line + "\n")
            joined = "".join(chunks)
            if joined.count("data:") >= 3:
                break

    events = [e for e in _parse_sse(chunks) if e.get("session_id") == sid]
    types = [e["type"] for e in events]
    assert types[:3] == ["prompt.started", "text-delta", "prompt.finished"]
    ids = [e["_id"] for e in events[:3]]
    assert ids == sorted(ids)


def test_ca3_resume_com_last_event_id_sem_perda(live_server):
    base, auth, _ = live_server
    session = httpx.post(f"{base}/api/session", auth=auth, json={"title": "s2"}).json()
    sid = session["id"]
    httpx.post(f"{base}/api/session/{sid}/prompt", auth=auth, json={"text": "oi"})

    # primeiro fluxo: lê tudo
    first: list[str] = []
    with httpx.stream(
        "GET",
        f"{base}/api/event",
        auth=auth,
        headers={"Last-Event-ID": "0"},
        timeout=10.0,
    ) as stream:
        for line in stream.iter_lines():
            first.append(line + "\n")
            if "".join(first).count("data:") >= 3:
                break
    todos = _parse_sse(first)
    corte = todos[1]["_id"]

    # reconecta a partir do corte — sem perda nem duplicação
    resumed: list[str] = []
    with httpx.stream(
        "GET",
        f"{base}/api/event",
        auth=auth,
        headers={"Last-Event-ID": str(corte)},
        timeout=10.0,
    ) as stream:
        for line in stream.iter_lines():
            resumed.append(line + "\n")
            if "".join(resumed).count("data:") >= 1:
                break
    depois = _parse_sse(resumed)
    assert depois
    assert depois[0]["_id"] == corte + 1
    ids_origem = {e["_id"] for e in todos if e["_id"] <= corte}
    assert all(e["_id"] not in ids_origem for e in depois)


def test_sessao_history_message_e_context(live_server):
    base, auth, _ = live_server
    sid = httpx.post(f"{base}/api/session", auth=auth, json={"title": "s3"}).json()["id"]
    httpx.post(f"{base}/api/session/{sid}/prompt", auth=auth, json={"text": "oi"})

    messages = httpx.get(f"{base}/api/session/{sid}/message", auth=auth).json()
    assert {m["role"] for m in messages} == {"user", "assistant"}

    history = httpx.get(f"{base}/api/session/{sid}/history", auth=auth).json()
    assert [m["role"] for m in history] == ["user", "assistant"]

    context = httpx.get(f"{base}/api/session/{sid}/context", auth=auth).json()
    assert context["message_count"] == 2
    assert context["part_count"] == 2


def test_agent_model_update_e_fs_read(live_server, tmp_path: Path):
    base, auth, _ = live_server
    sid = httpx.post(f"{base}/api/session", auth=auth, json={"title": "s4"}).json()["id"]

    r = httpx.post(f"{base}/api/session/{sid}/model", auth=auth, json={"model": "anthropic/claude"})
    assert r.json()["model"] == "anthropic/claude"
    r = httpx.post(f"{base}/api/session/{sid}/agent", auth=auth, json={"agent": "plan"})
    assert r.json()["agent"] == "plan"

    alvo = tmp_path / "arquivo.txt"
    alvo.write_text("conteudo do arquivo", encoding="utf-8")
    fs = httpx.get(f"{base}/api/fs/read", auth=auth, params={"path": str(alvo)})
    assert fs.status_code == 200
    assert "conteudo do arquivo" in fs.json()["content"]

    assert httpx.get(f"{base}/api/permission/saved", auth=auth).status_code == 200
    assert (
        httpx.post(
            f"{base}/api/permission/request",
            auth=auth,
            json={"permission": "read", "details": "x.py"},
        ).json()["decision"]
        == "allow"
    )
