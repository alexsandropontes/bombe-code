"""Unit tests for QuotaManager, Circuit Breaker, and HybridRouter failover."""

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from bombe_code.routing.classifier import ComplexityAnalysis
from bombe_code.routing.quota_manager import (
    ProviderQuotaStatus,
    QuotaExhaustedError,
    QuotaManager,
    QuotaState,
)
from bombe_code.routing.router import HybridRouter


def test_provider_quota_status_immutable():
    """Verify ProviderQuotaStatus schema is frozen."""
    status = ProviderQuotaStatus(status="healthy", consecutive_failures=0)
    assert status.status == "healthy"
    assert status.consecutive_failures == 0
    assert status.locked_until is None

    with pytest.raises(ValidationError):
        status.status = "exhausted"  # type: ignore


def test_quota_manager_defaults_healthy_for_unknown_provider(tmp_path: Path):
    """Verify unknown provider defaults to healthy and available."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)

    assert manager.is_available("cloud_zai") is True
    status = manager.get_provider_status("cloud_zai")
    assert status.status == "healthy"


def test_quota_manager_record_exhausted_persists_atomic_lock(tmp_path: Path):
    """Verify record_exhausted sets locked_until, marks exhausted and persists to disk."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)

    manager.record_exhausted(
        provider="cloud_zai",
        lock_duration_seconds=3600,
        error_code=429,
        error_message="Too Many Requests / Quota Exceeded",
    )

    assert manager.is_available("cloud_zai") is False
    status = manager.get_provider_status("cloud_zai")
    assert status.status == "exhausted"
    assert status.last_error_code == 429
    assert status.consecutive_failures == 1
    assert status.locked_until is not None
    assert status.locked_until > datetime.now(UTC)

    assert state_file.exists()

    # Re-instantiate manager from disk to confirm persistence
    fresh_manager = QuotaManager(state_path=state_file)
    assert fresh_manager.is_available("cloud_zai") is False
    fresh_status = fresh_manager.get_provider_status("cloud_zai")
    assert fresh_status.status == "exhausted"
    assert fresh_status.last_error_code == 429


def test_quota_manager_lock_expiration(tmp_path: Path):
    """Verify expired locked_until automatically marks provider available."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)

    # Set lock that already expired 10 seconds ago
    past_time = datetime.now(UTC) - timedelta(seconds=10)
    state = QuotaState(
        providers={
            "cloud_zai": ProviderQuotaStatus(
                status="exhausted",
                consecutive_failures=1,
                last_error_code=429,
                locked_until=past_time,
            )
        }
    )
    manager._state = state
    manager._save_state()

    assert manager.is_available("cloud_zai") is True


def test_quota_manager_reset(tmp_path: Path):
    """Verify reset restores provider to healthy and available."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)

    manager.record_exhausted("cloud_zai", lock_duration_seconds=3600)
    assert manager.is_available("cloud_zai") is False

    manager.reset("cloud_zai")
    assert manager.is_available("cloud_zai") is True
    status = manager.get_provider_status("cloud_zai")
    assert status.status == "healthy"
    assert status.locked_until is None


@pytest.mark.anyio
async def test_hybrid_router_failover_on_429_within_2_seconds(tmp_path: Path):
    """Verify execute_with_failover catches 429, locks quota, and executes fallback within 2s."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)
    router = HybridRouter(quota_manager=manager)

    start_time = time.monotonic()

    async def cloud_call():
        raise QuotaExhaustedError("HTTP 429 Too Many Requests / Quota Exceeded")

    async def local_fallback():
        return "local_inference_success"

    result = await router.execute_with_failover(
        call_fn=cloud_call,
        fallback_fn=local_fallback,
        provider_name="cloud_zai",
    )

    duration = time.monotonic() - start_time

    assert result == "local_inference_success"
    assert duration < 2.0
    assert manager.is_available("cloud_zai") is False


@pytest.mark.anyio
async def test_hybrid_router_short_circuits_locked_provider(tmp_path: Path):
    """Verify execute_with_failover bypasses cloud call if provider is already locked."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)
    manager.record_exhausted("cloud_zai", lock_duration_seconds=3600)
    router = HybridRouter(quota_manager=manager)

    cloud_called = False

    async def cloud_call():
        nonlocal cloud_called
        cloud_called = True
        return "cloud_result"

    async def local_fallback():
        return "fallback_result"

    result = await router.execute_with_failover(
        call_fn=cloud_call,
        fallback_fn=local_fallback,
        provider_name="cloud_zai",
    )

    assert result == "fallback_result"
    assert cloud_called is False  # Network was never attempted


def test_hybrid_router_integration_with_quota_manager(tmp_path: Path):
    """Verify HybridRouter automatically routes Senior to fallback when QuotaManager is locked."""
    state_file = tmp_path / "quota_state.json"
    manager = QuotaManager(state_path=state_file)
    manager.record_exhausted("cloud_zai", lock_duration_seconds=3600)

    router = HybridRouter(quota_manager=manager)
    analysis = ComplexityAnalysis(score=3, reasons=["Critical protocol"], recommended_tier="senior")
    decision = router.route(analysis)

    assert decision.provider_name == "vllm-local"
    assert decision.model_name == "gemma-26b-awq"
    assert decision.is_fallback is True
    assert "quota" in decision.reason.lower()
