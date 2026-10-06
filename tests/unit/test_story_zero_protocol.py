"""Testes unitários e de integração para o Protocolo da STORY-0 (ST-043, ST-044, ST-045)."""

from pathlib import Path
from unittest.mock import MagicMock

from bombe_code.starters.decision import load_starter_decision, save_starter_decision
from bombe_code.starters.matcher import TemplateMatcher
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.pbb import AtomicTask, AtomicTaskType, PBBDecomposer
from bombe_code.turing.upstream_gates import ArchitectureGate


def test_starter_decision_persistence_and_architecture_gate(tmp_path: Path):
    matcher = TemplateMatcher()
    match_res = matcher.match(
        product_type="saas",
        backend_language="python",
        frontend_stack="react",
        multitenancy="mono",
    )
    assert match_res.matched is True

    # 1. Salva a decisão em docs/arquitetura/TEMPLATE_STARTER.md
    dec_file = save_starter_decision(tmp_path, match_res, adr_id="ADR-001")
    assert dec_file.is_file()

    # 2. Carrega a decisão do disco
    loaded = load_starter_decision(tmp_path)
    assert loaded is not None
    assert loaded["starter_id"] == "python-mono"
    assert loaded["manifest"]["multitenancy_type"] == "mono"

    # 3. Testa ArchitectureGate:
    gate = ArchitectureGate()

    # ADR sem menção ao starter escolhido -> reprovado
    bad_adr = """# ADR-001: Decisões Arquiteturais
Stack: Python e React. Usaremos tabela clientes_tb customizada."""
    eval_bad = gate.evaluate(bad_adr, project_dir=tmp_path)
    assert eval_bad["approved"] is False
    assert any("Starter selecionado" in s for s in eval_bad["missing_sections"])

    # ADR com menção ao starter selecionado -> aprovado
    good_adr = """# ADR-001: Decisões Arquiteturais
Stack: Python e React.
Adotado o Starter oficial python-mono (blueprint python-react-fullstack).
Modelagem alinhada com as entidades padrão do template."""
    eval_good = gate.evaluate(good_adr, project_dir=tmp_path)
    assert eval_good["approved"] is True


def test_pbb_caroli_mandatory_story_zero(tmp_path: Path):
    # Sem starter decision: backlog normal
    stories = [
        {
            "id": "ST-001",
            "title": "Cadastro de Usuários",
            "requires_db": True,
            "requires_frontend": True,
        },
    ]
    tasks_normal = PBBDecomposer.decompose_backlog(stories, project_dir=tmp_path)
    task_ids_normal = [t.id for t in tasks_normal]
    assert "STORY-0-T1" not in task_ids_normal
    assert "ST-001-T1" in task_ids_normal

    # Com starter decision aprovado: criação mandatória da STORY-0
    matcher = TemplateMatcher()
    match_res = matcher.match("saas", "python", "react")
    save_starter_decision(tmp_path, match_res)

    tasks_with_s0 = PBBDecomposer.decompose_backlog(stories, project_dir=tmp_path)
    task_ids_with_s0 = [t.id for t in tasks_with_s0]

    # STORY-0 é a primeira história do backlog
    assert "STORY-0-T1" in task_ids_with_s0
    assert "STORY-0-T2" in task_ids_with_s0
    assert tasks_with_s0[0].id == "STORY-0-T1"
    assert tasks_with_s0[0].task_type == AtomicTaskType.FOUNDATION
    assert tasks_with_s0[0].responsible_agent == "@unclebob"

    # Story-1 (ST-001-T1) obrigatoriamente depende da conclusão do sanity check da STORY-0
    st1_task = next(t for t in tasks_with_s0 if t.id == "ST-001-T1")
    assert "STORY-0-T2" in st1_task.depends_on


def test_downstream_execution_story_zero(tmp_path: Path):
    matcher = TemplateMatcher()
    match_res = matcher.match("saas", "python", "react", "mono")
    save_starter_decision(tmp_path, match_res)

    orch = WaveOrchestrator(project_dir=tmp_path)
    orch.kanban.add_card(
        story_id="STORY-0", wave_id="ONDA-001", title="Fundação Starter", agent="@unclebob"
    )

    s0_tasks = PBBDecomposer.create_story_zero("python-mono", match_res.to_dict())

    # Mock do runner para STORY-0-T2 (sanity check)
    def mock_runner_factory(agent_handle: str):
        runner = MagicMock()
        res = MagicMock()
        res.success = True
        res.output = "Sanity check 100% verde: testes de fundação validados."
        res.is_blocked = False
        res.input_tokens = 10
        res.output_tokens = 20
        res.total_tokens = 30
        res.cost = 0.001
        res.duration_seconds = 0.2
        runner.run.return_value = res
        return runner

    orch._get_runner = mock_runner_factory

    exec_res = orch.run_story_tasks("STORY-0", s0_tasks)

    assert exec_res["success"] is True
    # Scaffolding determinístico gravou os arquivos no disco
    assert (tmp_path / ".bombeconfig").is_file()
    assert (tmp_path / "src" / "backend" / "main.py").is_file()
    assert (tmp_path / "src" / "frontend" / "package.json").is_file()


def test_downstream_execution_story_zero_fallback_recovery(tmp_path: Path):
    orch = WaveOrchestrator(project_dir=tmp_path)
    # Task com starter inexistente para forçar fallback
    task_fail = AtomicTask(
        id="STORY-0-T1",
        story_id="STORY-0",
        task_type=AtomicTaskType.FOUNDATION,
        title="Scaffolding Starter Inexistente 'starter-com-defeito'",
        description="Scaffold com defeito",
        responsible_agent="@unclebob",
    )

    # Runner do Tech Lead recupera o problema
    def mock_runner_factory(agent_handle: str):
        runner = MagicMock()
        res = MagicMock()
        res.success = True
        res.output = "Tech Lead corrigiu dependências da fundação."
        runner.run.return_value = res
        return runner

    orch._get_runner = mock_runner_factory
    orch.kanban.add_card("STORY-0", "ONDA-001", "Fundação", "@unclebob")

    exec_res = orch.run_story_tasks("STORY-0", [task_fail])
    assert exec_res["success"] is True
    assert "Recuperado pelo Tech Lead" in task_fail.output
