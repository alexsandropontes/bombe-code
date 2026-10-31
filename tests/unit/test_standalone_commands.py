"""Unit tests for standalone commands, project governance, and ShipEngine pre-flight gates."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bombe_code.cli.main import app
from bombe_code.config.project_config import InvalidModeError, ProjectConfigManager
from bombe_code.domain.contracts.ship import PromotionResult, ShipTarget
from bombe_code.orchestration.ship_engine import ShipEngine
from bombe_code.orchestration.standalone_engine import StandaloneEngine

runner = CliRunner()


def test_ship_engine_pre_flight_fails_blocks_promotion(tmp_path: Path) -> None:
    """Pre-flight test gate failure must abort promotion with tests_passed=False."""
    engine = ShipEngine(project_dir=tmp_path, test_runner=lambda: False)
    res = engine.promote_to_environment(ShipTarget.DEV)

    assert isinstance(res, PromotionResult)
    assert res.success is False
    assert res.tests_passed is False
    assert res.target_branch == "dev"
    assert "falharam" in res.message


def test_ship_engine_pre_flight_passes_executes_promotion(tmp_path: Path) -> None:
    """Pre-flight test gate pass proceeds to promotion through PromotorDeBranches."""
    # Inicializa repo git fake para o PromotorDeBranches
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@bombe.com"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Agent"],
        cwd=str(tmp_path),
        capture_output=True,
        check=True,
    )

    test_file = tmp_path / "hello.txt"
    test_file.write_text("initial", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True, check=True
    )

    engine = ShipEngine(project_dir=tmp_path, test_runner=lambda: True)
    res = engine.promote_to_environment(ShipTarget.DEV)

    assert isinstance(res, PromotionResult)
    assert res.success is True
    assert res.tests_passed is True
    assert res.target_branch == "dev"
    assert len(res.source_commit) > 0


def test_standalone_engine_switch_mode_audits_metadata(tmp_path: Path) -> None:
    """switch_mode writes mode_origin and mode_migrated_at to .bombeconfig."""
    cfg_mgr = ProjectConfigManager(str(tmp_path))
    cfg = cfg_mgr.load()
    cfg.mode = "slice-code"
    cfg_mgr.save(cfg)

    engine = StandaloneEngine(project_dir=tmp_path)
    updated = engine.switch_mode("vibe-code")

    assert updated.mode == "vibe-code"
    assert updated.mode_origin == "slice-code"
    assert updated.mode_migrated_at is not None

    reloaded = cfg_mgr.load()
    assert reloaded.mode == "vibe-code"
    assert reloaded.mode_origin == "slice-code"
    assert reloaded.mode_migrated_at == updated.mode_migrated_at


def test_standalone_engine_switch_mode_invalid_raises(tmp_path: Path) -> None:
    """switch_mode raises InvalidModeError on unsupported engineering mode."""
    engine = StandaloneEngine(project_dir=tmp_path)
    with pytest.raises(InvalidModeError):
        engine.switch_mode("invalid-mode-xyz")


def test_standalone_engine_generate_status_report(tmp_path: Path) -> None:
    """generate_status_report compiles metadata, mode and inspected missions."""
    missions_dir = tmp_path / "docs" / "missions" / "01"
    missions_dir.mkdir(parents=True, exist_ok=True)
    (missions_dir / "mission.md").write_text("# Mission 01", encoding="utf-8")

    engine = StandaloneEngine(project_dir=tmp_path)
    rep = engine.generate_status_report()

    assert rep["project_name"] == tmp_path.name
    assert rep["mode"] in {"slice-code", "vibe-code"}
    assert rep["missions_count"] == 1
    assert rep["missions"][0]["id"] == "01"
    assert rep["missions"][0]["status"] == "active"


def test_standalone_engine_dispatch_task_and_qa_audits(tmp_path: Path) -> None:
    """dispatch_task, run_rca, run_review and run_simplify return compliant schemas."""
    engine = StandaloneEngine(project_dir=tmp_path)

    task_res = engine.dispatch_task("Implementar endpoint", agent="@barbara")
    assert task_res["success"] is True
    assert task_res["agent"] == "@barbara"
    assert task_res["status"] == "dispatched"

    rca_res = engine.run_rca("Timeout intermitente no banco")
    assert rca_res["success"] is True
    assert rca_res["agent"] == "@unclebob"
    assert len(rca_res["causes"]) == 5

    review_res = engine.run_review("src/backend")
    assert review_res["success"] is True
    assert review_res["axes"]["architecture"] == "passed"

    simplify_res = engine.run_simplify("src/backend/service.py")
    assert simplify_res["success"] is True
    assert simplify_res["cyclomatic_complexity"] == "healthy"


def test_cli_project_configure_updates_bombeconfig(tmp_path: Path) -> None:
    """bombe project configure updates parameters without corrupting other keys."""
    res = runner.invoke(
        app,
        [
            "project",
            "configure",
            "--mode",
            "vibe-code",
            "--backend-path",
            "src/api/",
            "--frontend-path",
            "src/web/",
            "--backend-language",
            "go",
            "--frontend-stack",
            "vue",
            "--autonomy",
            "semi-auto",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0
    assert "Configuração atualizada com sucesso" in res.output

    cfg_mgr = ProjectConfigManager(str(tmp_path))
    cfg = cfg_mgr.load()
    assert cfg.mode == "vibe-code"
    assert cfg.backend_path == "src/api/"
    assert cfg.frontend_path == "src/web/"
    assert cfg.backend_language == "go"
    assert cfg.frontend_stack == "vue"
    assert cfg.autonomy == "semi-auto"


def test_cli_project_ship_blocks_on_failing_pre_flight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """bombe project ship exits with code 1 when pre-flight tests fail."""
    # Monkeypatch do ShipEngine._run_pre_flight_tests para simular falha
    monkeypatch.setattr(ShipEngine, "_run_pre_flight_tests", lambda self: False)

    res = runner.invoke(app, ["project", "ship", "dev", "--project-dir", str(tmp_path)])
    assert res.exit_code == 1
    assert "Testes pré-flight falharam" in res.output or "Falha na promoção" in res.output


def test_cli_project_ship_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """bombe project ship succeeds when pre-flight passes and promotion is successful."""
    monkeypatch.setattr(ShipEngine, "_run_pre_flight_tests", lambda self: True)
    monkeypatch.setattr(
        ShipEngine,
        "promote_to_environment",
        lambda self, target: PromotionResult(
            success=True,
            source_commit="abcdef123456",
            target_branch="dev",
            message="Promoted successfully to dev",
            tests_passed=True,
            details=["OK"],
        ),
    )

    res = runner.invoke(app, ["project", "ship", "dev", "--project-dir", str(tmp_path)])
    assert res.exit_code == 0
    assert "Promoção Git concluída com sucesso" in res.output


def test_cli_standalone_commands(tmp_path: Path) -> None:
    """CLI root and sub-app commands mode, task, rca, review, simplify, status-report."""
    # mode
    res_mode = runner.invoke(app, ["mode", "vibe-code", "--project-dir", str(tmp_path)])
    assert res_mode.exit_code == 0
    assert "Modo de engenharia alterado" in res_mode.output

    # task
    res_task = runner.invoke(
        app,
        [
            "task",
            "Criar migração de banco",
            "--agent",
            "@codd",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert res_task.exit_code == 0
    assert "@codd" in res_task.output

    # rca
    res_rca = runner.invoke(app, ["rca", "Vazamento de memória", "--project-dir", str(tmp_path)])
    assert res_rca.exit_code == 0
    assert "Root Cause Analysis" in res_rca.output or "RCA" in res_rca.output

    # review
    res_review = runner.invoke(
        app, ["review", "src/backend", "--project-dir", str(tmp_path)]
    )
    assert res_review.exit_code == 0
    assert "Auditoria de Qualidade" in res_review.output

    # simplify
    res_simplify = runner.invoke(
        app, ["simplify", "src/backend", "--project-dir", str(tmp_path)]
    )
    assert res_simplify.exit_code == 0
    assert "Code Simplification Audit" in res_simplify.output

    # status-report
    res_report = runner.invoke(app, ["status-report", "--project-dir", str(tmp_path)])
    assert res_report.exit_code == 0
    assert "Status Report do Projeto" in res_report.output
