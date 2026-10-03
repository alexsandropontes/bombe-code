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


class AtomicTaskType(str, Enum):
    """Tipos canônicos de tarefas técnicas atômicas de uma Story."""

    DATABASE = "DATABASE"                # Schema, migrations, índices e persistência
    CONTRACT = "CONTRACT"                # Schemas de validação Zod/Pydantic, tipos e DTOs
    BACKEND_TDD = "BACKEND_TDD"          # Rota, regras de negócio e testes de unidade/integração
    FRONTEND_UI = "FRONTEND_UI"          # Componente de interface, estado e validação inline
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

    DEFAULT_AGENTS: dict[AtomicTaskType, str] = {
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
