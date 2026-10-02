"""Testes unitários para o guarda determinístico de etapas e integração de Tab na TUI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bombe_code.permissions.stage_guard import (
    STAGE_DISCUSS,
    STAGE_EXECUTE,
    STAGE_PLAN,
    STAGE_VALIDATE,
    is_code_path,
    is_production_code_path,
    validate_stage_permission,
)
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.tools.base import ToolContext
from bombe_code.tools.builtin.fs_tools import _edit, _write
from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.widgets.prompt_input import PromptInput


def test_is_code_path_detection():
    assert is_code_path("src/main.py") is True
    assert is_code_path("tests/test_main.py") is True
    assert is_code_path("app/components/Button.tsx") is True
    assert is_code_path("docs/briefings/PRD.md") is False
    assert is_code_path("README.md") is False


def test_is_production_code_path():
    assert is_production_code_path("src/main.py") is True
    assert is_production_code_path("app/api.ts") is True
    assert is_production_code_path("tests/test_main.py") is False
    assert is_production_code_path("docs/architecture/ADR.md") is False


def test_stage_guard_discuss_blocks_code():
    # DISCUSS: escrita em código bloqueada
    allowed, reason = validate_stage_permission(STAGE_DISCUSS, "write", "src/main.py")
    assert allowed is False
    assert "⛔ [BLOQUEIO DE ETAPA: DISCUSS]" in reason

    allowed, reason = validate_stage_permission(STAGE_DISCUSS, "write", "tests/test_x.py")
    assert allowed is False
    assert "⛔ [BLOQUEIO DE ETAPA: DISCUSS]" in reason

    # DISCUSS: leitura permitida
    allowed, _ = validate_stage_permission(STAGE_DISCUSS, "read", "src/main.py")
    assert allowed is True

    # DISCUSS: escrita em docs permitida
    allowed, _ = validate_stage_permission(STAGE_DISCUSS, "write", "docs/briefings/PRD.md")
    assert allowed is True


def test_stage_guard_plan_blocks_production_code():
    # PLAN: produção bloqueada
    allowed, reason = validate_stage_permission(STAGE_PLAN, "write", "src/main.py")
    assert allowed is False
    assert "⛔ [BLOQUEIO DE ETAPA: PLAN]" in reason

    # PLAN: documentação e stories liberadas
    allowed, _ = validate_stage_permission(STAGE_PLAN, "write", "docs/stories/ST-001.md")
    assert allowed is True

    # PLAN: leitura permitida
    allowed, _ = validate_stage_permission(STAGE_PLAN, "read", "src/main.py")
    assert allowed is True


def test_stage_guard_execute_allows_everything():
    allowed, _ = validate_stage_permission(STAGE_EXECUTE, "write", "src/main.py")
    assert allowed is True

    allowed, _ = validate_stage_permission(STAGE_EXECUTE, "write", "tests/test_main.py")
    assert allowed is True

    allowed, _ = validate_stage_permission(STAGE_EXECUTE, "write", "docs/stories/ST-001.md")
    assert allowed is True


def test_stage_guard_validate_restricts_new_modules():
    # VALIDATE: novos módulos de produção bloqueados
    allowed, reason = validate_stage_permission(STAGE_VALIDATE, "write", "src/new_service.py")
    assert allowed is False
    assert "⛔ [BLOQUEIO DE ETAPA: VALIDATE]" in reason

    # VALIDATE: relatórios permitidos
    allowed, _ = validate_stage_permission(
        STAGE_VALIDATE, "write", "docs/reports/validation_report.md"
    )
    assert allowed is True


def test_fs_tools_respects_stage_guard(tmp_path: Path):
    target_code = tmp_path / "src" / "sample.py"
    target_doc = tmp_path / "docs" / "briefing.md"

    # Contexto em DISCUSS
    ctx_discuss = ToolContext(project_dir=str(tmp_path), stage="DISCUSS")

    # Tentativa de escrita em src/ durante DISCUSS deve falhar
    res_code = _write({"path": str(target_code), "content": "print('hello')"}, ctx_discuss)
    assert "⛔ [BLOQUEIO DE ETAPA: DISCUSS]" in res_code
    assert not target_code.exists()

    # Escrita em docs durante DISCUSS deve ter sucesso
    res_doc = _write({"path": str(target_doc), "content": "# Briefing"}, ctx_discuss)
    assert "Arquivo escrito" in res_doc
    assert target_doc.exists()

    # Contexto em EXECUTE
    ctx_execute = ToolContext(project_dir=str(tmp_path), stage="EXECUTE")
    res_exec = _write({"path": str(target_code), "content": "print('hello')"}, ctx_execute)
    assert "Arquivo escrito" in res_exec
    assert target_code.exists()

    # Edição em DISCUSS bloqueada em código
    res_edit_denied = _edit(
        {"path": str(target_code), "old_string": "hello", "new_string": "world"}, ctx_discuss
    )
    assert "⛔ [BLOQUEIO DE ETAPA: DISCUSS]" in res_edit_denied


def test_prompt_input_tab_delegates_to_cycle_stage(monkeypatch: pytest.MonkeyPatch):
    prompt_input = PromptInput()
    mock_app = MagicMock()
    mock_app.action_cycle_stage = MagicMock()
    monkeypatch.setattr(PromptInput, "app", property(lambda self: mock_app))

    # Input vazio: apertar Tab deve chamar action_cycle_stage
    prompt_input.value = ""
    prompt_input.action_complete()
    mock_app.action_cycle_stage.assert_called_once()



def test_tui_app_cycle_stage_and_state_db(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    db.save_wave_state(
        wave_id="ONDA-001",
        state="DISCUSS",
        autonomy_mode="AUTO",
        engineering_mode="tdd-code",
    )

    mock_client = MagicMock()
    mock_client.set_stage = AsyncMock()

    app = BombeTuiApp(client=mock_client, project_dir=str(tmp_path))
    # Deve carregar o estado inicial do banco
    assert app.wave_station == "DISCUSS"

    # Ciclar para PLAN
    app.action_cycle_stage()
    assert app.wave_station == "PLAN"
    loaded = db.load_wave_state()
    assert loaded["state"] == "PLAN"

    # Ciclar para EXECUTE
    app.action_cycle_stage()
    assert app.wave_station == "EXECUTE"
    loaded = db.load_wave_state()
    assert loaded["state"] == "EXECUTE"

    # Ciclar para VALIDATE
    app.action_cycle_stage()
    assert app.wave_station == "VALIDATE"
    loaded = db.load_wave_state()
    assert loaded["state"] == "VALIDATE"

    # Ciclar de volta para DISCUSS
    app.action_cycle_stage()
    assert app.wave_station == "DISCUSS"
    loaded = db.load_wave_state()
    assert loaded["state"] == "DISCUSS"


def test_stage_guard_vibe_mode_allows_everything():
    from bombe_code.permissions.stage_guard import STAGE_VIBE

    # Modo VIBE: qualquer escrita em código, testes ou docs é permitida
    allowed, _ = validate_stage_permission(STAGE_VIBE, "write", "src/main.py")
    assert allowed is True

    allowed, _ = validate_stage_permission(STAGE_VIBE, "write", "tests/test_x.py")
    assert allowed is True

    allowed, _ = validate_stage_permission(STAGE_VIBE, "write", "docs/stories/ST-001.md")
    assert allowed is True


def test_prompt_input_vibe_mode_does_not_cycle_stage(monkeypatch: pytest.MonkeyPatch):
    prompt_input = PromptInput()
    mock_app = MagicMock()
    mock_app.mode = "VIBE"
    mock_app.action_cycle_stage = MagicMock()
    monkeypatch.setattr(PromptInput, "app", property(lambda self: mock_app))

    # No modo VIBE, Tab não cicla etapas
    prompt_input.value = ""
    prompt_input.action_complete()
    mock_app.action_cycle_stage.assert_not_called()


def test_prompt_input_shift_tab_triggers_toggle_vibe_mode(monkeypatch: pytest.MonkeyPatch):
    prompt_input = PromptInput()
    mock_app = MagicMock()
    mock_app.action_toggle_vibe_mode = MagicMock()
    monkeypatch.setattr(PromptInput, "app", property(lambda self: mock_app))

    prompt_input.action_toggle_vibe_mode()
    mock_app.action_toggle_vibe_mode.assert_called_once()


def test_tui_app_toggle_vibe_mode_and_red_badge(tmp_path: Path):
    mock_client = MagicMock()
    mock_client.set_stage = AsyncMock()

    app = BombeTuiApp(client=mock_client, project_dir=str(tmp_path))
    assert app.mode == "TDD"
    assert app.wave_station == "DISCUSS"

    # Alterna para VIBE via Shift+Tab
    app.action_toggle_vibe_mode()
    assert app.mode == "VIBE"
    assert app.wave_station == "VIBE"
    status_text = app._status_text()
    assert "#ff0000" in status_text
    assert "VIBE" in status_text

    # No modo VIBE, tentar ciclar etapa não faz nada
    app.action_cycle_stage()
    assert app.wave_station == "VIBE"

    # Alterna de volta para TDD via Shift+Tab
    app.action_toggle_vibe_mode()
    assert app.mode == "TDD"
    assert app.wave_station == "DISCUSS"
    status_tdd = app._status_text()
    assert "TDD" in status_tdd


def test_orchestrator_start_wave_incomplete_warning_and_force(tmp_path: Path):
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=str(tmp_path))
    # Inicia ONDA-001
    res1 = orch.start_wave("ONDA-001", force=True)
    assert res1["success"] is True

    # Tenta iniciar ONDA-002 sem force enquanto ONDA-001 está em DISCUSS (incompleta)
    res2 = orch.start_wave("ONDA-002", force=False)
    assert res2["success"] is False
    assert "ainda está em andamento" in res2["message"]

    # Com --force (force=True), deve permitir sobrescrever e iniciar
    res3 = orch.start_wave("ONDA-002", force=True)
    assert res3["success"] is True
    assert res3["wave_id"] == "ONDA-002"

