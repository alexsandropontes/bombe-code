"""Unit tests for ComplexityAnalysis, ComplexityClassifier, and HybridRouter."""

import pytest
from pydantic import ValidationError

from bombe_code.routing.classifier import (
    ComplexityAnalysis,
    ComplexityClassifier,
)
from bombe_code.routing.router import (
    HybridRouter,
)


def test_complexity_analysis_schema_valid():
    """Verify valid ComplexityAnalysis instantiates and is frozen."""
    analysis = ComplexityAnalysis(
        score=2,
        reasons=["Multiple files modified", "Integration scope"],
        recommended_tier="pleno",
    )
    assert analysis.score == 2
    assert len(analysis.reasons) == 2
    assert analysis.recommended_tier == "pleno"

    with pytest.raises(ValidationError):
        analysis.score = 3  # type: ignore (frozen model)


def test_complexity_analysis_schema_invalid():
    """Verify ComplexityAnalysis rejects invalid score, tier, or empty reasons."""
    with pytest.raises(ValidationError):
        ComplexityAnalysis(score=0, reasons=["Invalid score"], recommended_tier="junior")

    with pytest.raises(ValidationError):
        ComplexityAnalysis(score=4, reasons=["Invalid score"], recommended_tier="senior")

    with pytest.raises(ValidationError):
        ComplexityAnalysis(score=1, reasons=[], recommended_tier="junior")

    with pytest.raises(ValidationError):
        ComplexityAnalysis(score=1, reasons=["Valid reason"], recommended_tier="invalid_tier")


def test_complexity_classifier_junior_tier():
    """Verify single file < 50 lines with simple scope gets score 1 (junior)."""
    classifier = ComplexityClassifier()
    spec = {
        "affected_files": ["tests/unit/test_simple.py"],
        "estimated_lines": 35,
        "scope": "Add isolated unit test for helper function",
    }
    analysis = classifier.evaluate_slice(spec)

    assert analysis.score == 1
    assert analysis.recommended_tier == "junior"
    assert len(analysis.reasons) >= 1
    assert any("isolated" in r.lower() or "50 lines" in r.lower() for r in analysis.reasons)


def test_complexity_classifier_pleno_tier():
    """Verify multiple files or 50-200 lines gets score 2 (pleno)."""
    classifier = ComplexityClassifier()
    spec = {
        "affected_files": ["src/service.py", "tests/unit/test_service.py"],
        "estimated_lines": 120,
        "scope": "Implement business logic and unit tests",
    }
    analysis = classifier.evaluate_slice(spec)

    assert analysis.score == 2
    assert analysis.recommended_tier == "pleno"
    assert len(analysis.reasons) >= 1
    assert any("multiple files" in r.lower() or "lines" in r.lower() for r in analysis.reasons)


def test_complexity_classifier_senior_tier_due_to_critical_terms():
    """Verify presence of critical architectural terms triggers score 3 (senior)."""
    classifier = ComplexityClassifier()
    spec = {
        "affected_files": ["src/bombe_code/providers/protocol.py"],
        "estimated_lines": 40,
        "scope": "Define core protocol and async concurrency locks",
    }
    analysis = classifier.evaluate_slice(spec)

    assert analysis.score == 3
    assert analysis.recommended_tier == "senior"
    assert len(analysis.reasons) >= 1
    assert any("protocol" in r.lower() or "critical" in r.lower() for r in analysis.reasons)


def test_complexity_classifier_senior_tier_due_to_lines():
    """Verify estimated lines > 200 triggers score 3 (senior)."""
    classifier = ComplexityClassifier()
    spec = {
        "affected_files": ["src/large_module.py"],
        "estimated_lines": 280,
        "scope": "Extensive refactoring",
    }
    analysis = classifier.evaluate_slice(spec)

    assert analysis.score == 3
    assert analysis.recommended_tier == "senior"
    assert len(analysis.reasons) >= 1
    assert any("lines" in r.lower() for r in analysis.reasons)


def test_hybrid_router_routes_junior_to_local_gemma_4b():
    """Verify junior tier (score 1) always routes to lightweight local model."""
    router = HybridRouter()
    analysis = ComplexityAnalysis(score=1, reasons=["Isolated test"], recommended_tier="junior")
    decision = router.route(analysis)

    assert decision.provider_name == "vllm-local"
    assert decision.model_name in ("gemma-4b", "lfm-1.7b")
    assert decision.tier == "junior"
    assert decision.is_fallback is False


def test_hybrid_router_routes_pleno_to_local_qwen_9b():
    """Verify pleno tier (score 2) routes to local qwen-9b."""
    router = HybridRouter()
    analysis = ComplexityAnalysis(score=2, reasons=["Multiple files"], recommended_tier="pleno")
    decision = router.route(analysis)

    assert decision.provider_name == "vllm-local"
    assert decision.model_name == "qwen-9b"
    assert decision.tier == "pleno"
    assert decision.is_fallback is False


def test_hybrid_router_routes_senior_to_cloud_when_quota_available():
    """Verify senior tier (score 3) routes to cloud provider when quota is available."""
    router = HybridRouter(quota_checker=lambda provider: True)
    analysis = ComplexityAnalysis(score=3, reasons=["Core protocol"], recommended_tier="senior")
    decision = router.route(analysis)

    assert decision.provider_name == "cloud_zai"
    assert decision.tier == "senior"
    assert decision.is_fallback is False


def test_hybrid_router_fallbacks_senior_to_local_when_quota_exhausted():
    """Verify senior tier falls back to local gemma-26b-awq when cloud quota is exhausted."""
    # Quota checker returns False (simulating 429 quota exhaustion)
    router = HybridRouter(quota_checker=lambda provider: False)
    analysis = ComplexityAnalysis(score=3, reasons=["Core protocol"], recommended_tier="senior")
    decision = router.route(analysis)

    assert decision.provider_name == "vllm-local"
    assert decision.model_name == "gemma-26b-awq"
    assert decision.tier == "senior"
    assert decision.is_fallback is True
    assert "quota" in decision.reason.lower() or "fallback" in decision.reason.lower()


def test_hybrid_router_routes_to_local_when_force_local_is_true():
    """Verify force_local flag forces routing to local cluster even with cloud quota."""
    router = HybridRouter(quota_checker=lambda provider: True)
    analysis = ComplexityAnalysis(score=3, reasons=["Core protocol"], recommended_tier="senior")
    decision = router.route(analysis, force_local=True)

    assert decision.provider_name == "vllm-local"
    assert decision.model_name == "gemma-26b-awq"
    assert decision.is_fallback is True
    assert "force_local" in decision.reason.lower()
