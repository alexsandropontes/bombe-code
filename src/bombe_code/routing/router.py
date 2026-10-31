"""Hybrid router directing slices to optimal provider based on complexity."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

from bombe_code.routing.classifier import ComplexityAnalysis
from bombe_code.routing.quota_manager import QuotaExhaustedError, QuotaManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RoutingDecision(BaseModel):
    """Immutable decision detailing selected provider and model for a slice."""

    model_config = ConfigDict(frozen=True)

    provider_name: str
    model_name: str
    tier: str
    is_fallback: bool = False
    reason: str


class HybridRouter:
    """Routes execution between local vLLM models and cloud providers."""

    def __init__(
        self,
        quota_checker: Callable[[str], bool] | None = None,
        quota_manager: QuotaManager | None = None,
    ) -> None:
        self._quota_manager = quota_manager
        if quota_checker is not None:
            self._quota_checker = quota_checker
        elif quota_manager is not None:
            self._quota_checker = quota_manager.is_available
        else:
            self._quota_checker = lambda _p: True

    def route(self, analysis: ComplexityAnalysis, force_local: bool = False) -> RoutingDecision:
        """Route slice to provider and model based on complexity tier and quota availability."""
        tier = analysis.recommended_tier

        if tier == "junior":
            return RoutingDecision(
                provider_name="vllm-local",
                model_name="gemma-4b",
                tier=tier,
                is_fallback=False,
                reason="Junior tier assigned to lightweight local model for zero-cost execution",
            )

        if tier == "pleno":
            return RoutingDecision(
                provider_name="vllm-local",
                model_name="qwen-9b",
                tier=tier,
                is_fallback=False,
                reason="Pleno tier assigned to high-performance local Qwen 9B model",
            )

        # Senior Tier (Score 3)
        return self._route_senior(tier, force_local)

    def _route_senior(self, tier: str, force_local: bool) -> RoutingDecision:
        if force_local:
            return RoutingDecision(
                provider_name="vllm-local",
                model_name="gemma-26b-awq",
                tier=tier,
                is_fallback=True,
                reason="Fallback triggered by force_local flag: using senior local model gemma-26b-awq",
            )

        target_cloud_provider = "cloud_zai"
        has_quota = self._quota_checker(target_cloud_provider)

        if has_quota:
            return RoutingDecision(
                provider_name=target_cloud_provider,
                model_name="glm-4-plus",
                tier=tier,
                is_fallback=False,
                reason="Senior tier assigned to preferred cloud provider (quota available)",
            )

        return RoutingDecision(
            provider_name="vllm-local",
            model_name="gemma-26b-awq",
            tier=tier,
            is_fallback=True,
            reason="Fallback triggered by exhausted cloud quota (429/limit reached): using senior local model gemma-26b-awq",
        )

    async def execute_with_failover(
        self,
        call_fn: Callable[[], Awaitable[T]],
        fallback_fn: Callable[[], Awaitable[T]],
        provider_name: str,
    ) -> T:
        """Execute call_fn with automatic fallback to fallback_fn if cloud quota is exhausted."""
        if self._quota_manager is not None and not self._quota_manager.is_available(provider_name):
            logger.warning(
                "Provider %s is locked due to quota exhaustion; short-circuiting directly to local fallback.",
                provider_name,
            )
            return await fallback_fn()

        try:
            return await call_fn()
        except QuotaExhaustedError as exc:
            logger.warning(
                "Intercepted QuotaExhaustedError from %s: %s. Failing over to local cluster.",
                provider_name,
                exc,
            )
            if self._quota_manager is not None:
                self._quota_manager.record_exhausted(
                    provider=provider_name,
                    error_code=429,
                    error_message=str(exc),
                )
            return await fallback_fn()
        except Exception as exc:
            err_msg = str(exc).lower()
            status_code = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if (
                status_code == 429
                or "429" in err_msg
                or "quota" in err_msg
                or "rate limit" in err_msg
            ):
                logger.warning(
                    "Intercepted HTTP 429 / quota error from %s: %s. Failing over to local cluster.",
                    provider_name,
                    exc,
                )
                if self._quota_manager is not None:
                    self._quota_manager.record_exhausted(
                        provider=provider_name,
                        error_code=429,
                        error_message=str(exc),
                    )
                return await fallback_fn()
            raise
