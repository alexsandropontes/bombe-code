"""Cliente assíncrono HTTP + SSE para comunicação entre a TUI e o Bombe Code Server."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class BombeClient:
    def __init__(self, base_url: str, auth: tuple[str, str] | None = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout

    async def get_health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.get("/api/health")
            resp.raise_for_status()
            return resp.json()

    async def create_session(self, title: str = "", directory: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title}
        if directory:
            payload["directory"] = directory
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post("/api/session", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def list_sessions(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.get("/api/session")
            resp.raise_for_status()
            return resp.json()

    async def get_history(self, session_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.get(f"/api/session/{session_id}/history")
            resp.raise_for_status()
            return resp.json()

    async def send_prompt(
        self,
        session_id: str,
        text: str,
        model: str | None = None,
        stage: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"text": text}
        if model:
            payload["model"] = model
        if stage:
            payload["stage"] = stage
        # A inferência de LLM (especialmente local ou raciocínio extenso) pode demorar minutos.
        # Usa timeout estendido para não abortar enquanto o stream de eventos está ativo.
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=600.0
        ) as client:
            resp = await client.post(f"/api/session/{session_id}/prompt", json=payload)
            resp.raise_for_status()
            return resp.json()

    async def set_stage(self, session_id: str, stage: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(f"/api/session/{session_id}/stage", json={"stage": stage})
            resp.raise_for_status()
            return resp.json()

    async def get_stage(self, session_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.get(f"/api/session/{session_id}/stage")
            resp.raise_for_status()
            return resp.json()

    async def set_model(self, session_id: str, model: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(f"/api/session/{session_id}/model", json={"model": model})
            resp.raise_for_status()
            return resp.json()

    async def get_model(self, session_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.get(f"/api/session/{session_id}/model")
            resp.raise_for_status()
            return resp.json()

    async def send_compact(self, session_id: str, summary: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(
                f"/api/session/{session_id}/compact", json={"summary": summary}
            )
            resp.raise_for_status()
            return resp.json()

    async def send_revert(self, session_id: str, message_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(f"/api/session/{session_id}/revert/{message_id}")
            resp.raise_for_status()
            return resp.json()

    async def interrupt(self, session_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(f"/api/session/{session_id}/interrupt")
            resp.raise_for_status()
            return resp.json()

    async def reply_permission(
        self, session_id: str, permission: str, details: str, decision: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(
                f"/api/session/{session_id}/permission/reply",
                json={"permission": permission, "details": details, "decision": decision},
            )
            resp.raise_for_status()
            return resp.json()

    async def reply_question(self, session_id: str, question: str, answer: str) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, auth=self.auth, timeout=self.timeout
        ) as client:
            resp = await client.post(
                f"/api/session/{session_id}/question/reply",
                json={"question": question, "answer": answer},
            )
            resp.raise_for_status()
            return resp.json()

    async def stream_events(
        self, session_id: str, last_event_id: int = 0
    ) -> AsyncIterator[dict[str, Any]]:
        headers = {}
        if last_event_id > 0:
            headers["Last-Event-ID"] = str(last_event_id)

        async with (
            httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=None) as client,
            client.stream(
                "GET",
                f"/api/session/{session_id}/event?last_event_id={last_event_id}",
                headers=headers,
            ) as response,
        ):
            response.raise_for_status()
            current_id: int | None = None
            current_data_lines: list[str] = []

            async for line in response.aiter_lines():
                line = line.strip()
                if not line or line.startswith(":"):
                    if current_data_lines:
                        data_str = "\n".join(current_data_lines)
                        try:
                            payload = json.loads(data_str)
                            if current_id is not None:
                                payload["_event_id"] = current_id
                            yield payload
                        except json.JSONDecodeError:
                            pass
                        current_data_lines = []
                        current_id = None
                    continue

                if line.startswith("id:"):
                    try:
                        current_id = int(line[3:].strip())
                    except ValueError:
                        pass
                elif line.startswith("data:"):
                    current_data_lines.append(line[5:].strip())
