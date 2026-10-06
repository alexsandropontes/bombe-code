"""Testes determinísticos para o WaveOrchestrator (ST-015).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage, WaveState


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    return tmp_path, db


def test_wave_orchestrator_init_and_start(project_env):
    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)

    res = orchestrator.start_wave("ONDA-004")
    assert res["success"] is True
    assert res["wave_id"] == "ONDA-004"
    assert res["stage"] == TuringStage.DISCUSS.value

    # Confirma que persistiu no SQLite
    saved = db.load_wave_state()
    assert saved is not None
    assert saved["wave_id"] == "ONDA-004"
    assert saved["state"] == WaveState.DISCUSS.value


def test_wave_orchestrator_get_status(project_env):
    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orchestrator.start_wave("ONDA-004")

    status = orchestrator.get_status()
    assert status["wave_id"] == "ONDA-004"
    assert status["stage"] == TuringStage.DISCUSS.value
    assert "autonomy_mode" in status
    assert "engineering_mode" in status
    assert "tasks_summary" in status


def test_wave_orchestrator_transitions(project_env):
    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orchestrator.start_wave("ONDA-004")

    # Transição DISCUSS -> PLAN
    assert orchestrator.transition_to(TuringStage.PLAN) is True
    assert orchestrator.get_status()["stage"] == TuringStage.PLAN.value

    # Transição PLAN -> EXECUTE
    assert orchestrator.transition_to(TuringStage.EXECUTE) is True
    assert orchestrator.get_status()["stage"] == TuringStage.EXECUTE.value

    # Transição EXECUTE -> VALIDATE
    assert orchestrator.transition_to(TuringStage.VALIDATE) is True
    assert orchestrator.get_status()["stage"] == TuringStage.VALIDATE.value

    # Transição VALIDATE -> COMPLETED
    assert orchestrator.transition_to(TuringStage.COMPLETED) is True
    assert orchestrator.get_status()["stage"] == TuringStage.COMPLETED.value


def test_wave_orchestrator_invalid_transition(project_env):
    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orchestrator.start_wave("ONDA-004")

    # Pular de DISCUSS direto para VALIDATE deve ser recusado
    assert orchestrator.transition_to(TuringStage.VALIDATE) is False
    assert orchestrator.get_status()["stage"] == TuringStage.DISCUSS.value


def test_wave_orchestrator_run_discuss_and_plan(project_env):
    from unittest.mock import MagicMock

    tmp_path, db = project_env

    mock_factory = MagicMock()
    mock_agent = MagicMock()

    def side_effect_run(prompt, context=None):
        m = MagicMock()
        m.data = (
            "Artefato gerado com sucesso e aprovado.\n\n"
            "## Viabilidade Técnica\nViável com baixo risco\n"
            "## Riscos\nRiscos mapeados e mitigados\n\n"
            "# PRD - Sistema\n"
            "## Visão Geral\nVisão geral do sistema\n"
            "## Problema\nProblema a resolver\n"
            "## Personas\nUsuário final\n"
            "## Critérios RICE\nRICE aprovado\n"
            "## MVP Operacional\nEntregável v1\n\n"
            "## Entry Points\nHome\n"
            "## Fluxo de Navegação\nFluxo 1\n"
            "## Telas\nDashboard\n\n"
            "## Decisões Arquiteturais\nClean Arch\n"
            "## Stack\nPython, FastAPI\n\n"
            "## Schema\nCREATE TABLE lead (id UUID);\n"
            "## Constraints\nPRIMARY KEY (id);\n\n"
            "# STORY ST-001: Implementação\n"
            "> **Status:** READY\n"
            "> **Blocked:** false\n"
            "## INVEST\nIndependente\n"
            "## Critérios de Aceite\nCritérios claros\n"
            "### Cenários BDD\n- Dado um usuário\n- Quando clicar\n- Então funciona\n"
        )
        return m

    mock_agent.run.side_effect = side_effect_run
    mock_factory.create_agent.return_value = mock_agent

    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orchestrator.start_wave("ONDA-004")

    # 1. Executa DISCUSS
    disc_res = orchestrator.run_discuss(topic="Novo Sistema de Pagamentos")
    assert disc_res["success"] is True
    assert disc_res["stage"] == TuringStage.DISCUSS.value
    assert len(disc_res["results"]) == 2  # @meira e @grace

    # 2. Transita e executa PLAN
    plan_res = orchestrator.run_plan()
    assert plan_res["success"] is True
    assert plan_res["stage"] == TuringStage.PLAN.value
    assert len(plan_res["results"]) == 4  # @alan, @ieru, @codd, @caroli


def test_wave_orchestrator_run_cycle_atomic(project_env):
    from unittest.mock import MagicMock

    tmp_path, db = project_env

    # Cria story pré-requisito no disco
    stories_dir = tmp_path / "docs" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "ST-015.md").write_text(
        "# STORY ST-015\n## INVEST\n## Critérios de Aceite\n### Cenários BDD\n- Dado X\n- Quando Y\n- Então Z\n"
    )

    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()
    mock_res.data = "TDD concluído e Selo do Cycle concedido e aprovado."
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orchestrator.start_wave("ONDA-004")
    orchestrator.transition_to(TuringStage.PLAN)
    orchestrator.transition_to(TuringStage.EXECUTE)

    # Executa ciclo atômico de uma story e para
    res = orchestrator.run_cycle("ST-015")
    assert res["success"] is True
    assert res["story_id"] == "ST-015"
    assert res["paused"] is True
    assert "Aguardando próximo comando" in res["message"]


def test_wave_orchestrator_run_execute_batch_and_manual_pause(project_env):
    from unittest.mock import MagicMock

    tmp_path, db = project_env

    # Cria stories pré-requisito no disco
    stories_dir = tmp_path / "docs" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    for sid in ["ST-001", "ST-002", "ST-003"]:
        (stories_dir / f"{sid}.md").write_text(
            f"# STORY {sid}\n## INVEST\n## Critérios de Aceite\n### Cenários BDD\n- Dado X\n- Quando Y\n- Então Z\n"
        )

    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()
    mock_res.data = "Story finalizada com sucesso e aprovado."
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    # 1. Modo AUTO: executa todas as stories
    orch_auto = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch_auto.start_wave("ONDA-004", autonomy_mode="AUTO")
    orch_auto.transition_to(TuringStage.PLAN)
    orch_auto.transition_to(TuringStage.EXECUTE)

    res_auto = orch_auto.run_execute(stories=["ST-001", "ST-002", "ST-003"])
    assert res_auto["success"] is True
    assert res_auto["total_executed"] == 3
    assert res_auto["completed_stories"] == ["ST-001", "ST-002", "ST-003"]

    # 2. Modo MANUAL: pausa e pede confirmação
    orch_manual = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch_manual.start_wave("ONDA-004", autonomy_mode="MANUAL")
    orch_manual.transition_to(TuringStage.PLAN)
    orch_manual.transition_to(TuringStage.EXECUTE)

    # Simula usuário aprovando ST-001, mas pausando em ST-002
    def confirm_cb(story: str) -> bool:
        return story == "ST-001"

    res_manual = orch_manual.run_execute(
        stories=["ST-001", "ST-002", "ST-003"],
        confirm_callback=confirm_cb,
    )
    assert res_manual["paused_by_user"] is True
    assert res_manual["completed_stories"] == ["ST-001", "ST-002"]


def test_wave_orchestrator_validate_and_end(project_env):
    from unittest.mock import MagicMock

    tmp_path, db = project_env

    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()
    mock_res.data = "Auditoria realizada e Selo Final Homologado."
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orchestrator.start_wave("ONDA-004")
    orchestrator.transition_to(TuringStage.PLAN)
    orchestrator.transition_to(TuringStage.EXECUTE)
    orchestrator.transition_to(TuringStage.VALIDATE)

    val_res = orchestrator.run_validate()
    assert val_res["success"] is True
    assert val_res["stage"] == TuringStage.VALIDATE.value

    end_res = orchestrator.end_wave()
    assert end_res["success"] is True
    assert end_res["stage"] == TuringStage.COMPLETED.value
    assert orchestrator.get_status()["stage"] == TuringStage.COMPLETED.value


def test_wave_orchestrator_meira_viability_persistence_and_approval(project_env):
    from unittest.mock import MagicMock

    from bombe_code.agents.runner import AgentExecutionResult

    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orchestrator.start_wave("ONDA-005")

    # Mock runner_meira
    mock_runner = MagicMock()
    mock_runner.run.return_value = AgentExecutionResult(
        agent_handle="@meira",
        success=True,
        output="## Análise de Viabilidade\nStatus: APROVADO\nVeredito: PROSSEGUIR com o MVP.",
    )
    # Mock runner_grace as well to prevent failing prerequisites or execution
    mock_runner_grace = MagicMock()
    mock_runner_grace.run.return_value = AgentExecutionResult(
        agent_handle="@grace",
        success=True,
        output="## PRD Oficial\nVisão do Produto e Personas.\nStatus: APROVADO",
    )

    def mock_get_runner(handle: str):
        if handle == "@meira":
            return mock_runner
        return mock_runner_grace

    orchestrator._get_runner = mock_get_runner

    orchestrator.run_discuss("Sistema de Pagamentos")
    viab_file = tmp_path / "docs" / "briefings" / "VIABILITY.md"
    assert viab_file.exists()
    assert "Status: APROVADO" in viab_file.read_text(encoding="utf-8")


def test_wave_orchestrator_caroli_dor_disk_inspection(project_env):
    from unittest.mock import MagicMock

    from bombe_code.agents.runner import AgentExecutionResult

    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orchestrator.start_wave("ONDA-006")
    orchestrator.transition_to(TuringStage.PLAN)

    # Pré-cria os artefatos de pré-requisitos para os arquitetos (> 50 bytes)
    (tmp_path / "docs" / "briefings").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "briefings" / "PRD.md").write_text(
        "# PRD Oficial - Onboarding\n## Visão do Produto\nPersonas bem definidas\n## Escopo do MVP detalhado com requisitos funcionais.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "architecture" / "journey.md").write_text(
        "# Journey Completo\n## Entry Points\nEntrada via web mobile.\n## Fluxo de Navegação\nPasso a passo 1-10.\n## Telas\nTelas responsivas.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "architecture" / "SYSTEM_ARCHITECTURE.md").write_text(
        "# Arquitetura do Sistema\n## Decisões Arquiteturais\nHexagonal puro e SPA client-side.\n## Stack\nPython e React com Vite.",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "architecture" / "db.md").write_text(
        "# Database Schema\n## Tabelas e Coleções\nArmazenamento em localStorage sem backend.",
        encoding="utf-8",
    )

    # Pré-cria a story com INVEST e BDD no diretório de backlog (como @caroli faz via tools)
    backlog_dir = tmp_path / "docs" / "backlog" / "stories"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    story_body = (
        "# STORY ST-001: Implementação\n"
        "> **Status:** READY\n"
        "## INVEST\n"
        "## Critérios de Aceite\n"
        "### Cenários BDD\n"
        "- Dado um usuário\n- Quando solicitar\n- Então recebe resposta\n"
    )
    (backlog_dir / "ST-001.md").write_text(story_body, encoding="utf-8")

    # Mock runners retornando saídas válidas
    mock_runner_alan = MagicMock()
    mock_runner_alan.run.return_value = AgentExecutionResult(
        agent_handle="@alan",
        success=True,
        output="## Entry Points\n## Fluxo de Navegação\n## Telas",
    )
    mock_runner_ieru = MagicMock()
    mock_runner_ieru.run.return_value = AgentExecutionResult(
        agent_handle="@ieru", success=True, output="## Decisões Arquiteturais\n## Stack"
    )
    mock_runner_codd = MagicMock()
    mock_runner_codd.run.return_value = AgentExecutionResult(
        agent_handle="@codd",
        success=True,
        output="## Schema e Tabelas\n## Constraints e Integridade\nCampos e chaves definidos.",
    )
    mock_runner_caroli = MagicMock()
    mock_runner_caroli.run.return_value = AgentExecutionResult(
        agent_handle="@caroli",
        success=True,
        output="Persistidas as stories em docs/backlog/stories/ conforme solicitado.",
    )

    def mock_get_runner(handle: str):
        mapping = {
            "@alan": mock_runner_alan,
            "@ieru": mock_runner_ieru,
            "@codd": mock_runner_codd,
            "@caroli": mock_runner_caroli,
        }
        return mapping.get(handle)

    orchestrator._get_runner = mock_get_runner

    res = orchestrator.run_plan()
    assert res["success"] is True
    wave_story = tmp_path / "docs" / "waves" / "ONDA-006" / "stories" / "ST-001.md"
    assert wave_story.exists()
    assert "INVEST" in wave_story.read_text(encoding="utf-8")


def test_wave_orchestrator_run_execute_auto_discovers_cards_and_skips_done(project_env):
    from unittest.mock import MagicMock

    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orchestrator.start_wave("ONDA-007")
    orchestrator.transition_to(TuringStage.PLAN)
    orchestrator.transition_to(TuringStage.EXECUTE)

    # Cadastra dois cards: ST-001 já DEV_DONE e ST-002 READY
    orchestrator.kanban.add_card("ST-001", "ONDA-007", "Title 1", "@valim", status="DEV_DONE")
    orchestrator.kanban.add_card("ST-002", "ONDA-007", "Title 2", "@valim", status="READY")

    # Mock run_cycle para retornar sucesso quando chamado para ST-002
    orchestrator.run_cycle = MagicMock(return_value={"success": True})

    # Chama run_execute sem passar lista de stories (deve auto-descobrir e pular ST-001)
    res = orchestrator.run_execute()
    assert res["success"] is True
    assert res["completed_stories"] == ["ST-001", "ST-002"]
    # Garante que run_cycle só foi chamado para ST-002
    orchestrator.run_cycle.assert_called_once_with(story_id="ST-002")

    # Chama com force=True para forçar re-execução de todas as stories
    orchestrator.run_cycle.reset_mock()
    res_forced = orchestrator.run_execute(force=True)
    assert res_forced["success"] is True
    assert orchestrator.run_cycle.call_count == 2


def test_start_wave_greenfield_and_zero_tasks_transition(project_env):
    tmp_path, db = project_env
    orchestrator = WaveOrchestrator(project_dir=str(tmp_path), db=db)

    # 1. Simula Greenfield: estado salvo como ONDA-000 em DISCOVERY
    db.save_wave_state(
        wave_id="ONDA-000",
        state="DISCOVERY",
        autonomy_mode="AUTO",
        engineering_mode="tdd-code",
    )

    # 2. Iniciar ONDA-001 sem tarefas pendentes deve suceder (transição natural de discovery para delivery)
    res = orchestrator.start_wave("ONDA-001")
    assert res["success"] is True
    assert res["wave_id"] == "ONDA-001"
    assert orchestrator.state_machine.wave_id == "ONDA-001"
