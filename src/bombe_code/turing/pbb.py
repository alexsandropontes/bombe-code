"""Módulo de Decomposição PBB (Product Backlog Building) e Tarefas Atômicas (ST-036).

Decompõe ai-stories em tarefas atômicas estritas (Single Responsibility Principle)
para execução sequencial no ciclo TDD por agentes especialistas:
1. DATABASE (@codd)
2. CONTRACT (@ieru)
3. BACKEND_TDD (@aniche / @valim)
4. FRONTEND_UI (@ada)
5. E2E_INTEGRATION (@fowler)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class AtomicTaskType(str, Enum):
    """Tipos canônicos de tarefas técnicas atômicas de uma Story."""

    FOUNDATION = "FOUNDATION"  # Scaffolding determinístico de starter e baseline
    DATABASE = "DATABASE"  # Schema, migrations, índices e persistência
    CONTRACT = "CONTRACT"  # Schemas de validação Zod/Pydantic, tipos e DTOs
    BACKEND_TDD = "BACKEND_TDD"  # Rota, regras de negócio e testes de unidade/integração
    FRONTEND_UI = "FRONTEND_UI"  # Componente de interface, estado e validação inline
    E2E_INTEGRATION = "E2E_INTEGRATION"  # Testes ponta a ponta (ex: Playwright)


@dataclass
class AtomicTask:
    """Tarefa técnica atômica de caráter estrito e isolado."""

    id: str
    story_id: str
    task_type: AtomicTaskType
    title: str
    description: str
    responsible_agent: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "PENDING"
    output: str | None = None
    error: str | None = None


class PBBDecomposer:
    """Motor de decomposição de stories em tarefas atômicas conforme metodologia PBB."""

    DEFAULT_AGENTS: ClassVar[dict[AtomicTaskType, str]] = {
        AtomicTaskType.FOUNDATION: "@unclebob",
        AtomicTaskType.DATABASE: "@codd",
        AtomicTaskType.CONTRACT: "@ieru",
        AtomicTaskType.BACKEND_TDD: "@aniche",
        AtomicTaskType.FRONTEND_UI: "@ada",
        AtomicTaskType.E2E_INTEGRATION: "@fowler",
    }

    @classmethod
    def decompose_story(
        cls,
        story_id: str,
        story_title: str,
        requires_db: bool = True,
        requires_frontend: bool = True,
    ) -> list[AtomicTask]:
        """Fatia uma story em tarefas atômicas sequenciais respeitando dependências."""
        tasks: list[AtomicTask] = []
        task_idx = 1
        db_task_id = None
        contract_task_id = None
        backend_task_id = None
        frontend_task_id = None

        # 1. DATABASE
        if requires_db:
            db_task_id = f"{story_id}-T{task_idx}"
            tasks.append(
                AtomicTask(
                    id=db_task_id,
                    story_id=story_id,
                    task_type=AtomicTaskType.DATABASE,
                    title=f"Schema e Migrations — {story_title}",
                    description=f"Modelagem física, migration transacional e constraints para {story_title}.",
                    responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.DATABASE],
                    depends_on=[],
                )
            )
            task_idx += 1

        # 2. CONTRACT (Tipos e Schemas Compartilhados)
        contract_task_id = f"{story_id}-T{task_idx}"
        contract_deps = [db_task_id] if db_task_id else []
        tasks.append(
            AtomicTask(
                id=contract_task_id,
                story_id=story_id,
                task_type=AtomicTaskType.CONTRACT,
                title=f"Contratos de Dados e Tipos — {story_title}",
                description=f"Definição de DTOs e esquemas compartilhados (Zod/Pydantic) para {story_title}.",
                responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.CONTRACT],
                depends_on=contract_deps,
            )
        )
        task_idx += 1

        # 3. BACKEND TDD
        backend_task_id = f"{story_id}-T{task_idx}"
        backend_deps = [d for d in (db_task_id, contract_task_id) if d]
        tasks.append(
            AtomicTask(
                id=backend_task_id,
                story_id=story_id,
                task_type=AtomicTaskType.BACKEND_TDD,
                title=f"Lógica de Domínio e API — {story_title}",
                description=f"Implementação guiada por testes (TDD Red-Green-Refactor) dos endpoints de {story_title}.",
                responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.BACKEND_TDD],
                depends_on=backend_deps,
            )
        )
        task_idx += 1

        # 4. FRONTEND UI
        if requires_frontend:
            frontend_task_id = f"{story_id}-T{task_idx}"
            tasks.append(
                AtomicTask(
                    id=frontend_task_id,
                    story_id=story_id,
                    task_type=AtomicTaskType.FRONTEND_UI,
                    title=f"Interface e Acessibilidade — {story_title}",
                    description=f"Componentes de UI, estados de tela e validações inline para {story_title}.",
                    responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.FRONTEND_UI],
                    depends_on=[backend_task_id, contract_task_id],
                )
            )
            task_idx += 1

            # 5. E2E INTEGRATION
            e2e_task_id = f"{story_id}-T{task_idx}"
            tasks.append(
                AtomicTask(
                    id=e2e_task_id,
                    story_id=story_id,
                    task_type=AtomicTaskType.E2E_INTEGRATION,
                    title=f"Testes Ponta a Ponta E2E — {story_title}",
                    description=f"Validação da jornada do usuário em navegador real (Playwright) para {story_title}.",
                    responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.E2E_INTEGRATION],
                    depends_on=[frontend_task_id, backend_task_id],
                )
            )

        return tasks

    @classmethod
    def create_story_zero(
        cls,
        starter_id: str,
        starter_info: dict[str, Any] | None = None,
    ) -> list[AtomicTask]:
        """Gera as tarefas atômicas mandatórias da STORY-0 para o Tech Lead (@unclebob)."""
        info = starter_info or {}
        blueprint = info.get("blueprint") or starter_id

        task_1 = AtomicTask(
            id="STORY-0-T1",
            story_id="STORY-0",
            task_type=AtomicTaskType.FOUNDATION,
            title=f"Scaffolding Determinístico de Fundação via Starter '{starter_id}'",
            description=(
                f"Aplicação do starter '{starter_id}' (blueprint '{blueprint}'). "
                "Copia estrutura padrão, inicializa .bombeconfig e configura dependências da stack."
            ),
            responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.FOUNDATION],
            depends_on=[],
        )

        task_2 = AtomicTask(
            id="STORY-0-T2",
            story_id="STORY-0",
            task_type=AtomicTaskType.E2E_INTEGRATION,
            title=f"Sanity Check e Baseline de Testes de Fundação ({starter_id})",
            description=(
                "Execução e validação da suíte de testes de fundação da stack recém-scaffoldada. "
                "Garante baseline 100% verde antes de liberar para o time TDD nas próximas stories. "
                "Em caso de falha de ambiente/template, o Tech Lead (@unclebob) elimina o erro."
            ),
            responsible_agent=cls.DEFAULT_AGENTS[AtomicTaskType.FOUNDATION],
            depends_on=["STORY-0-T1"],
        )

        return [task_1, task_2]

    @classmethod
    def decompose_backlog(
        cls,
        stories: list[dict[str, Any]],
        project_dir: Any = None,
    ) -> list[AtomicTask]:
        """Decompõe o backlog completo inserindo obrigatoriamente a STORY-0 se houver starter aprovado."""
        from ..starters.decision import load_starter_decision

        all_tasks: list[AtomicTask] = []
        story_zero_done_dep: str | None = None

        if project_dir:
            starter_data = load_starter_decision(project_dir)
            if starter_data:
                s_id = starter_data.get("starter_id")
                if s_id:
                    s0_tasks = cls.create_story_zero(starter_id=s_id, starter_info=starter_data)
                    all_tasks.extend(s0_tasks)
                    story_zero_done_dep = s0_tasks[-1].id  # STORY-0-T2

        for st in stories:
            s_id = st.get("id", "ST-001")
            s_title = st.get("title", "")
            req_db = st.get("requires_db", True)
            req_fe = st.get("requires_frontend", True)
            tasks = cls.decompose_story(
                story_id=s_id,
                story_title=s_title,
                requires_db=req_db,
                requires_frontend=req_fe,
            )
            # Se STORY-0 existir, as tarefas iniciais das demais stories dependem do sanity check da fundação
            if story_zero_done_dep:
                for t in tasks:
                    if not t.depends_on:
                        t.depends_on.append(story_zero_done_dep)
            all_tasks.extend(tasks)

        return all_tasks
