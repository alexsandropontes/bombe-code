"""Local vLLM Provider Adapter and SingleModelQueueManager."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any, Self

import httpx

from bombe_code.providers.protocol import (
    CompletionChunk,
    VllmConnectionError,
)

DEFAULT_VLLM_PORT = 18096
DEFAULT_VLLM_HOST = "127.0.0.1"


class SingleModelQueueManager:
    """Enforces Fila Indiana: strictly at most one model loaded and executing in GPU VRAM."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_model: str | None = None

    @property
    def current_active_model(self) -> str | None:
        """The model currently or most recently active in VRAM."""
        return self._current_model

    @property
    def is_locked(self) -> bool:
        """Whether an inference session currently holds the GPU lock."""
        return self._lock.locked()

    @asynccontextmanager
    async def acquire(self, model_name: str) -> AsyncIterator[str]:
        """Acquire exclusive GPU execution lock for model_name."""
        async with self._lock:
            self._current_model = model_name
            yield model_name


class LocalVllmAdapter:
    """Adapter for local vLLM server running on port 18096 with OpenAI-compatible API."""

    def __init__(
        self,
        host: str = DEFAULT_VLLM_HOST,
        port: int = DEFAULT_VLLM_PORT,
        client: httpx.AsyncClient | None = None,
        queue_manager: SingleModelQueueManager | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.base_url = f"http://{self.host}:{self.port}/v1"
        self._client = client
        self._queue_manager = queue_manager or SingleModelQueueManager()

    @property
    def name(self) -> str:
        return "vllm-local"

    @property
    def provider_type(self) -> str:
        return "local"

    @property
    def queue_manager(self) -> SingleModelQueueManager:
        return self._queue_manager

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        """Close underlying HTTP client if owned by this adapter."""
        if getattr(self, "_owns_client", False) and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def check_health(self) -> bool:
        """Check if local vLLM is responding."""
        try:
            client = self._get_client()
            response = await client.get(f"{self.base_url}/models", timeout=2.0)
            return response.status_code == 200
        except (httpx.HTTPError, httpx.NetworkError, TimeoutError):
            return False

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[CompletionChunk]:
        """Stream chat completions from local vLLM under Fila Indiana locking."""
        target_model = model or "default"
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        async with self._queue_manager.acquire(target_model):
            try:
                client = self._get_client()
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        content = await response.aread()
                        raise VllmConnectionError(
                            f"vLLM returned HTTP {response.status_code}: {content.decode('utf-8', errors='replace')}"
                        )

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            break
                        if line.startswith("data: "):
                            raw_data = line[6:]
                            try:
                                data = json.loads(raw_data)
                            except json.JSONDecodeError:
                                continue

                            choices = data.get("choices", [])
                            if not choices:
                                continue
                            choice = choices[0]
                            delta_content = choice.get("delta", {}).get("content", "")
                            finish_reason = choice.get("finish_reason")
                            model_returned = data.get("model", target_model)
                            usage = data.get("usage")

                            yield CompletionChunk(
                                delta=delta_content,
                                finish_reason=finish_reason,
                                model=model_returned,
                                usage=usage,
                            )
            except httpx.HTTPError as exc:
                raise VllmConnectionError(
                    f"Failed to connect to local vLLM on {self.base_url}: {exc}"
                ) from exc
