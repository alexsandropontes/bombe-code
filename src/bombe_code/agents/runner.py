"""Executor de agentes integrado com Pydantic AI, Skills sob demanda e Kanban local."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from bombe_code.agents.models import AgentDefinition
from bombe_code.llm.pydantic_factory import PydanticAiFactory
from bombe_code.skills.registry import SkillRegistry
from bombe_code.skills.tools import make_skill_tools
from bombe_code.storage.project_db import ProjectDatabase

logger = logging.getLogger(__name__)


class AgentExecutionResult(BaseModel):
    """Resultado da execução de um turno de um agente."""

    agent_handle: str = Field(..., description="Handle do agente que executou")
    success: bool = Field(..., description="Indica se a execução ocorreu com sucesso")
    output: str = Field(default="", description="Saída textual ou estruturada gerada pelo agente")
    error: str | None = Field(default=None, description="Mensagem de erro em caso de falha")
    task_id: str | None = Field(
        default=None, description="ID da task registrada no SQLite do projeto"
    )


class AgentRunner:
    """Orquestrador de execução de um agente com injeção de tools e persistência de tarefas."""

    def __init__(
        self,
        agent: AgentDefinition,
        llm_factory: PydanticAiFactory,
        skill_registry: SkillRegistry | None = None,
        project_db: ProjectDatabase | None = None,
        extra_tools: list[Any] | None = None,
    ) -> None:
        self.agent = agent
        self.llm_factory = llm_factory
        self.skill_registry = skill_registry
        self.project_db = project_db
        self.extra_tools = extra_tools or []

    def _prepare_tools(self) -> list[Any]:
        """Prepara e injeta as tools de busca e carregamento de skills."""
        tools: list[Any] = list(self.extra_tools)
        if self.skill_registry:
            search_fn, load_fn = make_skill_tools(self.skill_registry)
            tools.extend([search_fn, load_fn])
        return tools

    def run(self, prompt: str, context: dict[str, Any] | None = None) -> AgentExecutionResult:
        """Executa um ciclo de trabalho do agente via Pydantic AI."""
        task_id: str | None = None

        if self.project_db:
            try:
                task_id = self.project_db.create_agent_task(
                    agent_handle=self.agent.handle,
                    description=prompt,
                )
                self.project_db.update_agent_task_status(task_id, "in_progress")
            except (OSError, RuntimeError) as e:
                logger.warning("Não foi possível registrar task no SQLite do projeto: %s", e)

        tools = self._prepare_tools()

        try:
            # Cria a instância tipada do agente Pydantic AI
            pydantic_agent = self.llm_factory.create_agent(
                system_prompt=self.agent.system_prompt,
                tools=tools,
            )

            # Execução síncrona ou assíncrona
            exec_prompt = prompt
            if context:
                context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
                exec_prompt = f"{prompt}\n\nContexto da Execução:\n{context_str}"

            raw_result = pydantic_agent.run(exec_prompt)
            output_text = getattr(raw_result, "data", str(raw_result))

            if self.project_db and task_id:
                self.project_db.update_agent_task_status(task_id, "completed")

            return AgentExecutionResult(
                agent_handle=self.agent.handle,
                success=True,
                output=str(output_text),
                task_id=task_id,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("Falha na execução do agente %s: %s", self.agent.handle, exc)
            if self.project_db and task_id:
                self.project_db.update_agent_task_status(task_id, "failed")

            return AgentExecutionResult(
                agent_handle=self.agent.handle,
                success=False,
                error=str(exc),
                task_id=task_id,
            )
