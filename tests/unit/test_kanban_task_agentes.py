"""KANBAN DE AGENTES — manda em tudo (fonte única de verdade).

- A task de agente NASCE NO KANBAN (designada, ordenada) ANTES de qualquer
  agente acordar. Sem ordem no kanban, agente nem acorda.
- Colunas: BACKLOG → AGUARDANDO DEV → EM DEV → DEV DONE → DONE DEFINITIVO.
- BLOCKED acontece NA coluna em que está e fica ali, tipado; prioridade
  Andon: primeiro resolvo blocked antes de qualquer outra coisa.
- Resume: DEV DONE/DONE DEFINITIVO são IGNORADOS (revalidar é papel do code
  review final da story); pega BLOCKED ou o próximo AGUARDANDO DEV.
- Code review achou algo do agente X → os cards DEV DONE de X voltam para o
  BURN. Story 100% aprovada → DONE DEFINITIVO (nunca mais volta; mexer
  depois = CHANGE = novo card).
"""

from pathlib import Path

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.pbb import AtomicTask, AtomicTaskType
from bombe_code.turing.progress import BUS
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    (tmp_path / "app.py").write_text("def app() -> str:\n    return 'ok'\n", encoding="utf-8")
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-004", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.kanban.add_card(
        story_id="ST-001", wave_id="ONDA-004", title="Story 1", agent="@valim", status="IN_PROGRESS"
    )
    return tmp_path, orch


def _tarefas():
    return [
        AtomicTask(
            id="T1",
            story_id="ST-001",
            task_type=AtomicTaskType.FRONTEND_UI,
            title="Tela",
            description="tela",
            responsible_agent="@ada",
        ),
        AtomicTask(
            id="T2",
            story_id="ST-001",
            task_type=AtomicTaskType.BACKEND_TDD,
            title="Rota",
            description="rota",
            responsible_agent="@valim",
        ),
        AtomicTask(
            id="T3",
            story_id="ST-001",
            task_type=AtomicTaskType.DATABASE,
            title="Schema",
            description="schema",
            responsible_agent="@codd",
        ),
    ]


def test_task_nasce_no_kanban_designada_e_ordenada(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())

    cartoes = orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    assert [c["task_id"] for c in cartoes] == ["T1", "T2", "T3"], "ordem de execução"
    assert [c["agent_role"] for c in cartoes] == ["@ada", "@valim", "@codd"], "designação"
    assert all(c["kanban_status"] == "AGUARDANDO_DEV" for c in cartoes), (
        "nasce BACKLOG e vai para AGUARDANDO DEV quando pronta"
    )


def test_preparar_nao_toca_cards_em_andamento(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "EM_DEV")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T3", "DEV_DONE")

    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())  # re-chamada (resume)

    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados == {"T1": "AGUARDANDO_DEV", "T2": "EM_DEV", "T3": "DEV_DONE"}


def test_fila_blocked_primeiro_e_feitos_ignorados(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "BLOCKED", "INTERNAL_SCALE")

    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001", _tarefas())
    finally:
        BUS.publish = publicar_original

    assert [t.id for t in fila] == ["T2", "T3"], "blocked primeiro (Andon), depois a fila"
    assert any("🚩 ANDON" in t and "T2" in t for t in publicados)
    assert any("ignoro no resume" in t and "T1" in t for t in publicados)


def test_transicao_binaria_dev_done_ou_blocked(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # deu certo
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "EM_DEV")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    # não deu certo — blocked tipado, fica NA coluna (EM_DEV não existia mais)
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "EM_DEV")
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T2", "BLOCKED", "HUMAN_SCALE")

    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    tipos = {
        c["task_id"]: c["block_tipo"] for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados["T1"] == "DEV_DONE"
    assert estados["T2"] == "BLOCKED"
    assert tipos["T2"] == "HUMAN_SCALE"


def test_achado_devolve_cards_do_agente_para_burn(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    for tid in ("T1", "T2", "T3"):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "EM_DEV")
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "DEV_DONE")

    voltaram = orch._garcom_devolver_cards_para_burn("ONDA-004", "ST-001", "@codd")

    assert voltaram == 1
    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert estados["T3"] == "AGUARDANDO_DEV", "card do banco voltou para o BURN"
    assert estados["T1"] == "DEV_DONE" and estados["T2"] == "DEV_DONE"


def test_story_aprovada_vira_done_definitivo(project_env):
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    for tid in ("T1", "T2", "T3"):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "DEV_DONE")

    # Story 100% aprovada → DONE DEFINITIVO (nunca mais volta)
    for tid in ("T1", "T2", "T3"):
        orch.db.mover_task_kanban("ONDA-004", "ST-001", tid, "DONE_DEFINITIVO")

    estados = {
        c["task_id"]: c["kanban_status"]
        for c in orch.db.carregar_tasks_kanban("ONDA-004", "ST-001")
    }
    assert all(s == "DONE_DEFINITIVO" for s in estados.values())
    # _garcom_devolver_cards_para_burn NÃO mexe em DONE DEFINITIVO
    assert orch._garcom_devolver_cards_para_burn("ONDA-004", "ST-001", "@codd") == 0


def test_review_nao_pula_fila_por_blocked_precedencia(project_env):
    """PRECEDÊNCIA > PRIORIDADE: review bloqueado NÃO é tratado antes das
    tasks pendentes — a regra que libera o review (todas as tasks DEV DONE)
    é o que define QUANDO ele pode ser queimado."""
    _tmp_path, orch = project_env
    orch._garcom_preparar_tasks("ONDA-004", "ST-001", _tarefas())
    # T1 pronta; T2 e T3 ainda na fila; review bloqueado tentando furar
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "T1", "DEV_DONE")
    orch.db.criar_task_kanban(
        "ONDA-004", "ST-001", "REVIEW-TECH", "Code Review da story", "@unclebob", 90
    )
    orch.db.mover_task_kanban("ONDA-004", "ST-001", "REVIEW-TECH", "BLOCKED", "INTERNAL_SCALE")

    publicados: list[str] = []
    publicar_original = BUS.publish

    def capturar(etype, **kw):
        publicados.append(kw.get("text", ""))
        return publicar_original(etype, **kw)

    BUS.publish = capturar
    try:
        fila, _ = orch._garcom_carregar_fila("ONDA-004", "ST-001", _tarefas())
    finally:
        BUS.publish = publicar_original

    # A fila é das TASKS: T2 e T3 (blocked T2? não — T2/T3 aguardando; T1 feito)
    ids = [t.id for t in fila]
    assert "T2" in ids and "T3" in ids, "as tasks pendentes são queimadas primeiro"
    # O aviso de precedência explica por que o review não sobe
    assert any("PRECEDÊNCIA" in t and "AGUARDA" in t for t in publicados)
