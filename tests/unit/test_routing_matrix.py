"""Comprehensive unit tests for the Cognitive Routing Matrix, Quick Setup, and Quota Failover."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bombe_code.cli.main import app
from bombe_code.providers.auth import load_auth, save_api_key, save_provider_url
from bombe_code.routing.classifier import ComplexityAnalysis
from bombe_code.routing.matrix import (
    DemandSituation,
    ModelNotConfiguredError,
    ModelSlot,
    RoutingMatrixConfig,
    SituationRoute,
    load_matrix,
    save_matrix,
)
from bombe_code.routing.quota_manager import QuotaManager
from bombe_code.routing.router import HybridRouter

runner = CliRunner()


def test_matrix_is_configured_and_quick_setup(tmp_path: Path):
    """Verify quick_setup replicates primary and fallback across all 6 demand situations."""
    matrix = RoutingMatrixConfig()
    assert matrix.is_configured() is False

    primary = ModelSlot(provider="zai", model="glm-5.3-flash")
    fallback = ModelSlot(provider="vllm-local", model="qwen-3.8-9b")

    matrix.quick_setup(primary=primary, fallback=fallback)
    assert matrix.is_configured() is True

    # Assert all 6 situations received the replicated configuration
    for situation in DemandSituation:
        route = matrix.get_route(situation)
        assert route.primary is not None
        assert route.primary.provider == "zai"
        assert route.primary.model == "glm-5.3-flash"
        assert route.fallback is not None
        assert route.fallback.provider == "vllm-local"
        assert route.fallback.model == "qwen-3.8-9b"


def test_matrix_set_route_customization(tmp_path: Path):
    """Verify individual customization of demand situations."""
    matrix = RoutingMatrixConfig()
    matrix.quick_setup(primary=ModelSlot(provider="zai", model="glm-5.3-flash"))

    # Customize Senior to Claude 3.5
    matrix.set_route(
        DemandSituation.SENIOR,
        primary=ModelSlot(provider="anthropic", model="claude-3-5-sonnet"),
        fallback=ModelSlot(provider="vllm-local", model="gemma-4-26b-a4b"),
    )

    senior_route = matrix.get_route(DemandSituation.SENIOR)
    assert senior_route.primary.provider == "anthropic"
    assert senior_route.primary.model == "claude-3-5-sonnet"
    assert senior_route.fallback.model == "gemma-4-26b-a4b"

    # Junior remains zai/glm-5.3-flash
    jr_route = matrix.get_route(DemandSituation.JUNIOR)
    assert jr_route.primary.provider == "zai"


def test_matrix_persistence_atomic(tmp_path: Path):
    """Verify atomic load and save of routing matrix."""
    matrix_file = tmp_path / "models_matrix.json"
    matrix = RoutingMatrixConfig()
    matrix.quick_setup(primary=ModelSlot(provider="ollama", model="llama3.1:8b"))

    save_matrix(matrix, path=matrix_file)
    assert matrix_file.exists()

    loaded = load_matrix(path=matrix_file)
    assert loaded.is_configured() is True
    assert loaded.get_route(DemandSituation.JUNIOR).primary.model == "llama3.1:8b"


def test_hybrid_router_uses_configured_matrix(tmp_path: Path):
    """Verify HybridRouter routes accurately based on custom matrix configuration."""
    matrix = RoutingMatrixConfig()
    matrix.set_route(
        DemandSituation.JUNIOR,
        primary=ModelSlot(provider="vllm-local", model="gemma-4-e4b"),
    )
    matrix.set_route(
        DemandSituation.SENIOR,
        primary=ModelSlot(provider="zai", model="glm-5.3-flash"),
        fallback=ModelSlot(provider="vllm-local", model="gemma-4-26b-a4b"),
    )

    # Quota available
    router = HybridRouter(quota_checker=lambda p: True, matrix=matrix)
    jr_decision = router.route(ComplexityAnalysis(score=1, reasons=["small"], recommended_tier="junior"))
    assert jr_decision.provider_name == "vllm-local"
    assert jr_decision.model_name == "gemma-4-e4b"
    assert jr_decision.is_fallback is False

    sr_decision = router.route(ComplexityAnalysis(score=3, reasons=["large"], recommended_tier="senior"))
    assert sr_decision.provider_name == "zai"
    assert sr_decision.model_name == "glm-5.3-flash"
    assert sr_decision.is_fallback is False


def test_hybrid_router_failover_when_cloud_in_cooldown(tmp_path: Path):
    """Verify HybridRouter switches to fallback when cloud provider is in cooldown / exhausted."""
    matrix = RoutingMatrixConfig()
    matrix.set_route(
        DemandSituation.FINAL_REVIEW,
        primary=ModelSlot(provider="zai", model="glm-5.3-flash"),
        fallback=ModelSlot(provider="vllm-local", model="qwen-3.8-9b"),
    )

    # Cloud zai quota exhausted
    router = HybridRouter(quota_checker=lambda p: False, matrix=matrix)
    review_decision = router.route_situation(DemandSituation.FINAL_REVIEW)

    assert review_decision.provider_name == "vllm-local"
    assert review_decision.model_name == "qwen-3.8-9b"
    assert review_decision.is_fallback is True
    assert "fallback" in review_decision.reason.lower()


def test_cli_models_setup_and_matrix_display(tmp_path: Path, monkeypatch):
    """Verify CLI commands for quick setup and matrix visualization."""
    matrix_file = tmp_path / "models_matrix.json"
    monkeypatch.setenv("BOMBE_MODELS_MATRIX_PATH", str(matrix_file))

    # 1. Quick setup via CLI
    res = runner.invoke(
        app,
        ["models", "setup", "-p", "zai", "-m", "glm-5.3-flash", "-fp", "vllm-local", "-fm", "qwen-3.8-9b"],
    )
    assert res.exit_code == 0
    assert "Configuração concluída com sucesso" in res.output

    # 2. View matrix via CLI
    res_matrix = runner.invoke(app, ["models", "matrix"], env={"COLUMNS": "180"})
    assert res_matrix.exit_code == 0
    assert "Matriz Cognitiva de Modelos" in res_matrix.output
    assert "zai/glm-5.3-flash" in res_matrix.output
    assert "vllm-local/qwen-3.8-9b" in res_matrix.output


def test_cli_models_set_advanced_customization(tmp_path: Path, monkeypatch):
    """Verify CLI command for advanced situation customization."""
    matrix_file = tmp_path / "models_matrix.json"
    monkeypatch.setenv("BOMBE_MODELS_MATRIX_PATH", str(matrix_file))

    # Setup baseline
    runner.invoke(app, ["models", "setup", "-p", "zai", "-m", "glm-5.3-flash"])

    # Customize final_review
    res = runner.invoke(
        app,
        ["models", "set", "final_review", "-p", "anthropic", "-m", "claude-3-5-sonnet", "-fp", "vllm-local", "-fm", "qwen-3.8-9b"],
    )
    assert res.exit_code == 0
    assert "final_review' atualizada com sucesso" in res.output

    matrix = load_matrix(path=matrix_file)
    rev_route = matrix.get_route(DemandSituation.FINAL_REVIEW)
    assert rev_route.primary.provider == "anthropic"
    assert rev_route.primary.model == "claude-3-5-sonnet"


def test_no_opencode_auth_fallback(tmp_path: Path, monkeypatch):
    """Ensure Bombe Code never reads from ~/.local/share/opencode/auth.json."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))

    # Create dummy OpenCode auth.json
    opencode_dir = fake_home / ".local" / "share" / "opencode"
    opencode_dir.mkdir(parents=True)
    (opencode_dir / "auth.json").write_text(json.dumps({"opencode_secret": {"api_key": "LEAKED_KEY"}}))

    # Ensure Bombe Code does NOT load it
    auth = load_auth()
    assert "opencode_secret" not in auth
