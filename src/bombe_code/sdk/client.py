"""Cliente SDK Python tipado para o Bombe Code Server."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .models import PromptResult, SDKEvent, SessionModel


class BombeSDK:
    """Cliente assíncrono tipado para APIs do Bombe Code Server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:4096",
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout

    async def create_session(self, title: str = "") -> SessionModel:
        async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=self.timeout) as client:
            resp = await client.post("/api/session", json={"title": title})
            resp.raise_for_status()
            return SessionModel.model_validate(resp.json())

    async def list_sessions(self) -> list[SessionModel]:
        async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=self.timeout) as client:
            resp = await client.get("/api/session")
            resp.raise_for_status()
            return [SessionModel.model_validate(s) for s in resp.json()]

    async def send_prompt(self, session_id: str, text: str) -> PromptResult:
        async with httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=self.timeout) as client:
            resp = await client.post(f"/api/session/{session_id}/prompt", json={"text": text})
            resp.raise_for_status()
            return PromptResult.model_validate(resp.json())

    async def stream_events(
        self, session_id: str, last_event_id: int = 0
    ) -> AsyncIterator[SDKEvent]:
        headers = {}
        if last_event_id > 0:
            headers["Last-Event-ID"] = str(last_event_id)

        async with (
            httpx.AsyncClient(base_url=self.base_url, auth=self.auth, timeout=None) as client,
            client.stream(
                "GET", f"/api/session/{session_id}/event?last_event_id={last_event_id}", headers=headers
            ) as response,
        ):
            response.raise_for_status()
            current_id: int | None = None
            current_data_lines: list[str] = []

            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    if current_data_lines:
                        data_str = "\n".join(current_data_lines)
                        try:
                            payload: dict[str, Any] = json.loads(data_str)
                            if current_id is not None:
                                payload["_event_id"] = current_id
                            yield SDKEvent(
                                type=payload.get("type", "unknown"),
                                session_id=payload.get("session_id"),
                                _event_id=current_id,
                                raw=payload,
                            )
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
