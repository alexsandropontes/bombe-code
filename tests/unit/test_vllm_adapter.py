"""Unit tests for LLMProviderProtocol, Chunks, SingleModelQueueManager, and LocalVllmAdapter."""

from collections.abc import AsyncIterator
from dataclasses import FrozenInstanceError

import httpx
import pytest

from bombe_code.providers.local_vllm import (
    DEFAULT_VLLM_PORT,
    LocalVllmAdapter,
    SingleModelQueueManager,
)
from bombe_code.providers.protocol import (
    CompletionChunk,
    LLMProviderError,
    LLMProviderProtocol,
    QueueCapacityError,
    ToolCallChunk,
    VllmConnectionError,
)


def test_completion_chunk_immutability():
    """Verify CompletionChunk is a frozen dataclass with expected attributes."""
    chunk = CompletionChunk(
        delta="hello", finish_reason=None, model="test-model", usage={"tokens": 1}
    )
    assert chunk.delta == "hello"
    assert chunk.finish_reason is None
    assert chunk.model == "test-model"
    assert chunk.usage == {"tokens": 1}

    with pytest.raises(FrozenInstanceError):
        chunk.delta = "modified"  # type: ignore


def test_tool_call_chunk_immutability():
    """Verify ToolCallChunk is a frozen dataclass with expected attributes."""
    chunk = ToolCallChunk(
        index=0, call_id="call_123", name="read_file", arguments_delta='{"path": "'
    )
    assert chunk.index == 0
    assert chunk.call_id == "call_123"
    assert chunk.name == "read_file"
    assert chunk.arguments_delta == '{"path": "'

    with pytest.raises(FrozenInstanceError):
        chunk.name = "write_file"  # type: ignore


def test_custom_exceptions_hierarchy():
    """Verify custom exception inheritance."""
    assert issubclass(VllmConnectionError, LLMProviderError)
    assert issubclass(QueueCapacityError, LLMProviderError)
    assert issubclass(LLMProviderError, Exception)


def test_protocol_runtime_checkable():
    """Verify LLMProviderProtocol is runtime checkable."""

    class DummyValidProvider:
        @property
        def name(self) -> str:
            return "dummy"

        @property
        def provider_type(self) -> str:
            return "local"

        async def stream_chat(
            self,
            messages: list[dict],
            model: str | None = None,
            temperature: float = 0.7,
            **kwargs,
        ) -> AsyncIterator[CompletionChunk]:
            if False:
                yield CompletionChunk(delta="")

        async def check_health(self) -> bool:
            return True

    class DummyInvalidProvider:
        pass

    assert isinstance(DummyValidProvider(), LLMProviderProtocol)
    assert not isinstance(DummyInvalidProvider(), LLMProviderProtocol)


@pytest.mark.anyio
async def test_single_model_queue_manager_enforces_one_model():
    """Verify SingleModelQueueManager allows only one active model at a time."""
    manager = SingleModelQueueManager()
    assert manager.current_active_model is None

    async with manager.acquire("model-a"):
        assert manager.current_active_model == "model-a"
        assert manager.is_locked is True

    assert manager.current_active_model == "model-a"
    assert manager.is_locked is False

    async with manager.acquire("model-b"):
        assert manager.current_active_model == "model-b"
        assert manager.is_locked is True

    assert manager.is_locked is False


def test_local_vllm_adapter_conforms_to_protocol():
    """Verify LocalVllmAdapter implements LLMProviderProtocol."""
    adapter = LocalVllmAdapter()
    assert isinstance(adapter, LLMProviderProtocol)
    assert adapter.name == "vllm-local"
    assert adapter.provider_type == "local"
    assert adapter.port == DEFAULT_VLLM_PORT
    assert adapter.port == 18096


@pytest.mark.anyio
async def test_local_vllm_adapter_check_health_success():
    """Verify check_health returns True on HTTP 200."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    adapter = LocalVllmAdapter(client=client)

    healthy = await adapter.check_health()
    assert healthy is True


@pytest.mark.anyio
async def test_local_vllm_adapter_check_health_failure():
    """Verify check_health returns False when connection is refused or returns 500."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused on 18096")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    adapter = LocalVllmAdapter(client=client)

    healthy = await adapter.check_health()
    assert healthy is False


@pytest.mark.anyio
async def test_local_vllm_adapter_stream_chat_success():
    """Verify stream_chat parses SSE lines and yields CompletionChunk."""
    sse_body = (
        'data: {"choices": [{"delta": {"content": "Hello"}}], "model": "qwen2.5-coder-7b"}\n\n'
        'data: {"choices": [{"delta": {"content": " world!"}}], "model": "qwen2.5-coder-7b"}\n\n'
        'data: {"choices": [{"finish_reason": "stop"}], "model": "qwen2.5-coder-7b", "usage": {"total_tokens": 10}}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.method == "POST"
        return httpx.Response(
            200, content=sse_body.encode("utf-8"), headers={"content-type": "text/event-stream"}
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    adapter = LocalVllmAdapter(client=client)

    chunks: list[CompletionChunk] = []
    async for chunk in adapter.stream_chat(
        messages=[{"role": "user", "content": "hi"}],
        model="qwen2.5-coder-7b",
    ):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert chunks[0].delta == "Hello"
    assert chunks[1].delta == " world!"
    assert chunks[2].finish_reason == "stop"
    assert chunks[2].usage == {"total_tokens": 10}


@pytest.mark.anyio
async def test_local_vllm_adapter_stream_chat_connection_error():
    """Verify stream_chat raises VllmConnectionError on connection failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("vLLM offline")

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    adapter = LocalVllmAdapter(client=client)

    with pytest.raises(VllmConnectionError):
        async for _ in adapter.stream_chat(messages=[{"role": "user", "content": "hi"}]):
            pass
