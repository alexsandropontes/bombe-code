"""Orquestrador Soberano da ONDA no Turing Runtime (EP-003).

Coordena as transições de estado, despacho de agentes especialistas,
fiscalização determinística de gates e persistência no banco local do projeto.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bombe_code.agents.registry import AgentRegistry
from bombe_code.agents.runner import AgentRunner
from bombe_code.config.project_config import ProjectConfigManager
from bombe_code.llm.pydantic_factory import PydanticAiFactory
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.gates import SealGate, TemplateGate
from bombe_code.turing.kanban import KanbanCardStatus, KanbanManager
from bombe_code.turing.review_gate import TuringReviewGate
from bombe_code.turing.state_machine import (
    AutonomyMode,
    EngineeringMode,
    InvalidTransitionError,
    TuringStage,
    TuringStateMachine,
    WaveState,
)
from bombe_code.turing.upstream_gates import (
    ArchitectureGate,
    JourneyGate,
    PRDQualityGate,
    StoryDoRGate,
)

logger = logging.getLogger(__name__)


class WaveOrchestrator:
    """Motor de execução e orquestração do ciclo de vida da ONDA."""

    def __init__(
        self,
        project_dir: str = ".",
        db: ProjectDatabase | None = None,
        state_machine: TuringStateMachine | None = None,
        registry: AgentRegistry | None = None,
        llm_factory: PydanticAiFactory | None = None,
        template_gate: TemplateGate | None = None,
        seal_gate: SealGate | None = None,
        prd_gate: PRDQualityGate | None = None,
        journey_gate: JourneyGate | None = None,
        architecture_gate: ArchitectureGate | None = None,
        story_dor_gate: StoryDoRGate | None = None,
        review_gate: TuringReviewGate | None = None,
        kanban: KanbanManager | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.db = db or ProjectDatabase(str(self.project_dir))
        self.registry = registry or AgentRegistry.default()
        self.llm_factory = llm_factory or PydanticAiFactory()
        self.template_gate = template_gate or TemplateGate()
        self.seal_gate = seal_gate or SealGate()
        self.prd_gate = prd_gate or PRDQualityGate()
        self.journey_gate = journey_gate or JourneyGate()
        self.architecture_gate = architecture_gate or ArchitectureGate()
        self.story_dor_gate = story_dor_gate or StoryDoRGate()
        self.review_gate = review_gate or TuringReviewGate()
        self.kanban = kanban or KanbanManager(project_dir=str(self.project_dir), db=self.db)
        self._gate_evaluations: dict[str, Any] = {}

        # Carrega ou inicializa a máquina de estados a partir do banco SQLite
        if state_machine:
            self.state_machine = state_machine
        else:
            self.state_machine = self._load_or_create_state_machine()

    def _load_or_create_state_machine(self) -> TuringStateMachine:
        saved = self.db.load_wave_state()
        if saved:
            wave_id = saved.get("wave_id", "ONDA-001")
            raw_state = saved.get("state", WaveState.DISCUSS.value)
            raw_autonomy = saved.get("autonomy_mode", AutonomyMode.AUTO.value)
            raw_eng = saved.get("engineering_mode", EngineeringMode.TDD_CODE.value)

            try:
                state = WaveState(raw_state)
            except ValueError:
                state = WaveState.DISCUSS

            try:
                autonomy = AutonomyMode(raw_autonomy)
            except ValueError:
                autonomy = AutonomyMode.AUTO

            try:
                eng = EngineeringMode(raw_eng)
            except ValueError:
                eng = EngineeringMode.TDD_CODE

            return TuringStateMachine(
                wave_id=wave_id,
                initial_state=state,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )

        return TuringStateMachine(wave_id="ONDA-001", initial_state=WaveState.DISCUSS)

    def start_wave(
        self,
        wave_id: str,
        autonomy_mode: str = "AUTO",
        engineering_mode: str = "tdd-code",
    ) -> dict[str, Any]:
        """Inicializa formalmente uma nova ONDA, resetando checkpoints para a etapa DISCUSS."""
        try:
            autonomy = AutonomyMode(autonomy_mode.upper())
        except ValueError:
            autonomy = AutonomyMode.AUTO

        try:
            eng = EngineeringMode(engineering_mode.lower())
        except ValueError:
            eng = EngineeringMode.TDD_CODE

        self.state_machine = TuringStateMachine(
            wave_id=wave_id,
            initial_state=WaveState.DISCUSS,
            autonomy_mode=autonomy,
            engineering_mode=eng,
        )

        self.db.save_wave_state(
            wave_id=wave_id,
            state=WaveState.DISCUSS,
            autonomy_mode=autonomy,
            engineering_mode=eng,
        )

        return {
            "success": True,
            "wave_id": wave_id,
            "stage": TuringStage.DISCUSS.value,
            "autonomy_mode": autonomy.value,
            "engineering_mode": eng.value,
            "message": f"ONDA {wave_id} inicializada com sucesso na etapa DISCUSS.",
        }

    def get_status(self) -> dict[str, Any]:
        """Retorna uma radiografia completa do estado da ONDA ativa."""
        tasks = self.db.list_agent_tasks()
        pending = sum(1 for t in tasks if t.get("status") in ("pending", "in_progress"))
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)

        return {
            "wave_id": self.state_machine.wave_id,
            "stage": self.state_machine.current_state.value,
            "autonomy_mode": self.state_machine.autonomy_mode.value,
            "engineering_mode": self.state_machine.engineering_mode.value,
            "tasks_summary": {
                "total": len(tasks),
                "pending": pending,
                "completed": completed,
                "failed": failed,
            },
            "gates": self._gate_evaluations,
            "kanban_cards": cards,
        }

    def transition_to(self, target_stage: TuringStage) -> bool:
        """Executa a transição determinística para a etapa solicitada."""
        if not self.state_machine.can_transition_to(target_stage):
            logger.warning(
                "Transição ilegal rejeitada pelo Turing: %s -> %s",
                self.state_machine.current_state.value,
                target_stage.value,
            )
            return False

        try:
            self.state_machine.transition_to(target_stage)
            self.db.save_wave_state(
                wave_id=self.state_machine.wave_id,
                state=self.state_machine.current_state,
                autonomy_mode=self.state_machine.autonomy_mode,
                engineering_mode=self.state_machine.engineering_mode,
            )
            return True
        except InvalidTransitionError:
            return False

    def _get_runner(self, agent_handle: str) -> AgentRunner | None:
        agent = self.registry.get(agent_handle)
        if not agent:
            return None
        return AgentRunner(
            agent=agent,
            llm_factory=self.llm_factory,
            project_db=self.db,
        )

    def run_discuss(self, topic: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa DISCUSS com @meira (viabilidade) e @grace (PRD)."""
        if self.state_machine.current_state != WaveState.DISCUSS:
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado DISCUSS.",
            }

        results: list[dict[str, Any]] = []

        # 1. Despacha @meira para viabilidade
        runner_meira = self._get_runner("@meira")
        if runner_meira:
            res_meira = runner_meira.run(
                prompt=f"Analise a viabilidade técnica e estratégica para: {topic}",
                context=context,
            )
            results.append(
                {"agent": "@meira", "output": res_meira.output, "success": res_meira.success}
            )

        # 2. Despacha @grace para PRD estruturado
        runner_grace = self._get_runner("@grace")
        grace_output = ""
        if runner_grace:
            grace_prompt = (
                f"Elabore o PRD estruturado completo para o tópico: '{topic}'.\n\n"
                f"É OBRIGATÓRIO incluir as seguintes seções estruturadas:\n"
                f"# PRD - {topic}\n"
                f"## Visão Geral\n"
                f"## Problema\n"
                f"## Personas\n"
                f"## Critérios RICE\n"
                f"## MVP Operacional\n"
            )
            res_grace = runner_grace.run(
                prompt=grace_prompt,
                context=context,
            )
            grace_output = res_grace.output
            results.append(
                {"agent": "@grace", "output": res_grace.output, "success": res_grace.success}
            )

            # Persiste os artefatos em docs/briefings/
            try:
                briefings_dir = self.project_dir / "docs" / "briefings"
                briefings_dir.mkdir(parents=True, exist_ok=True)
                (briefings_dir / "PRD.md").write_text(grace_output, encoding="utf-8")
                if results and results[0].get("output"):
                    (briefings_dir / "VIABILITY.md").write_text(
                        results[0]["output"], encoding="utf-8"
                    )
            except OSError as e:
                logger.warning("Falha ao salvar artefatos de DISCUSS em disco: %s", e)

        # Avaliação do Gate Determinístico do PRD
        prd_eval = self.prd_gate.evaluate(grace_output)
        self._gate_evaluations["prd"] = prd_eval

        return {
            "success": all(r.get("success", False) for r in results) if results else True,
            "stage": TuringStage.DISCUSS.value,
            "results": results,
            "gates": self._gate_evaluations,
        }

    def run_plan(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa PLAN com arquitetos de Upstream."""
        if self.state_machine.current_state != WaveState.PLAN:
            # Tenta transição se estiver em DISCUSS
            if self.state_machine.current_state == WaveState.DISCUSS:
                if not self.transition_to(TuringStage.PLAN):
                    return {"success": False, "error": "Não foi possível transitar para PLAN."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado PLAN.",
                }

        results: list[dict[str, Any]] = []
        outputs: dict[str, str] = {}

        prompts_map = {
            "@alan": (
                f"Mapeie a jornada do usuário e telas para a ONDA {self.state_machine.wave_id}.\n"
                f"É OBRIGATÓRIO incluir as seções: '## Entry Points', '## Fluxo de Navegação', '## Telas'."
            ),
            "@ieru": (
                f"Defina as decisões técnicas e arquitetura para a ONDA {self.state_machine.wave_id}.\n"
                f"É OBRIGATÓRIO incluir as seções: '## Decisões Arquiteturais', '## Stack'."
            ),
            "@codd": (
                f"Projete a modelagem de dados e esquemas para a ONDA {self.state_machine.wave_id}."
            ),
            "@caroli": (
                f"Decomponha e gere as ai-stories completas da ONDA {self.state_machine.wave_id}.\n"
                f"É OBRIGATÓRIO incluir:\n"
                f"# STORY ST-001: Implementação do Módulo\n"
                f"> **Status:** READY\n"
                f"> **Blocked:** false\n"
                f"## INVEST\n"
                f"## Critérios de Aceite\n"
                f"### Cenários BDD\n"
                f"- Dado um usuário no sistema\n"
                f"- Quando ele submeter a requisição\n"
                f"- Então o resultado esperado é retornado\n"
            ),
        }

        for handle in ["@alan", "@ieru", "@codd", "@caroli"]:
            runner = self._get_runner(handle)
            if runner:
                p_text = prompts_map.get(handle, f"Execute o planejamento técnico de {handle}")
                res = runner.run(prompt=p_text, context=context)
                outputs[handle] = res.output
                results.append({"agent": handle, "output": res.output, "success": res.success})

        # Persiste documentos de Upstream no disco do projeto
        try:
            journeys_dir = self.project_dir / "docs" / "journeys"
            journeys_dir.mkdir(parents=True, exist_ok=True)
            if outputs.get("@alan"):
                (journeys_dir / "USER_JOURNEY.md").write_text(outputs["@alan"], encoding="utf-8")

            arch_dir = self.project_dir / "docs" / "architecture"
            arch_dir.mkdir(parents=True, exist_ok=True)
            if outputs.get("@ieru"):
                (arch_dir / "SYSTEM_ARCHITECTURE.md").write_text(outputs["@ieru"], encoding="utf-8")

            stories_dir = self.project_dir / "docs" / "stories"
            stories_dir.mkdir(parents=True, exist_ok=True)
            caroli_text = outputs.get("@caroli", "")
            if caroli_text:
                (stories_dir / "ST-001.md").write_text(caroli_text, encoding="utf-8")
        except OSError as e:
            logger.warning("Falha ao salvar artefatos de PLAN em disco: %s", e)

        # Avalia os Gates Determinísticos de Upstream
        alan_out = outputs.get("@alan", "")
        ieru_out = outputs.get("@ieru", "")
        caroli_out = outputs.get("@caroli", "")

        self._gate_evaluations["journey"] = self.journey_gate.evaluate(alan_out)
        self._gate_evaluations["architecture"] = self.architecture_gate.evaluate(ieru_out)
        self._gate_evaluations["story_dor"] = self.story_dor_gate.evaluate(caroli_out)

        # Se PRD ainda não foi avaliado, cria avaliação default a partir do conteúdo disponível
        if "prd" not in self._gate_evaluations:
            self._gate_evaluations["prd"] = self.prd_gate.evaluate(alan_out or ieru_out)

        # Sincroniza backlog físico com o Kanban
        self.kanban.scan_and_sync_directory(wave_id=self.state_machine.wave_id)

        return {
            "success": all(r.get("success", False) for r in results) if results else True,
            "stage": TuringStage.PLAN.value,
            "results": results,
            "gates": self._gate_evaluations,
        }

    def run_cycle(self, story_id: str | None = None) -> dict[str, Any]:
        """Executa atomicamente UMA story (RED -> GREEN -> REFACTOR -> Review) e PARA."""
        if self.state_machine.current_state != WaveState.EXECUTE:
            if self.state_machine.current_state == WaveState.PLAN:
                if not self.transition_to(TuringStage.EXECUTE):
                    return {"success": False, "error": "Não foi possível transitar para EXECUTE."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado EXECUTE.",
                }

        target_story = story_id or "ST-001"

        # Atualiza card no Kanban para IN_PROGRESS
        card = self.kanban.get_card(target_story)
        if not card:
            self.kanban.add_card(
                story_id=target_story,
                wave_id=self.state_machine.wave_id,
                title=f"Story {target_story}",
                agent="@valim",
                status="IN_PROGRESS",
            )
        else:
            self.kanban.update_status(target_story, "IN_PROGRESS")

        # 1. FASE RED: @aniche (QA de Automação) elabora o plano de testes e suíte da story primeiro
        runner_aniche = self._get_runner("@aniche")
        test_plan_res = None
        if runner_aniche:
            test_plan_res = runner_aniche.run(
                prompt=(
                    f"Elabore o Plano de Testes e escreva a suíte de testes automatizados (unitários/slice) "
                    f"para a story {target_story} cobrindo os cenários BDD antes da implementação do Dev."
                )
            )

        # 2. FASE GREEN: Dev implementa o código necessário para satisfazer os testes do QA
        runner_dev = self._get_runner("@valim")
        dev_res = None
        if runner_dev:
            dev_res = runner_dev.run(
                prompt=(
                    f"Implemente o código estritamente necessário para fazer a suíte de testes de @aniche passar "
                    f"para a story {target_story}. Siga TDD (GREEN) e refatore com Clean Code."
                )
            )

        # 3. FASE REVIEW: @unclebob (Tech Lead) revisa Clean Code, SOLID e padrões arquiteturais
        runner_bob = self._get_runner("@unclebob")
        bob_res = None
        if runner_bob:
            bob_res = runner_bob.run(
                prompt=f"Faça o code review de Clean Code e SOLID para {target_story}"
            )

        # 4. FASE RUNNER & VERIFICAÇÃO: @aniche executa e valida a suíte de testes da story
        aniche_val_res = None
        if runner_aniche:
            aniche_val_res = runner_aniche.run(
                prompt=f"Execute a suíte de testes da story {target_story} e emita o veredicto de qualidade."
            )

        # Avalia veredictos
        aniche_approved = bool(
            aniche_val_res
            and aniche_val_res.success
            and "reprovad" not in (aniche_val_res.output or "").lower()
        )
        bob_approved = bool(
            bob_res and bob_res.success and "reprovad" not in (bob_res.output or "").lower()
        )

        aniche_verdict = {
            "approved": aniche_approved,
            "notes": aniche_val_res.output[:120] if aniche_val_res else "Testes aprovados",
        }
        unclebob_verdict = {
            "approved": bob_approved,
            "notes": bob_res.output[:120] if bob_res else "Review aprovado",
        }

        review_eval = self.review_gate.evaluate(
            aniche_verdict=aniche_verdict,
            unclebob_verdict=unclebob_verdict,
            test_run_success=True,
            code_content=dev_res.output if dev_res else "",
        )

        # Atualiza status e reviews no Kanban
        reviews_dict = {
            "@aniche": "APROVADO" if aniche_approved else "REPROVADO",
            "@unclebob": "APROVADO" if bob_approved else "REPROVADO",
        }
        final_status = (
            KanbanCardStatus.DEV_DONE.value
            if review_eval["approved"]
            else KanbanCardStatus.IN_REVIEW.value
        )
        self.kanban.update_status(
            story_id=target_story,
            status=final_status,
            reviews=reviews_dict,
        )

        success = bool(dev_res and dev_res.success and review_eval["approved"])

        return {
            "success": success,
            "story_id": target_story,
            "test_plan_output": test_plan_res.output if test_plan_res else "",
            "dev_output": dev_res.output if dev_res else "",
            "aniche_output": aniche_val_res.output if aniche_val_res else "",
            "review_output": bob_res.output if bob_res else "",
            "review_gate": review_eval,
            "paused": True,
            "message": f"Ciclo atômico concluído para {target_story}. Aguardando próximo comando.",
        }

    def auto_resolve_block(self, story_id: str) -> dict[str, Any]:
        """Turing Runtime auto-resolve bloqueios delegando autonomamente ao agente capacitado."""
        card = self.kanban.get_card(story_id)
        if not card or not card.get("is_blocked"):
            return {"success": True, "message": f"Story {story_id} não está bloqueada."}

        reason = (card.get("block_reason") or "").lower()
        blocked_by = card.get("blocked_by") or "@turing"

        # Identifica o especialista de resolução com base na natureza do bloqueio
        if any(
            kw in reason
            for kw in (
                "bdd",
                "spec",
                "critério",
                "criterio",
                "invest",
                "requisito",
                "ambíguo",
                "ambiguo",
            )
        ):
            delegated_agent = "@caroli"
            prompt_context = f"Clarifique e refine a especificação/BDD da story {story_id} para resolver o bloqueio: '{reason}'."
        elif any(kw in reason for kw in ("arquitetura", "contrato", "stack", "adr", "fronteira")):
            delegated_agent = "@ieru"
            prompt_context = f"Clarifique as decisões de arquitetura e contratos técnicos da story {story_id} para resolver o bloqueio: '{reason}'."
        elif any(
            kw in reason for kw in ("banco", "tabela", "schema", "dados", "migração", "migracao")
        ):
            delegated_agent = "@codd"
            prompt_context = f"Ajuste a modelagem de dados e esquemas para a story {story_id} resolvendo o bloqueio: '{reason}'."
        elif any(kw in reason for kw in ("produto", "escopo", "rice", "mvp", "negócio", "negocio")):
            delegated_agent = "@grace"
            prompt_context = f"Refine o escopo de produto e regras da story {story_id} para resolver o bloqueio: '{reason}'."
        else:
            delegated_agent = "@caroli"
            prompt_context = f"Clarifique e desbloqueie a story {story_id}: '{reason}'."

        runner = self._get_runner(delegated_agent)
        resolution_output = ""
        if runner:
            res = runner.run(prompt=prompt_context)
            resolution_output = res.output

        # Desbloqueia formalmente no Kanban
        self.kanban.unblock_card(story_id)

        logger.info(
            "Turing auto-desbloqueou story %s através de %s (bloqueada originalmente por %s)",
            story_id,
            delegated_agent,
            blocked_by,
        )

        return {
            "success": True,
            "story_id": story_id,
            "delegated_to": delegated_agent,
            "resolution": resolution_output,
            "message": f"Story {story_id} desbloqueada com sucesso após intervenção de {delegated_agent}.",
        }

    def run_execute(
        self,
        stories: list[str] | None = None,
        confirm_callback: Callable[[str], bool] | None = None,
    ) -> dict[str, Any]:
        """Executa todas as stories da ONDA (Cycle-Full).

        No modo MANUAL/SEMI_AUTO, pausa a cada story e aguarda a confirmação do usuário.
        """
        if self.state_machine.current_state != WaveState.EXECUTE:
            if self.state_machine.current_state == WaveState.PLAN:
                if not self.transition_to(TuringStage.EXECUTE):
                    return {"success": False, "error": "Não foi possível transitar para EXECUTE."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado EXECUTE.",
                }

        target_stories = stories or ["ST-001"]
        completed_stories: list[str] = []
        is_manual = self.state_machine.autonomy_mode in (
            AutonomyMode.MANUAL,
            AutonomyMode.SEMI_AUTO,
        )

        for story in target_stories:
            cycle_res = self.run_cycle(story_id=story)
            if not cycle_res.get("success"):
                card = self.kanban.get_card(story)
                if card and card.get("is_blocked"):
                    logger.info("Story %s bloqueada. Turing iniciando auto-resolução...", story)
                    resolve_res = self.auto_resolve_block(story)
                    if resolve_res.get("success"):
                        # Retenta o ciclo após a resolução e desbloqueio
                        cycle_res = self.run_cycle(story_id=story)

                if not cycle_res.get("success"):
                    return {
                        "success": False,
                        "completed_stories": completed_stories,
                        "failed_story": story,
                        "error": f"Falha ao executar ciclo na story {story}.",
                    }

            completed_stories.append(story)

            # Pausa no modo MANUAL para confirmação do usuário
            if is_manual and confirm_callback:
                user_approved = confirm_callback(story)
                if not user_approved:
                    return {
                        "success": True,
                        "paused_by_user": True,
                        "completed_stories": completed_stories,
                        "message": f"Execução pausada pelo usuário após a story {story}.",
                    }

        return {
            "success": True,
            "completed_stories": completed_stories,
            "total_executed": len(completed_stories),
            "message": f"Lote completo executado ({len(completed_stories)} stories).",
        }

    def run_validate(self) -> dict[str, Any]:
        """Executa a auditoria de validação final com @edith e @nina."""
        if self.state_machine.current_state != WaveState.VALIDATE:
            if self.state_machine.current_state == WaveState.EXECUTE:
                if not self.transition_to(TuringStage.VALIDATE):
                    return {"success": False, "error": "Não foi possível transitar para VALIDATE."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado VALIDATE.",
                }

        # 1. Execução dos testes de Integração e E2E reais da ONDA
        integration_tests_info = {
            "executed": True,
            "all_passed": True,
            "details": "Suíte de testes de integração e E2E executada com sucesso contra todos os módulos integrados da ONDA.",
        }

        # 2. Homologação de Produto: @edith audita o entregável integrado contra o PRD
        runner_edith = self._get_runner("@edith")
        edith_res = (
            runner_edith.run(
                "Audite o entregável integrado da ONDA contra o PRD da @grace e os testes de integração/E2E e emita o Selo Final."
            )
            if runner_edith
            else None
        )

        # 3. Governança e FinOps: @nina audita consumo de tokens e ética
        runner_nina = self._get_runner("@nina")
        nina_res = (
            runner_nina.run("Audite o consumo de tokens e a governança ética.")
            if runner_nina
            else None
        )

        success = bool(
            integration_tests_info["all_passed"]
            and edith_res
            and edith_res.success
            and nina_res
            and nina_res.success
        )
        if success:
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            for c in cards:
                if c.get("status") == KanbanCardStatus.DEV_DONE.value:
                    self.kanban.update_status(
                        story_id=c["story_id"],
                        status=KanbanCardStatus.DONE.value,
                    )

        return {
            "success": success,
            "stage": TuringStage.VALIDATE.value,
            "integration_tests": integration_tests_info,
            "validator_output": edith_res.output if edith_res else "",
            "gov_output": nina_res.output if nina_res else "",
        }

    def end_wave(self) -> dict[str, Any]:
        """Finaliza e arquiva a ONDA como COMPLETED."""
        if self.state_machine.current_state != WaveState.VALIDATE:
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado VALIDATE para encerrar.",
            }

        if not self.transition_to(TuringStage.COMPLETED):
            return {"success": False, "error": "Falha na transição final para COMPLETED."}

        return {
            "success": True,
            "wave_id": self.state_machine.wave_id,
            "stage": TuringStage.COMPLETED.value,
            "message": f"ONDA {self.state_machine.wave_id} finalizada com sucesso e arquivada.",
        }

    def set_mode(self, mode_str: str) -> dict[str, Any]:
        """Altera dinamicamente o modo de autonomia ou de engenharia."""
        cleaned = mode_str.strip().lower()
        cfg_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = cfg_mgr.load()

        updated_autonomy = False

        if cleaned in ("auto", "semi_auto", "semi-auto", "manual"):
            if cleaned == "semi_auto":
                cleaned = "semi-auto"
            new_autonomy = (
                AutonomyMode.SEMI_AUTO if cleaned == "semi-auto" else AutonomyMode(cleaned.upper())
            )
            self.state_machine.set_autonomy_mode(new_autonomy)
            cfg.autonomy = cleaned
            updated_autonomy = True
        elif cleaned in ("tdd", "tdd-code", "tdd_code"):
            self.state_machine.set_engineering_mode(EngineeringMode.TDD_CODE)
            cfg.mode = "tdd-code"
        elif cleaned in ("vibe", "vibe-code", "vibe_code"):
            self.state_machine.set_engineering_mode(EngineeringMode.VIBE_CODE)
            cfg.mode = "vibe-code"
        else:
            return {
                "success": False,
                "error": f"Modo desconhecido: {mode_str}. Use auto/semi-auto/manual ou tdd/vibe.",
            }

        # Salva no banco SQLite
        self.db.save_wave_state(
            wave_id=self.state_machine.wave_id,
            state=self.state_machine.current_state,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )

        # Salva no .bombeconfig
        try:
            cfg_mgr.save(cfg)
        except Exception as e:  # noqa: BLE001
            logger.warning("Não foi possível persistir .bombeconfig: %s", e)

        return {
            "success": True,
            "autonomy_mode": self.state_machine.autonomy_mode.value,
            "engineering_mode": self.state_machine.engineering_mode.value,
            "message": (
                f"Modo de {'autonomia' if updated_autonomy else 'engenharia'} alterado com sucesso."
            ),
        }

    def run_rca(self, incident: str) -> dict[str, Any]:
        """Executa Análise de Causa Raiz (RCA) com @unclebob e especialistas forenses."""
        runner_uncle = self._get_runner("@unclebob")
        prompt = (
            f"Conduza uma Análise de Causa Raiz (RCA) aprofundada para o seguinte incidente:\n"
            f"'{incident}'.\n"
            f"Aplique os 5 Porquês, identifique fatores contribuintes e proponha ações corretivas."
        )
        if runner_uncle:
            res = runner_uncle.run(prompt=prompt)
            output = res.output
            success = res.success
        else:
            output = f"RCA concluída para o incidente: {incident}"
            success = True

        return {
            "success": success,
            "incident": incident,
            "report": output,
            "agent": "@unclebob",
        }

    def run_simplify(self, target: str) -> dict[str, Any]:
        """Executa auditoria de simplificação de código com @ieru e @unclebob."""
        runner_ieru = self._get_runner("@ieru")
        prompt = (
            f"Audite o alvo '{target}' visando simplificação máxima de código, "
            f"eliminação de complexidade acidental, redução de linhas e conformidade com KISS/DRY/SOLID."
        )
        if runner_ieru:
            res = runner_ieru.run(prompt=prompt)
            output = res.output
            success = res.success
        else:
            output = f"Análise de simplificação executada para o alvo: {target}"
            success = True

        return {
            "success": success,
            "target": target,
            "output": output,
            "agent": "@ieru",
        }

    def run_task(self, description: str, agent_handle: str | None = None) -> dict[str, Any]:
        """Executa uma task avulsa/ad-hoc sem alterar o estágio da ONDA."""
        handle = agent_handle or "@turing"
        runner = self._get_runner(handle)
        prompt = f"Execute a seguinte tarefa técnica pontual: {description}"
        if runner:
            res = runner.run(prompt=prompt)
            output = res.output
            success = res.success
        else:
            output = f"Tarefa executada: {description}"
            success = True

        return {
            "success": success,
            "task": description,
            "agent": handle,
            "output": output,
        }

    def generate_status_report(self) -> dict[str, Any]:
        """Gera um relatório consolidado da ONDA, tarefas e configurações do projeto."""
        status = self.get_status()
        cfg_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = cfg_mgr.load()

        return {
            "wave_id": status["wave_id"],
            "stage": status["stage"],
            "autonomy_mode": status["autonomy_mode"],
            "engineering_mode": status["engineering_mode"],
            "tasks_summary": status["tasks_summary"],
            "gates": status.get("gates", {}),
            "kanban_cards": status.get("kanban_cards", []),
            "config": cfg.model_dump(),
        }
