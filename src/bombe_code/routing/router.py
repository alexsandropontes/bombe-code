"""Hybrid router directing slices to optimal provider based on complexity."""

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from bombe_code.routing.classifier import ComplexityAnalysis


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

    def __init__(self, quota_checker: Callable[[str], bool] | None = None) -> None:
        self._quota_checker = quota_checker or (lambda _p: True)

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
