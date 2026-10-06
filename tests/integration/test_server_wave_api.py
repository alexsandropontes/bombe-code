"""Testes de integração da API da ONDA no Bombe Code Server (FastAPI + SSE)."""

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bombe_code.server.app import create_app


class DummyAdapter:
    provider = "dummy"
    model = "dummy-model"

    def stream(self, messages, tools=None, system=None):
        yield {"type": "text-delta", "text": "resposta dummy"}
        yield {"type": "finish", "reason": "stop"}


@pytest.fixture
def auth_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from bombe_code.server.app import _ensure_password

    pwd = _ensure_password()
    raw = f"bombe:{pwd}".encode()
    return {"Authorization": f"Basic {base64.b64encode(raw).decode('utf-8')}"}


def test_server_wave_routes_lifecycle(tmp_path: Path, auth_header: dict[str, str]):
    app = create_app(adapter=DummyAdapter(), project_dir=str(tmp_path))
    client = TestClient(app)

    # 1. Status inicial
    res = client.get("/api/wave/status", headers=auth_header)
    assert res.status_code == 200
    data = res.json()
    assert "wave_id" in data
    assert "stage" in data

    # 2. Inicia uma nova ONDA via HTTP
    start_payload = {
        "wave_id": "ONDA-999",
        "autonomy_mode": "SEMI_AUTO",
        "engineering_mode": "tdd-code",
        "force": True,
    }
    res = client.post("/api/wave/start", json=start_payload, headers=auth_header)
    assert res.status_code == 200
    assert res.json().get("success") is True

    # 3. Status atualizado
    res = client.get("/api/wave/status", headers=auth_header)
    assert res.status_code == 200
    assert res.json()["wave_id"] == "ONDA-999"


def test_server_prompt_routes_turing_intent_in_tdd_mode(
    tmp_path: Path, auth_header: dict[str, str]
):
    app = create_app(adapter=DummyAdapter(), project_dir=str(tmp_path))
    client = TestClient(app)

    # Cria sessão
    res = client.post(
        "/api/session",
        json={"title": "TDD Session", "directory": str(tmp_path)},
        headers=auth_header,
    )
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Envia prompt de ideia que o Turing Waiter reconhece como início de ONDA / DISCUSS
    res = client.post(
        f"/api/session/{session_id}/prompt",
        json={"text": "Quero criar um app de onboarding com quiz financeiro"},
        headers=auth_header,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "text" in data
