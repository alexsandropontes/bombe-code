"""Executor de agentes integrado com Pydantic AI, Skills sob demanda e Kanban local."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from pydantic import BaseModel, Field

from bombe_code.agents.models import AgentDefinition
from bombe_code.llm.pydantic_factory import PydanticAiFactory
from bombe_code.llm.quota_detector import is_quota_or_rate_limit_error
from bombe_code.skills.registry import SkillRegistry
from bombe_code.skills.tools import make_skill_tools
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.progress import ABORT_EVENT, BUS

logger = logging.getLogger(__name__)


class AgentExecutionResult(BaseModel):
    """Resultado da execução de um turno de um agente."""

    agent_handle: str = Field(..., description="Handle do agente que executou")
    success: bool = Field(..., description="Indica se a execução ocorreu com sucesso")
    status: str = Field(
        default="COMPLETED", description="Status da execução: COMPLETED, BLOCKED ou FAILED"
    )
    is_blocked: bool = Field(
        default=False, description="Indica se o agente reportou bloqueio ou impedimento"
    )
    block_reason: str | None = Field(
        default=None, description="Motivo do bloqueio caso is_blocked seja True"
    )
    output: str = Field(default="", description="Saída textual ou estruturada gerada pelo agente")
    error: str | None = Field(default=None, description="Mensagem de erro em caso de falha")
    task_id: str | None = Field(
        default=None, description="ID da task registrada no SQLite do projeto"
    )
    input_tokens: int = Field(default=0, description="Tokens de entrada/prompt")
    output_tokens: int = Field(default=0, description="Tokens de saída/completion")
    total_tokens: int = Field(default=0, description="Total de tokens consumidos")
    cost: float = Field(default=0.0, description="Custo calculado em USD")
    duration_seconds: float = Field(default=0.0, description="Duração da chamada em segundos")


class AgentRunner:
    """Orquestrador de execução de um agente com injeção de tools e persistência de tarefas."""

    def __init__(
        self,
        agent: AgentDefinition,
        llm_factory: PydanticAiFactory,
        skill_registry: SkillRegistry | None = None,
        project_db: ProjectDatabase | None = None,
        extra_tools: list[Any] | None = None,
        router: Any | None = None,
        guarda: Any | None = None,
    ) -> None:
        self.agent = agent
        self.llm_factory = llm_factory
        self.skill_registry = skill_registry
        self.project_db = project_db
        self.extra_tools = extra_tools or []
        self.router = router
        self.guarda = guarda

    def _prepare_tools(self) -> list[Any]:
        """Prepara e injeta as tools de busca e carregamento de skills."""
        tools: list[Any] = list(self.extra_tools)
        if self.skill_registry:
            search_fn, load_fn = make_skill_tools(self.skill_registry)
            tools.extend([search_fn, load_fn])
        return tools

    def run(self, prompt: str, context: dict[str, Any] | None = None) -> AgentExecutionResult:
        """Executa um ciclo de trabalho do agente via Pydantic AI.

        No modo verboso (padrão), o texto, o raciocínio e as tool calls são
        publicados no TuringProgressBus em tempo real (streaming token-a-token).
        No modo quiet, o barramento filtra os deltas e mantém apenas anúncios.
        """
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

        max_attempts = (
            max(1, len(self.router.slots))
            if (self.router and getattr(self.router, "slots", None))
            else 1
        )

        for attempt in range(max_attempts):
            active_slot = self.router.get_active_slot() if self.router else None
            model_to_use = active_slot.model if active_slot else None

            try:
                # Cria a instância tipada do agente Pydantic AI
                pydantic_agent = self.llm_factory.create_agent(
                    model_name=model_to_use,
                    system_prompt=self.agent.system_prompt,
                    tools=tools,
                )

                # Execução síncrona ou assíncrona
                exec_prompt = prompt
                if context:
                    context_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
                    exec_prompt = f"{prompt}\n\nContexto da Execução:\n{context_str}"

                t0 = time.perf_counter()
                provider_tag = (
                    f" via {active_slot.name} ({active_slot.model})" if active_slot else ""
                )
                # Anúncio por agente (paridade opencode: cada especialista é
                # anunciado e o stream completo dele aparece na tela).
                from bombe_code.turing.progress import BUS as _bus

                _bus.publish(
                    "agent_start",
                    agent=self.agent.handle,
                    text=f"🤖 [{self.agent.handle}] executando sua parte{provider_tag}...",
                )
                if not os.environ.get("BOMBE_TUI_RUNNING"):
                    print(
                        f"  ⚡ [{self.agent.handle}] Invocando modelo{provider_tag}...", flush=True
                    )
                logger.info("  ⚡ [%s] Invocando modelo%s...", self.agent.handle, provider_tag)
                from pydantic_ai.usage import UsageLimits

                limits = UsageLimits(request_limit=15)

                # Execução: streaming de eventos (verboso) com fallback síncrono.
                is_mock = type(pydantic_agent).__name__.endswith("Mock")
                stream_capable = not is_mock and hasattr(pydantic_agent, "run_stream_events")

                raw_result = None
                if stream_capable:
                    try:
                        raw_result = self._run_with_stream_events(
                            pydantic_agent, exec_prompt, limits
                        )
                    except (TypeError, AttributeError) as api_exc:
                        logger.warning(
                            "Streaming de eventos indisponível para %s (%s); usando execução síncrona.",
                            self.agent.handle,
                            api_exc,
                        )

                if raw_result is None:
                    # Pydantic AI real usa run_sync, mocks de teste usam run
                    if (
                        is_mock
                        and hasattr(pydantic_agent, "run_sync")
                        and not type(pydantic_agent.run_sync.return_value).__name__.endswith("Mock")
                    ):
                        try:
                            raw_result = pydantic_agent.run_sync(exec_prompt, usage_limits=limits)
                        except TypeError:
                            raw_result = pydantic_agent.run_sync(exec_prompt)
                    elif is_mock:
                        raw_result = pydantic_agent.run(exec_prompt)
                    elif hasattr(pydantic_agent, "run_sync"):
                        try:
                            raw_result = pydantic_agent.run_sync(exec_prompt, usage_limits=limits)
                        except TypeError:
                            raw_result = pydantic_agent.run_sync(exec_prompt)
                    else:
                        raw_result = pydantic_agent.run(exec_prompt)

                duration_seconds = round(time.perf_counter() - t0, 3)
                if not os.environ.get("BOMBE_TUI_RUNNING"):
                    print(
                        f"  ✓ [{self.agent.handle}] Resposta recebida em {duration_seconds:.1f}s.",
                        flush=True,
                    )
                logger.info(
                    "  ✓ [%s] Resposta recebida em %.1fs.", self.agent.handle, duration_seconds
                )

                # Extrai telemetria de tokens e custos do Pydantic AI
                input_tokens = 0
                output_tokens = 0
                total_tokens = 0
                cost = 0.0

                usage_obj = getattr(raw_result, "usage", None)
                if usage_obj is not None:
                    if callable(usage_obj):
                        try:
                            usage_obj = usage_obj()
                        except (TypeError, AttributeError):  # pragma: no cover
                            pass
                    input_tokens = getattr(usage_obj, "input_tokens", 0) or 0
                    output_tokens = getattr(usage_obj, "output_tokens", 0) or 0
                    total_tokens = getattr(usage_obj, "total_tokens", 0) or (
                        input_tokens + output_tokens
                    )
                    c = getattr(usage_obj, "cost", 0.0) or 0.0
                    try:
                        cost = float(c)
                    except (ValueError, TypeError):
                        cost = 0.0

                # Extrai texto de saída suportando pydantic-ai real (.output) e mocks de teste (.data)
                if hasattr(raw_result, "output") and not type(raw_result.output).__name__.endswith(
                    "Mock"
                ):
                    output_text = raw_result.output
                elif hasattr(raw_result, "data") and not type(raw_result.data).__name__.endswith(
                    "Mock"
                ):
                    output_text = raw_result.data
                elif hasattr(raw_result, "output"):
                    output_text = raw_result.output
                else:
                    output_text = getattr(raw_result, "data", str(raw_result))

                output_str = str(output_text)
                is_blocked, block_reason = self._detect_block(output_str)

                task_status = "blocked" if is_blocked else "completed"
                if self.project_db and task_id:
                    self.project_db.update_agent_task_status(
                        task_id, task_status, output=output_str
                    )

                if total_tokens or cost:
                    BUS.publish(
                        "agent_usage",
                        agent=self.agent.handle,
                        total_tokens=total_tokens,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost=cost,
                    )

                return AgentExecutionResult(
                    agent_handle=self.agent.handle,
                    success=not is_blocked,
                    status="BLOCKED" if is_blocked else "COMPLETED",
                    is_blocked=is_blocked,
                    block_reason=block_reason,
                    output=output_str,
                    task_id=task_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    duration_seconds=duration_seconds,
                )

            except Exception as exc:  # noqa: BLE001
                logger.error("Falha na execução do agente %s: %s", self.agent.handle, exc)

                # BANDEIRA VERMELHA: comportamento indevido determinado pela
                # Guardiã — escala para o humano com evidência (a exceção do
                # processo), sem apagar o trabalho já gravado.
                if isinstance(exc, InterruptedError):
                    motivo = f"⏸ {exc}"
                    if self.project_db and task_id:
                        self.project_db.update_agent_task_status(task_id, "blocked", output=motivo)
                    return AgentExecutionResult(
                        agent_handle=self.agent.handle,
                        success=False,
                        status="INTERRUPTED",
                        is_blocked=True,
                        block_reason=motivo,
                        error=str(exc),
                        task_id=task_id,
                    )

                from bombe_code.permissions.acao_guard import RedFlagError

                if isinstance(exc, RedFlagError):
                    from bombe_code.turing.progress import BUS as _bus

                    motivo = f"🚩 BANDEIRA VERMELHA do agente {self.agent.handle}: {exc}"
                    _bus.publish("escalation", agent=self.agent.handle, text=motivo)
                    if self.project_db and task_id:
                        self.project_db.update_agent_task_status(task_id, "blocked", output=motivo)
                    return AgentExecutionResult(
                        agent_handle=self.agent.handle,
                        success=False,
                        status="RED_FLAG",
                        is_blocked=True,
                        block_reason=motivo,
                        error=str(exc),
                        task_id=task_id,
                    )

                is_quota, quota_reason = is_quota_or_rate_limit_error(exc)
                if is_quota and self.router:
                    from bombe_code.llm.quota_detector import parse_quota_reset_info

                    quota_info = parse_quota_reset_info(
                        exc, provider_hint=active_slot.name if active_slot else None
                    )
                    next_slot = (
                        self.router.report_quota_exhausted(active_slot, quota_info)
                        if active_slot
                        else None
                    )

                    if next_slot:
                        logger.info(
                            "🔄 [FAILOVER] Alternando automaticamente agente %s para o provedor %s (%s)...",
                            self.agent.handle,
                            next_slot.name,
                            next_slot.model,
                        )
                        continue

                    # Se todos os provedores estão em cooldown, avalia se pode esperar timer
                    should_wait, wait_secs, wait_reason = self.router.should_wait_timer()
                    if should_wait:
                        logger.info(
                            "⏳ [TIMER] %s. Aguardando %.1fs para retomar...",
                            wait_reason,
                            wait_secs,
                        )
                        time.sleep(wait_secs)
                        continue

                if is_quota:
                    logger.critical(
                        "🚨 ESTOURO DE COTA/RATE LIMIT DETECTADO para o agente %s: %s",
                        self.agent.handle,
                        quota_reason,
                    )
                    if self.project_db and task_id:
                        self.project_db.update_agent_task_status(
                            task_id, "blocked", output=quota_reason
                        )

                    return AgentExecutionResult(
                        agent_handle=self.agent.handle,
                        success=False,
                        status="QUOTA_EXHAUSTED",
                        is_blocked=True,
                        block_reason=quota_reason,
                        error=str(exc),
                        task_id=task_id,
                    )

                if self.project_db and task_id:
                    self.project_db.update_agent_task_status(task_id, "failed")

                return AgentExecutionResult(
                    agent_handle=self.agent.handle,
                    success=False,
                    status="FAILED",
                    is_blocked=False,
                    error=str(exc),
                    task_id=task_id,
                )

    def _run_with_stream_events(self, pydantic_agent: Any, exec_prompt: str, limits: Any) -> Any:
        """Executa o agente streamando eventos (texto, raciocínio, tools) no bus.

        Roda um event loop dedicado (seguro em worker thread do orquestrador).
        Se já houver loop rodando na thread corrente, levanta RuntimeError para
        o chamador cair no caminho síncrono.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("run_stream_events requer thread sem event loop ativo")

        from pydantic_ai import AgentRunResultEvent
        from pydantic_ai.messages import (
            FunctionToolCallEvent,
            FunctionToolResultEvent,
            PartDeltaEvent,
            TextPartDelta,
            ThinkingPartDelta,
        )

        from bombe_code.turing.progress import BUS

        handle = self.agent.handle
        # SEMÂNTICA DE TEMPO: só existe o IDLE (provedor sem resposta) —
        # a proteção contra alucinação é a Guardiã de Ações (por ação),
        # não um relógio de duração que mata trabalho legítimo.
        import os
        import time as _time

        idle_s = float(os.environ.get("BOMBE_AGENT_IDLE_TIMEOUT", "240"))

        def _publicar_tool_call(nome: str, args_str: str) -> None:
            """Publica a tool call com paridade opencode: qual arquivo, o quê."""
            BUS.publish("tool_call", agent=handle, text=nome, args=args_str)
            # Gravação/edição de arquivo ganha evento dedicado com prévia do conteúdo
            if ("write" in nome.lower() or "edit" in nome.lower()) and args_str:
                caminho = ""
                previa = ""
                try:
                    import json as _json

                    dados = _json.loads(args_str) if args_str.strip().startswith("{") else {}
                    caminho = str(
                        dados.get("path") or dados.get("file_path") or dados.get("caminho") or ""
                    )
                    conteudo = str(
                        dados.get("content")
                        or dados.get("conteudo")
                        or dados.get("new_string")
                        or ""
                    )
                    previa = conteudo[:700]
                except Exception:  # noqa: BLE001 — prévia é best-effort
                    previa = args_str[:400]
                BUS.publish(
                    "file_write",
                    agent=handle,
                    text=caminho or "(caminho não informado)",
                    preview=previa,
                )

        async def _drive() -> Any:
            inicio = _time.monotonic()
            ultimo_evento = inicio
            result: Any = None
            async with pydantic_agent.run_stream_events(exec_prompt, usage_limits=limits) as events:
                async for ev in events:
                    agora = _time.monotonic()
                    if agora - ultimo_evento > idle_s:
                        raise TimeoutError(
                            f"Provedor sem resposta há {idle_s:.0f}s (nenhum evento de stream) — "
                            f"execução do agente {handle} abortada. (ajuste com BOMBE_AGENT_IDLE_TIMEOUT)"
                        )
                    ultimo_evento = agora
                    # BANDEIRA VERMELHA: a Guardiã vetou ações demais — a LLM
                    # perde o direito de continuar (exceção, não timeout).
                    if self.guarda is not None and self.guarda.red_flag:
                        from bombe_code.permissions.acao_guard import RedFlagError

                        raise RedFlagError(self.guarda.red_flag)
                    if ABORT_EVENT.is_set():
                        raise InterruptedError("Execução interrompida pelo usuário (ESC ESC)")
                    if isinstance(ev, PartDeltaEvent):
                        delta = ev.delta
                        if isinstance(delta, TextPartDelta) and delta.content_delta:
                            BUS.publish("text_delta", agent=handle, text=delta.content_delta)
                        elif isinstance(delta, ThinkingPartDelta) and delta.content_delta:
                            BUS.publish("thinking_delta", agent=handle, text=delta.content_delta)
                    elif isinstance(ev, FunctionToolCallEvent):
                        part = ev.part
                        _publicar_tool_call(
                            getattr(part, "tool_name", "") or "",
                            str(getattr(part, "args", "")),
                        )
                    elif isinstance(ev, FunctionToolResultEvent):
                        # pydantic-ai real: o conteúdo vive em ev.part.content
                        # (ev.content pode vir None — publicava "None" na tela)
                        conteudo = getattr(ev, "content", None)
                        if conteudo is None:
                            part = getattr(ev, "part", None)
                            conteudo = getattr(part, "content", None) if part else None
                        if conteudo is not None:
                            BUS.publish("tool_result", agent=handle, text=str(conteudo)[:4000])
                    elif isinstance(ev, AgentRunResultEvent):
                        result = ev.result
            return result

        return asyncio.run(_drive())

    @staticmethod
    def _detect_block(output_text: str) -> tuple[bool, str | None]:
        """Detecta deterministicamente se a LLM sinalizou bloqueio ou impedimento."""
        text_lower = output_text.lower()
        block_keywords = [
            "bloqueio registrado",
            "auditoria bloqueada",
            "auditoria não iniciável",
            "auditoria não iniciada",
            "auditoria nao iniciavel",
            "auditoria nao iniciada",
            "sem red legítimo",
            "sem red legitimo",
            "status: blocked",
            "status: ⛔",
            "status: ⚠️",
            "[blocked:",
            "🛑 [blocked",
            "impossível prosseguir",
            "impossivel prosseguir",
            "artefatos insuficientes",
            "evidências obrigatórias não recebidas",
            "evidencias obrigatorias nao recebidas",
        ]
        for kw in block_keywords:
            if kw in text_lower:
                for line in output_text.splitlines():
                    if kw in line.lower():
                        clean = line.strip().strip("*#-> []")
                        return True, clean or f"Bloqueio detectado ({kw})"
                return True, f"Bloqueio detectado: {kw}"
        return False, None
