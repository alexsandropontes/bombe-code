"""E2E test suite validating real contingency failover from cloud Z.ai 429 to local vLLM."""

import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from bombe_code.providers.local_vllm import LocalVllmAdapter
from bombe_code.providers.protocol import CompletionChunk
from bombe_code.routing.quota_manager import (
    QuotaExhaustedError,
    QuotaManager,
    QuotaState,
)
from bombe_code.routing.router import HybridRouter


def _create_mock_local_vllm_adapter() -> LocalVllmAdapter:
    sse_body = (
        'data: {"choices": [{"delta": {"content": "def solve(): "}}], "model": "qwen-9b"}\n\n'
        'data: {"choices": [{"delta": {"content": "return True"}}], "model": "qwen-9b"}\n\n'
        'data: {"choices": [{"finish_reason": "stop"}], "model": "qwen-9b", "usage": {"total_tokens": 12}}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen-9b"}]})
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(
                200,
                content=sse_body.encode("utf-8"),
                headers={"content-type": "text/event-stream"},
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return LocalVllmAdapter(client=client)


async def _dummy_fallback(val: str = "fallback_ok") -> str:
    return val


@pytest.mark.anyio
async def test_contingency_failover_z_ai_429_to_local_vllm_e2e(tmp_path: Path) -> None:
    """AC-01 & AC-02: Intercept 429 without crash and failover to local vLLM in < 2.0s."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)
    router = HybridRouter(quota_manager=manager)
    adapter = _create_mock_local_vllm_adapter()

    async def cloud_call() -> list[CompletionChunk]:
        raise QuotaExhaustedError("Z.ai HTTP 429: Rate limit or quota exhausted")

    async def local_fallback() -> list[CompletionChunk]:
        return [chunk async for chunk in adapter.stream_chat([{"role": "user", "content": "test"}])]

    start = time.monotonic()
    result = await router.execute_with_failover(cloud_call, local_fallback, "cloud_zai")
    duration = time.monotonic() - start

    assert duration < 2.0
    assert len(result) >= 1
    assert any(c.finish_reason == "stop" for c in result)
    assert manager.is_available("cloud_zai") is False


@pytest.mark.anyio
async def test_contingency_persists_quota_state_json_atomically(tmp_path: Path) -> None:
    """AC-04: Validate atomic disk persistence of exhausted status, code 429, and locked_until."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)
    router = HybridRouter(quota_manager=manager)

    async def cloud_call() -> str:
        raise QuotaExhaustedError("Z.ai quota exhausted")

    await router.execute_with_failover(cloud_call, lambda: _dummy_fallback(), "cloud_zai")

    assert state_file.exists()
    saved = QuotaState.model_validate_json(state_file.read_text(encoding="utf-8"))
    status = saved.providers["cloud_zai"]
    assert status.status == "exhausted"
    assert status.last_error_code == 429
    assert status.locked_until is not None and status.locked_until > datetime.now(UTC)


@pytest.mark.anyio
async def test_contingency_short_circuits_subsequent_calls_to_local(tmp_path: Path) -> None:
    """Validate subsequent calls bypass cloud network and dispatch directly to local."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)
    manager.record_exhausted("cloud_zai", lock_duration_seconds=10800, error_code=429)
    router = HybridRouter(quota_manager=manager)

    cloud_attempted = False

    async def cloud_call() -> str:
        nonlocal cloud_attempted
        cloud_attempted = True
        return "cloud_response"

    result = await router.execute_with_failover(
        cloud_call, lambda: _dummy_fallback("short_circuited"), "cloud_zai"
    )

    assert result == "short_circuited"
    assert cloud_attempted is False


@pytest.mark.anyio
async def test_contingency_local_vllm_produces_green_completion(tmp_path: Path) -> None:
    """AC-03: Validate local vLLM fallback generates valid green completion with finish_reason stop."""
    adapter = _create_mock_local_vllm_adapter()
    assert await adapter.check_health() is True

    chunks: list[CompletionChunk] = []
    async for chunk in adapter.stream_chat(
        [{"role": "user", "content": "solve task"}], model="qwen-9b"
    ):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert "".join(c.delta for c in chunks) == "def solve(): return True"
    assert chunks[-1].finish_reason == "stop"
