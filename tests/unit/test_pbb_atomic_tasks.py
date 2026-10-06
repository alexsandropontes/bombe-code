"""Testes TDD para a Story ST-036: Decomposição PBB — Modelo de Dados de AtomicTask."""

from bombe_code.turing.pbb import (
    AtomicTaskType,
    PBBDecomposer,
)


def test_atomic_task_types_exist():
    assert AtomicTaskType.DATABASE.value == "DATABASE"
    assert AtomicTaskType.CONTRACT.value == "CONTRACT"
    assert AtomicTaskType.BACKEND_TDD.value == "BACKEND_TDD"
    assert AtomicTaskType.FRONTEND_UI.value == "FRONTEND_UI"
    assert AtomicTaskType.E2E_INTEGRATION.value == "E2E_INTEGRATION"


def test_pbb_decomposes_fullstack_story_into_ordered_atomic_tasks():
    tasks = PBBDecomposer.decompose_story(
        story_id="ST-001",
        story_title="Quiz Financeiro com Persistência",
        requires_db=True,
        requires_frontend=True,
    )

    assert len(tasks) == 5
    assert [t.task_type for t in tasks] == [
        AtomicTaskType.DATABASE,
        AtomicTaskType.CONTRACT,
        AtomicTaskType.BACKEND_TDD,
        AtomicTaskType.FRONTEND_UI,
        AtomicTaskType.E2E_INTEGRATION,
    ]

    # Valida IDs ordenados
    assert tasks[0].id == "ST-001-T1"
    assert tasks[1].id == "ST-001-T2"
    assert tasks[2].id == "ST-001-T3"
    assert tasks[3].id == "ST-001-T4"
    assert tasks[4].id == "ST-001-T5"

    # Valida agentes especialistas responsáveis
    assert tasks[0].responsible_agent == "@codd"
    assert tasks[1].responsible_agent == "@ieru"
    assert tasks[2].responsible_agent == "@aniche"
    assert tasks[3].responsible_agent == "@ada"
    assert tasks[4].responsible_agent == "@fowler"


def test_backend_task_depends_on_database_and_contract():
    tasks = PBBDecomposer.decompose_story(
        story_id="ST-002",
        story_title="Motor de Cálculo de Perfil",
        requires_db=True,
        requires_frontend=True,
    )

    backend_task = next(t for t in tasks if t.task_type == AtomicTaskType.BACKEND_TDD)
    assert "ST-002-T1" in backend_task.depends_on
    assert "ST-002-T2" in backend_task.depends_on


def test_backend_only_story_omits_frontend_and_e2e_ui():
    tasks = PBBDecomposer.decompose_story(
        story_id="ST-003",
        story_title="Job de Reconciliação",
        requires_db=True,
        requires_frontend=False,
    )

    types = [t.task_type for t in tasks]
    assert AtomicTaskType.DATABASE in types
    assert AtomicTaskType.BACKEND_TDD in types
    assert AtomicTaskType.FRONTEND_UI not in types
