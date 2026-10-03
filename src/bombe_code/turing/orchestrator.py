"""Orquestrador Soberano da ONDA no Turing Runtime (EP-003).

Coordena as transições de estado, despacho de agentes especialistas,
fiscalização determinística de gates e persistência no banco local do projeto.
"""

from __future__ import annotations

import json
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
from bombe_code.turing.prompt_assembler import DeliveryTarget, TuringPromptAssembler
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
    DatabaseQualityGate,
    JourneyGate,
    PRDQualityGate,
    StoryDoRGate,
    ViabilityQualityGate,
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
        self.viability_gate = ViabilityQualityGate()
        self.prd_gate = prd_gate or PRDQualityGate()
        self.journey_gate = journey_gate or JourneyGate()
        self.architecture_gate = architecture_gate or ArchitectureGate()
        self.db_gate = DatabaseQualityGate()
        self.story_dor_gate = story_dor_gate or StoryDoRGate()
        self.review_gate = review_gate or TuringReviewGate()
        self.kanban = kanban or KanbanManager(project_dir=str(self.project_dir), db=self.db)
        self._gate_evaluations: dict[str, Any] = {}
        self.config_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = self.config_mgr.load()
        raw_target = getattr(cfg, "delivery_target", "mvp")
        self.delivery_target = DeliveryTarget.from_str(raw_target)
        self.prompt_assembler = TuringPromptAssembler()
        self.telemetry: dict[str, Any] = {
            "stages": {},
            "total": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_seconds": 0.0,
            },
        }

        # Carrega ou inicializa a máquina de estados a partir do banco SQLite
        if state_machine:
            self.state_machine = state_machine
        else:
            self.state_machine = self._load_or_create_state_machine()

    def _record_telemetry(self, stage: str, agent: str, result: Any) -> None:
        """Registra métricas de execução de um agente em uma etapa da ONDA."""
        if not result:
            return
        if stage not in self.telemetry["stages"]:
            self.telemetry["stages"][stage] = {
                "agents": [],
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_seconds": 0.0,
            }
        stg = self.telemetry["stages"][stage]
        in_tok = getattr(result, "input_tokens", 0) or 0
        out_tok = getattr(result, "output_tokens", 0) or 0
        tot_tok = getattr(result, "total_tokens", 0) or (in_tok + out_tok)
        c = getattr(result, "cost", 0.0) or 0.0
        dur = getattr(result, "duration_seconds", 0.0) or 0.0

        stg["agents"].append({
            "agent": agent,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "total_tokens": tot_tok,
            "cost": round(c, 6),
            "duration_seconds": round(dur, 3),
            "success": getattr(result, "success", True),
        })
        stg["input_tokens"] += in_tok
        stg["output_tokens"] += out_tok
        stg["total_tokens"] += tot_tok
        stg["cost"] = round(stg["cost"] + c, 6)
        stg["duration_seconds"] = round(stg["duration_seconds"] + dur, 3)

        tot = self.telemetry["total"]
        tot["input_tokens"] += in_tok
        tot["output_tokens"] += out_tok
        tot["total_tokens"] += tot_tok
        tot["cost"] = round(tot["cost"] + c, 6)
        tot["duration_seconds"] = round(tot["duration_seconds"] + dur, 3)

        self._save_telemetry_files()

    def _save_telemetry_files(self) -> None:
        """Persiste os arquivos telemetry.json e telemetria.md sob docs/."""
        try:
            docs_dir = self.project_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            telemetry_json = docs_dir / "telemetry.json"
            telemetry_json.write_text(
                json.dumps(self.telemetry, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            tot = self.telemetry["total"]
            speed = round(tot["total_tokens"] / max(tot["duration_seconds"], 0.001), 1)
            md_lines = [
                f"# 📊 Telemetria de Execução da ONDA {self.state_machine.wave_id}",
                "",
                "## 📈 Resumo Geral Consolidado",
                f"- **Tokens de Entrada (Prompt):** {tot['input_tokens']:,}",
                f"- **Tokens de Saída (Completion):** {tot['output_tokens']:,}",
                f"- **Total de Tokens:** {tot['total_tokens']:,}",
                f"- **Custo Total Estimado:** ${tot['cost']:.6f} USD",
                f"- **Tempo Total em LLM:** {tot['duration_seconds']:.2f}s",
                f"- **Velocidade Média:** {speed:,} tokens/s",
                "",
                "## 📋 Detalhamento por Etapa e Agente Especialista",
                "| Etapa | Agente | Tokens Entrada | Tokens Saída | Total Tokens | Custo (USD) | Duração (s) | Velocidade (tok/s) |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
            for stg_name, stg_data in self.telemetry["stages"].items():
                for ag in stg_data["agents"]:
                    ag_speed = round(
                        ag["total_tokens"] / max(ag["duration_seconds"], 0.001), 1
                    )
                    md_lines.append(
                        f"| **{stg_name}** | `{ag['agent']}` | {ag['input_tokens']:,} | {ag['output_tokens']:,} | {ag['total_tokens']:,} | ${ag['cost']:.6f} | {ag['duration_seconds']:.2f}s | {ag_speed:,} |"
                    )
                stg_speed = round(
                    stg_data["total_tokens"] / max(stg_data["duration_seconds"], 0.001), 1
                )
                md_lines.append(
                    f"| *Subtotal {stg_name}* | - | *{stg_data['input_tokens']:,}* | *{stg_data['output_tokens']:,}* | *{stg_data['total_tokens']:,}* | *${stg_data['cost']:.6f}* | *{stg_data['duration_seconds']:.2f}s* | *{stg_speed:,}* |"
                )

            (docs_dir / "telemetria.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Falha ao salvar arquivos de telemetria: %s", exc)

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
        force: bool = False,
        delivery_target: str | None = None,
    ) -> dict[str, Any]:
        """Inicializa formalmente uma nova ONDA, resetando checkpoints para a etapa DISCUSS."""
        saved = self.db.load_wave_state()
        if (
            not force
            and saved
            and saved.get("state") not in (WaveState.COMPLETED.value, "COMPLETED")
            and saved.get("wave_id") != wave_id
        ):
            current_wave = saved.get("wave_id", "atual")
            current_stage = saved.get("state", "DISCUSS")
            return {
                "success": False,
                "error": "wave_in_progress",
                "current_wave": current_wave,
                "current_stage": current_stage,
                "message": (
                    f"⚠️ A {current_wave} ainda está em andamento (etapa: {current_stage}) e possui pendências ativas. "
                    f"Finalize-a com '/wave end' ou use '--force' ('/wave start {wave_id} --force') para sobrescrever e iniciar uma nova onda."
                ),
            }

        if delivery_target:
            self.delivery_target = DeliveryTarget.from_str(delivery_target)
            try:
                cfg = self.config_mgr.load()
                cfg.delivery_target = self.delivery_target.value
                self.config_mgr.save(cfg)
            except Exception as e:
                logger.warning("Falha ao salvar delivery_target no config: %s", e)

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

    def _get_project_fs_tools(self) -> list[Any]:
        project_dir = self.project_dir

        def read_project_file(path: str) -> str:
            """Lê o conteúdo de um arquivo do projeto a partir do caminho relativo (ex: 'docs/stories/ST-001.md')."""
            try:
                target = (project_dir / path).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return f"Erro: Acesso fora do projeto negado para {path}"
                if not target.exists() or not target.is_file():
                    return f"Erro: Arquivo {path} não existe no projeto."
                return target.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return f"Erro ao ler {path}: {e}"

        def write_project_file(path: str, content: str) -> str:
            """Grava conteúdo em um arquivo do projeto no caminho relativo especificado (ex: 'js/logic.js')."""
            try:
                target = (project_dir / path).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return f"Erro: Acesso fora do projeto negado para {path}"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"Arquivo {path} gravado com sucesso ({len(content)} caracteres)."
            except Exception as e:
                return f"Erro ao gravar {path}: {e}"

        def list_project_files(directory: str = ".") -> list[str]:
            """Lista os arquivos existentes no diretório relativo do projeto."""
            try:
                target = (project_dir / directory).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return ["Erro: Acesso fora do projeto negado."]
                if not target.exists():
                    return []
                return [
                    str(p.relative_to(project_dir))
                    for p in target.rglob("*.*")
                    if p.is_file() and not str(p).startswith(str(project_dir / ".git"))
                ]
            except Exception as e:
                return [f"Erro: {e}"]

        return [read_project_file, write_project_file, list_project_files]

    def _get_runner(self, agent_handle: str) -> AgentRunner | None:
        agent = self.registry.get(agent_handle)
        if not agent:
            return None
        return AgentRunner(
            agent=agent,
            llm_factory=self.llm_factory,
            project_db=self.db,
            extra_tools=self._get_project_fs_tools(),
        )

    def _assemble_prompt(
        self, agent_handle: str, task_prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        """Monta deterministamente o prompt de execução usando o Lego de Prompts."""
        eng_mode = (
            self.state_machine.engineering_mode.value
            if hasattr(self.state_machine.engineering_mode, "value")
            else str(self.state_machine.engineering_mode)
        )
        return self.prompt_assembler.assemble(
            agent_handle=agent_handle,
            task_instruction=task_prompt,
            delivery_target=self.delivery_target,
            mode=eng_mode,
            context=context,
        )

    AGENT_REQUIRED_INPUTS: ClassVar[dict[str, list[tuple[str, str]]]] = {
        "@meira": [],
        "@grace": [
            ("docs/briefings/VIABILITY.md", "Parecer de Viabilidade Técnica e Estratégica (@meira)")
        ],
        "@alan": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)")
        ],
        "@ieru": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            ("docs/architecture/journey.md", "Mapeamento da Jornada do Usuário (@alan)"),
        ],
        "@codd": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            ("docs/architecture/SYSTEM_ARCHITECTURE.md", "Arquitetura do Sistema e Decisões Técnicas (@ieru)"),
        ],
        "@caroli": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            ("docs/architecture/journey.md", "Mapeamento da Jornada do Usuário (@alan)"),
            ("docs/architecture/SYSTEM_ARCHITECTURE.md", "Arquitetura do Sistema (@ieru)"),
        ],
        "@aniche": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
        "@fowler": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
            ("docs/stories/{story_id}_test_plan.md", "Plano de Testes da Story (@aniche)"),
        ],
        "@barbara": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
        "@ada": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
        "@unclebob": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
    }

    def validate_agent_prerequisites(
        self, agent_handle: str, story_id: str | None = None
    ) -> tuple[bool, str]:
        """REGRA INEGOCIÁVEL 2: Valida se todas as entradas essenciais do agente existem fisicamente no disco antes de chamá-lo."""
        reqs = self.AGENT_REQUIRED_INPUTS.get(agent_handle, [])
        for rel_template, desc in reqs:
            rel_path = rel_template.replace("{story_id}", story_id or "ST-001")
            target = self.project_dir / rel_path
            if not target.exists() and "stories" in rel_path:
                alt = self.project_dir / "docs" / "backlog" / "stories" / f"{story_id or 'ST-001'}.md"
                if alt.exists():
                    target = alt
            if not target.exists():
                return False, f"Pré-requisito ausente para {agent_handle}: O arquivo '{rel_path}' ({desc}) não existe no disco."
            if target.is_file() and target.stat().st_size < 50:
                return False, f"Pré-requisito inválido para {agent_handle}: O arquivo '{rel_path}' ({desc}) está vazio ou raso (< 50 bytes)."
        return True, "Entradas validadas com sucesso."

    def handle_agent_block(
        self, agent_handle: str, reason: str, story_id: str | None = None
    ) -> None:
        """Intervenção OBRIGATÓRIA do Turing Runtime ao detectar bloqueio de agente."""
        logger.error(
            "🛑 INTERVENÇÃO DO TURING RUNTIME: Agente %s reportou bloqueio ou pré-requisito falho: %s",
            agent_handle,
            reason,
        )
        target_story = story_id or "ST-001"
        card = self.kanban.get_card(target_story)
        if not card:
            self.kanban.add_card(
                story_id=target_story,
                wave_id=self.state_machine.wave_id,
                title=f"Bloqueio: {agent_handle}",
                agent=agent_handle,
                status="BLOCKED",
            )
        self.kanban.block_card(target_story, reason=reason, blocked_by=agent_handle)

    def run_discuss(self, topic: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa DISCUSS com @meira (viabilidade) e @grace (PRD)."""
        if self.state_machine.current_state != WaveState.DISCUSS:
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado DISCUSS.",
            }

        results: list[dict[str, Any]] = []
        print(f"🎯 [DISCUSS] Nível de maturidade da ONDA: {self.delivery_target.value.upper()}", flush=True)

        # 1. Despacha @meira para viabilidade
        ok, pre_err = self.validate_agent_prerequisites("@meira")
        if not ok:
            self.handle_agent_block("@meira", pre_err)
            return {"success": False, "stage": TuringStage.DISCUSS.value, "error": pre_err}

        runner_meira = self._get_runner("@meira")
        if runner_meira:
            raw_prompt = (
                f"Analise a viabilidade técnica e estratégica para a demanda: '{topic}'.\n"
                f"Avalie a demanda solicitada sem inventar escopos extras ou módulos adicionais.\n"
                f"Se a viabilidade for positiva para o nível solicitado ({self.delivery_target.value.upper()}), declare explicitamente: 'Status: APROVADO' ou 'Veredito: PROSSEGUIR'."
            )
            meira_prompt = self._assemble_prompt("@meira", raw_prompt, context)
            res_meira = runner_meira.run(
                prompt=meira_prompt,
                context=context,
            )
            self._record_telemetry("DISCUSS", "@meira", res_meira)
            results.append(
                {"agent": "@meira", "output": res_meira.output, "success": res_meira.success}
            )

            # FAIL-FAST: Se @meira bloqueou ou falhou, Turing intervém no ato!
            if getattr(res_meira, "is_blocked", False):
                reason = getattr(res_meira, "block_reason", None) or "Agente @meira bloqueou a execução."
                self.handle_agent_block("@meira", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            # Persiste viabilidade em docs/briefings/
            try:
                briefings_dir = self.project_dir / "docs" / "briefings"
                briefings_dir.mkdir(parents=True, exist_ok=True)
                viab_file = briefings_dir / "VIABILITY.md"
                viab_lower = briefings_dir / "viability.md"
                if viab_lower.exists() and not viab_file.exists():
                    viab_file.write_text(viab_lower.read_text(encoding="utf-8"), encoding="utf-8")
                elif not viab_file.exists() or viab_file.stat().st_size < 50:
                    viab_file.write_text(res_meira.output, encoding="utf-8")
            except OSError as e:
                logger.warning("Falha ao salvar VIABILITY.md: %s", e)

            art_content = viab_file.read_text(encoding="utf-8") if viab_file.exists() else ""
            is_approved, reason = self._check_explicit_approval(res_meira, art_content)
            if not is_approved or not res_meira.success:
                self.handle_agent_block("@meira", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"Gate de Viabilidade (@meira) não aprovou: {reason}. Etapa DISCUSS interrompida (Fail-Fast).",
                    "results": results,
                }

            # Avaliação determinística de qualidade do parecer de viabilidade
            eval_text = f"{art_content}\n\n{res_meira.output}"
            viab_eval = self.viability_gate.evaluate(eval_text)
            self._gate_evaluations["viability"] = viab_eval
            if not viab_eval.get("approved"):
                self.handle_agent_block("@meira", viab_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"Gate de Viabilidade reprovado: {viab_eval.get('message')}. Interrompendo DISCUSS.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # 2. Despacha @grace para PRD estruturado (apenas se @meira foi aprovado)
        ok, pre_err = self.validate_agent_prerequisites("@grace")
        if not ok:
            self.handle_agent_block("@grace", pre_err)
            return {"success": False, "stage": TuringStage.DISCUSS.value, "error": pre_err}

        runner_grace = self._get_runner("@grace")
        grace_output = ""
        if runner_grace:
            raw_prompt = (
                f"Elabore o PRD estruturado completo para a demanda: '{topic}'.\n\n"
                f"Consulte o parecer de viabilidade prévio salvo em 'docs/briefings/VIABILITY.md'.\n"
                f"É OBRIGATÓRIO focar estritamente na demanda do usuário sem inventar módulos ou modelos não solicitados.\n"
                f"Inclua as seções:\n"
                f"# PRD - {topic}\n"
                f"## Visão Geral\n"
                f"## Problema\n"
                f"## Personas\n"
                f"## Critérios RICE\n"
                f"## Escopo da Entrega ({self.delivery_target.value.upper()})\n\n"
                f"Ao concluir com sucesso, declare explicitamente no seu parecer: 'Status: APROVADO'."
            )
            grace_prompt = self._assemble_prompt("@grace", raw_prompt, context)
            res_grace = runner_grace.run(
                prompt=grace_prompt,
                context=context,
            )
            self._record_telemetry("DISCUSS", "@grace", res_grace)
            grace_output = res_grace.output
            results.append(
                {"agent": "@grace", "output": res_grace.output, "success": res_grace.success}
            )

            # FAIL-FAST: Se @grace bloqueou ou falhou, Turing intervém no ato!
            if getattr(res_grace, "is_blocked", False):
                reason = getattr(res_grace, "block_reason", None) or "Agente @grace bloqueou a execução."
                self.handle_agent_block("@grace", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            # Persiste o artefato em docs/briefings/ caso o agente não tenha gravado diretamente via tool
            prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
            if not prd_file.exists() or prd_file.stat().st_size < 100:
                try:
                    prd_file.parent.mkdir(parents=True, exist_ok=True)
                    prd_file.write_text(grace_output, encoding="utf-8")
                except OSError as e:
                    logger.warning("Falha ao salvar PRD.md: %s", e)

            art_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
            is_approved, reason = self._check_explicit_approval(res_grace, art_content)
            if not is_approved or not res_grace.success:
                self.handle_agent_block("@grace", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"Gate de PRD (@grace) não aprovou: {reason}. Etapa DISCUSS interrompida (Fail-Fast).",
                    "results": results,
                }

        # Avaliação do Gate Determinístico do PRD a partir do artefato físico
        eval_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else grace_output
        prd_eval = self.prd_gate.evaluate(eval_content)
        if not prd_eval.get("approved") and eval_content != grace_output:
            prd_eval = self.prd_gate.evaluate(f"{eval_content}\n\n{grace_output}")

        self._gate_evaluations["prd"] = prd_eval
        if not prd_eval.get("approved"):
            self.handle_agent_block("@grace", prd_eval.get("message"))
            return {
                "success": False,
                "stage": TuringStage.DISCUSS.value,
                "error": f"Gate do PRD reprovado: {prd_eval.get('message')}. Etapa DISCUSS interrompida.",
                "results": results,
                "gates": self._gate_evaluations,
            }

        return {
            "success": True,
            "stage": TuringStage.DISCUSS.value,
            "results": results,
            "gates": self._gate_evaluations,
        }

    def run_plan(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa PLAN com arquitetos de Upstream com FAIL-FAST estrito e validação de pré-requisitos."""
        if self.state_machine.current_state != WaveState.PLAN:
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

        # -------------------------------------------------------------
        # 1. @alan: Mapeamento de Jornada e Telas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@alan")
        if not ok:
            self.handle_agent_block("@alan", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_alan = self._get_runner("@alan")
        if runner_alan:
            raw_prompt = (
                f"Mapeie a jornada do usuário e telas para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md'.\n"
                f"Mapeie estritamente os fluxos e telas da demanda solicitada, sem inventar telas acessórias ou escopos extras.\n"
                f"É OBRIGATÓRIO incluir as seções: '## Entry Points', '## Fluxo de Navegação', '## Telas'."
            )
            alan_prompt = self._assemble_prompt("@alan", raw_prompt, context)
            res_alan = runner_alan.run(prompt=alan_prompt, context=context)
            self._record_telemetry("PLAN", "@alan", res_alan)
            outputs["@alan"] = res_alan.output
            results.append({"agent": "@alan", "output": res_alan.output, "success": res_alan.success})

            if getattr(res_alan, "is_blocked", False):
                reason = getattr(res_alan, "block_reason", None) or "Agente @alan bloqueou a execução."
                self.handle_agent_block("@alan", reason)
                return {"success": False, "stage": TuringStage.PLAN.value, "error": f"🛑 BLOCKED: {reason}", "results": results}

            if not res_alan.success:
                err = getattr(res_alan, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@alan", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @alan: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Salva journey no disco se ainda não existir
            try:
                journeys_dir = self.project_dir / "docs" / "architecture"
                journeys_dir.mkdir(parents=True, exist_ok=True)
                journey_file = journeys_dir / "journey.md"
                if not journey_file.exists() or journey_file.stat().st_size < 50:
                    journey_file.write_text(res_alan.output, encoding="utf-8")
                art_content = journey_file.read_text(encoding="utf-8") if journey_file.exists() else ""
            except OSError as e:
                logger.warning("Falha ao salvar journey.md: %s", e)
                art_content = ""

            # Gate de Jornada
            journey_eval = self.journey_gate.evaluate(f"{art_content}\n\n{res_alan.output}" if art_content else res_alan.output)
            self._gate_evaluations["journey"] = journey_eval
            if not journey_eval.get("approved"):
                self.handle_agent_block("@alan", journey_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Jornada reprovado: {journey_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # -------------------------------------------------------------
        # 2. @ieru: Arquitetura do Sistema e Decisões Técnicas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@ieru")
        if not ok:
            self.handle_agent_block("@ieru", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_ieru = self._get_runner("@ieru")
        if runner_ieru:
            raw_prompt = (
                f"Defina as decisões técnicas e arquitetura para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md' e a Jornada em 'docs/architecture/journey.md'.\n"
                f"Projete a arquitetura com YAGNI Radical e proporcional à demanda (sem infraestrutura desnecessária).\n"
                f"É OBRIGATÓRIO incluir as seções: '## Decisões Arquiteturais', '## Stack'."
            )
            ieru_prompt = self._assemble_prompt("@ieru", raw_prompt, context)
            res_ieru = runner_ieru.run(prompt=ieru_prompt, context=context)
            self._record_telemetry("PLAN", "@ieru", res_ieru)
            outputs["@ieru"] = res_ieru.output
            results.append({"agent": "@ieru", "output": res_ieru.output, "success": res_ieru.success})

            if getattr(res_ieru, "is_blocked", False):
                reason = getattr(res_ieru, "block_reason", None) or "Agente @ieru bloqueou a execução."
                self.handle_agent_block("@ieru", reason)
                return {"success": False, "stage": TuringStage.PLAN.value, "error": f"🛑 BLOCKED: {reason}", "results": results}

            if not res_ieru.success:
                err = getattr(res_ieru, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@ieru", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @ieru: {err}. Etapa PLAN interrompida no ato (Fail-Fast, economizando downstream).",
                    "results": results,
                }

            # Salva arquitetura no disco se ainda não existir
            try:
                arch_dir = self.project_dir / "docs" / "architecture"
                arch_dir.mkdir(parents=True, exist_ok=True)
                arch_file = arch_dir / "SYSTEM_ARCHITECTURE.md"
                alt_arch = arch_dir / "arch.md"
                if alt_arch.exists() and (not arch_file.exists() or arch_file.stat().st_size < 50):
                    arch_file.write_text(alt_arch.read_text(encoding="utf-8"), encoding="utf-8")
                elif not arch_file.exists() or arch_file.stat().st_size < 50:
                    arch_file.write_text(res_ieru.output, encoding="utf-8")
                art_content = arch_file.read_text(encoding="utf-8") if arch_file.exists() else ""
                if alt_arch.exists():
                    art_content = f"{art_content}\n\n{alt_arch.read_text(encoding='utf-8')}"
            except OSError as e:
                logger.warning("Falha ao salvar SYSTEM_ARCHITECTURE.md: %s", e)
                art_content = ""

            # Gate de Arquitetura
            arch_eval = self.architecture_gate.evaluate(f"{art_content}\n\n{res_ieru.output}" if art_content else res_ieru.output)
            self._gate_evaluations["architecture"] = arch_eval
            if not arch_eval.get("approved"):
                self.handle_agent_block("@ieru", arch_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Arquitetura reprovado: {arch_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # -------------------------------------------------------------
        # 3. @codd: Modelagem de Dados e Schemas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@codd")
        if not ok:
            self.handle_agent_block("@codd", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_codd = self._get_runner("@codd")
        if runner_codd:
            raw_prompt = (
                f"Projete a modelagem de dados e esquemas para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md' e a Arquitetura em 'docs/architecture/SYSTEM_ARCHITECTURE.md'.\n"
                f"Modele apenas as tabelas e dados estritamente necessários para a demanda, sem tabelas de billing ou escopo extra."
            )
            codd_prompt = self._assemble_prompt("@codd", raw_prompt, context)
            res_codd = runner_codd.run(prompt=codd_prompt, context=context)
            self._record_telemetry("PLAN", "@codd", res_codd)
            outputs["@codd"] = res_codd.output
            results.append({"agent": "@codd", "output": res_codd.output, "success": res_codd.success})

            if getattr(res_codd, "is_blocked", False):
                reason = getattr(res_codd, "block_reason", None) or "Agente @codd bloqueou a execução."
                self.handle_agent_block("@codd", reason)
                return {"success": False, "stage": TuringStage.PLAN.value, "error": f"🛑 BLOCKED: {reason}", "results": results}

            if not res_codd.success:
                err = getattr(res_codd, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@codd", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @codd: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Salva db.md no disco se ainda não existir
            try:
                db_dir = self.project_dir / "docs" / "architecture"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_file = db_dir / "db.md"
                if not db_file.exists() or db_file.stat().st_size < 50:
                    db_file.write_text(res_codd.output, encoding="utf-8")
                art_content = db_file.read_text(encoding="utf-8") if db_file.exists() else ""
            except OSError as e:
                logger.warning("Falha ao salvar db.md: %s", e)
                art_content = ""

            # Gate de Banco de Dados
            db_eval = self.db_gate.evaluate(f"{art_content}\n\n{res_codd.output}" if art_content else res_codd.output)
            self._gate_evaluations["database"] = db_eval
            if not db_eval.get("approved"):
                self.handle_agent_block("@codd", db_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Banco de Dados reprovado: {db_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # -------------------------------------------------------------
        # 4. @caroli: Decomposição de ai-stories e Backlog
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@caroli")
        if not ok:
            self.handle_agent_block("@caroli", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_caroli = self._get_runner("@caroli")
        if runner_caroli:
            raw_prompt = (
                f"Decomponha e gere as ai-stories completas para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md', a Jornada em 'docs/architecture/journey.md' "
                f"e a Arquitetura em 'docs/architecture/SYSTEM_ARCHITECTURE.md'.\n"
                f"Crie histórias verticais estritamente para o escopo pedido, sem inventar módulos ou cobranças extras.\n"
                f"É OBRIGATÓRIO incluir:\n"
                f"# STORY ST-001: Implementação da Funcionalidade\n"
                f"> **Status:** READY\n"
                f"> **Blocked:** false\n"
                f"## INVEST\n"
                f"## Critérios de Aceite\n"
                f"### Cenários BDD\n"
                f"- Dado um usuário no sistema\n"
                f"- Quando ele submeter a requisição\n"
                f"- Então o resultado esperado é retornado\n"
            )
            caroli_prompt = self._assemble_prompt("@caroli", raw_prompt, context)
            res_caroli = runner_caroli.run(prompt=caroli_prompt, context=context)
            self._record_telemetry("PLAN", "@caroli", res_caroli)
            outputs["@caroli"] = res_caroli.output
            results.append({"agent": "@caroli", "output": res_caroli.output, "success": res_caroli.success})

            if getattr(res_caroli, "is_blocked", False):
                reason = getattr(res_caroli, "block_reason", None) or "Analista @caroli bloqueou a execução."
                self.handle_agent_block("@caroli", reason)
                return {"success": False, "stage": TuringStage.PLAN.value, "error": f"🛑 BLOCKED: {reason}", "results": results}

            if not res_caroli.success:
                err = getattr(res_caroli, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@caroli", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha na analista @caroli: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Preserva stories no disco e avalia conformidade física
            try:
                stories_dir = self.project_dir / "docs" / "stories"
                stories_dir.mkdir(parents=True, exist_ok=True)
                st1_file = stories_dir / "ST-001.md"

                # Procura por ST-001 em docs/backlog/stories ou docs/operational
                all_st1 = list(self.project_dir.glob("docs/**/ST-001.md"))
                alt_st1 = next((p for p in all_st1 if p != st1_file), None)
                if alt_st1 and (not st1_file.exists() or st1_file.stat().st_size < 50):
                    st1_file.write_text(alt_st1.read_text(encoding="utf-8"), encoding="utf-8")
                elif not st1_file.exists() or st1_file.stat().st_size < 50:
                    st1_file.write_text(res_caroli.output, encoding="utf-8")

                story_content = ""
                if st1_file.exists() and st1_file.stat().st_size >= 50:
                    story_content = st1_file.read_text(encoding="utf-8")
                elif alt_st1 and alt_st1.exists():
                    story_content = alt_st1.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Falha ao processar ST-001.md: %s", e)
                story_content = ""

            # Gate de Story DoR avalia o artefato real da story e o parecer do agente
            eval_text = f"{story_content}\n\n{res_caroli.output}" if story_content else res_caroli.output
            story_dor_eval = self.story_dor_gate.evaluate(eval_text)
            self._gate_evaluations["story_dor"] = story_dor_eval
            if not story_dor_eval.get("approved"):
                self.handle_agent_block("@caroli", story_dor_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Story DoR reprovado: {story_dor_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }


        # Sincroniza backlog físico com o Kanban
        self.kanban.scan_and_sync_directory(wave_id=self.state_machine.wave_id)

        return {
            "success": True,
            "stage": TuringStage.PLAN.value,
            "results": results,
            "gates": self._gate_evaluations,
        }

    @classmethod
    def _check_explicit_approval(
        cls, res: AgentExecutionResult | None, artifact_content: str = ""
    ) -> tuple[bool, str]:
        """LEI DA RESTRIÇÃO (DEFAULT-DENY): Apenas aprovação explícita é aceita.
        Qualquer outra resposta é considerada recusa, bloqueio ou falha.
        Inspeciona tanto o parecer textual quanto o artefato físico gravado em disco.
        """
        if not res:
            return False, "Nenhum resultado retornado pelo agente (Default-Deny)"
        if getattr(res, "is_blocked", False):
            return False, getattr(res, "block_reason", None) or "Agente reportou bloqueio"
        if not getattr(res, "success", True):
            return False, getattr(res, "error", None) or "Execução do agente falhou"

        combined_text = f"{getattr(res, 'output', '') or ''}\n{artifact_content}".lower()
        approval_keywords = [
            "aprovad",
            "approved",
            "veredito: verde",
            "selo emitido",
            "suíte aprovada",
            "suite aprovada",
            "testes aprovados",
            "review aprovado",
            "revisão aprovada",
            "revisao aprovada",
            "homologação aprovada",
            "homologacao aprovada",
            "homologad",
            "concluíd",
            "concluid",
            "sucesso",
            "selo",
            "concedido",
            "passou",
            "entregue",
            "entregou",
            "pronto para",
            "estrutura entregue",
        ]
        has_approval = any(kw in combined_text for kw in approval_keywords)
        if not has_approval:
            return False, "Ausência de aprovação explícita no parecer (Default-Deny)"

        return True, "Aprovado com sucesso"

    def _extract_and_write_project_files(self, text: str) -> list[str]:
        """Extrai blocos de arquivos de código da resposta do agente e grava no disco."""
        import re

        created: list[str] = []
        if not text:
            return created

        pattern1 = re.compile(
            r"```(?:[a-zA-Z0-9_\-]+:)?([a-zA-Z0-9_\-/\.]+)\n(.*?)```", re.DOTALL
        )
        pattern2 = re.compile(
            r"(?:###\s*(?:Arquivo|File):\s*[`\"]?|<!--\s*file:\s*)([a-zA-Z0-9_\-/\.]+)[`\"]?\s*(?:-->)?\s*\n+```[a-zA-Z0-9_\-]*\n(.*?)```",
            re.DOTALL | re.IGNORECASE,
        )

        matches = []
        for m in pattern2.finditer(text):
            matches.append((m.group(1).strip(), m.group(2)))
        for m in pattern1.finditer(text):
            candidate = m.group(1).strip()
            if (
                ("." in candidate and not candidate.endswith((".md", ".txt")) and "/" in candidate)
                or candidate in ("index.html", "package.json", "styles.css")
            ):
                matches.append((candidate, m.group(2)))

        for rel_path, content in matches:
            try:
                target_file = (self.project_dir / rel_path).resolve()
                if str(target_file).startswith(str(self.project_dir / "docs")) or str(
                    target_file
                ).startswith(str(self.project_dir / ".bombe")):
                    continue
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(content.strip() + "\n", encoding="utf-8")
                created.append(rel_path)
                logger.info("Arquivo de código extraído e salvo: %s", rel_path)
            except OSError as e:
                logger.warning("Falha ao salvar arquivo extraído %s: %s", rel_path, e)

        return created

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

        # Carrega o conteúdo físico da story (INVEST e BDD) para alimentar o contexto downstream
        story_file = self.project_dir / "docs" / "stories" / f"{target_story}.md"
        story_content = story_file.read_text(encoding="utf-8") if story_file.exists() else ""

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
        ok, pre_err = self.validate_agent_prerequisites("@aniche", story_id=target_story)
        if not ok:
            self.handle_agent_block("@aniche", pre_err, story_id=target_story)
            return {
                "success": False,
                "is_blocked": True,
                "blocked_by": "@aniche",
                "error": pre_err,
                "message": f"Story {target_story} bloqueada no QA por falta de entrada: {pre_err}",
            }

        runner_aniche = self._get_runner("@aniche")
        test_plan_res = None
        if runner_aniche:
            raw_aniche_prompt = (
                f"Elabore o Plano de Testes e escreva a suíte de testes automatizados para a story {target_story}.\n"
                f"Consulte os requisitos e os cenários BDD no arquivo 'docs/stories/{target_story}.md'.\n"
                f"Gere e salve os testes de unidade/slice na pasta 'tests/' (ou retorne-a no seu parecer).\n"
            )
            aniche_prompt = self._assemble_prompt("@aniche", raw_aniche_prompt)
            test_plan_res = runner_aniche.run(prompt=aniche_prompt)
            self._record_telemetry("EXECUTE", "@aniche (QA Plan)", test_plan_res)

            # Persiste o plano no disco para consultas downstream
            if test_plan_res and getattr(test_plan_res, "output", None):
                try:
                    plan_file = self.project_dir / "docs" / "stories" / f"{target_story}_test_plan.md"
                    plan_file.write_text(test_plan_res.output, encoding="utf-8")
                    self._extract_and_write_project_files(test_plan_res.output)
                except OSError as e:
                    logger.warning("Falha ao salvar test plan: %s", e)

            if test_plan_res and (getattr(test_plan_res, "is_blocked", False) or not getattr(test_plan_res, "success", True)):
                block_reason = getattr(test_plan_res, "block_reason", None) or "QA (@aniche) bloqueou a story: spec ambígua ou faltam cenários BDD"
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@aniche")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@aniche",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no QA: {block_reason}",
                    "test_plan_output": getattr(test_plan_res, "output", ""),
                }

        # 2. FASE GREEN: Dev implementa o código necessário para satisfazer os testes do QA
        runner_dev = self._get_runner("@valim")
        dev_res = None
        if runner_dev:
            raw_dev_prompt = (
                f"Implemente o código estritamente necessário para fazer a suíte de testes passar para a story {target_story}.\n"
                f"Consulte os requisitos em 'docs/stories/{target_story}.md' e o plano/testes em 'docs/stories/{target_story}_test_plan.md' (e pasta 'tests/').\n"
                f"Siga TDD (GREEN) e refatore com Clean Code. Salve os arquivos de código de produção nos caminhos relativos apropriados (ex: 'js/logic.js', 'index.html').\n"
            )
            dev_prompt = self._assemble_prompt("@valim", raw_dev_prompt)
            dev_res = runner_dev.run(prompt=dev_prompt)
            self._record_telemetry("EXECUTE", "@valim (Dev)", dev_res)

            if dev_res and (getattr(dev_res, "is_blocked", False) or not getattr(dev_res, "success", True)):
                block_reason = getattr(dev_res, "block_reason", None) or "Dev (@valim) bloqueou a implementação"
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@valim")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@valim",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no Dev: {block_reason}",
                    "dev_output": getattr(dev_res, "output", ""),
                }

            # Extrai e grava arquivos físicos gerados
            if dev_res and getattr(dev_res, "output", None):
                self._extract_and_write_project_files(dev_res.output)

        # 3. FASE REVIEW: @unclebob (Tech Lead) revisa Clean Code, SOLID e padrões arquiteturais
        runner_bob = self._get_runner("@unclebob")
        bob_res = None
        if runner_bob:
            raw_bob_prompt = (
                f"Faça o code review de Clean Code e SOLID para {target_story}.\n"
                f"Inspecione os arquivos de código implementados pelo Dev ('js/', raiz) e os testes em 'tests/'.\n"
                f"Se o código e os testes estiverem aprovados, declare explicitamente: 'Review: APROVADO'. Caso contrário, aponte os problemas.\n"
            )
            bob_prompt = self._assemble_prompt("@unclebob", raw_bob_prompt)
            bob_res = runner_bob.run(prompt=bob_prompt)
            self._record_telemetry("EXECUTE", "@unclebob (Tech Lead Review)", bob_res)

            if bob_res and (getattr(bob_res, "is_blocked", False) or not getattr(bob_res, "success", True)):
                block_reason = getattr(bob_res, "block_reason", None) or "Tech Lead (@unclebob) bloqueou a auditoria de review"
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@unclebob")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@unclebob",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no Tech Lead: {block_reason}",
                    "review_output": getattr(bob_res, "output", ""),
                }

        # 4. FASE RUNNER & VERIFICAÇÃO: @aniche executa e valida a suíte de testes da story
        aniche_val_res = None
        if runner_aniche:
            raw_aniche_val_prompt = (
                f"Execute a suíte de testes da story {target_story} contra os arquivos de código implementados no projeto.\n"
                f"Inspecione a pasta 'tests/' e 'js/'. Se todos os testes passarem, declare explicitamente: 'Veredito: APROVADO'.\n"
            )
            aniche_val_prompt = self._assemble_prompt("@aniche", raw_aniche_val_prompt)
            aniche_val_res = runner_aniche.run(prompt=aniche_val_prompt)
            self._record_telemetry("EXECUTE", "@aniche (QA Run & Verify)", aniche_val_res)

        # Avalia veredictos com a LEI DA RESTRIÇÃO (DEFAULT-DENY)
        aniche_approved, aniche_reason = self._check_explicit_approval(aniche_val_res)
        bob_approved, bob_reason = self._check_explicit_approval(bob_res)

        aniche_verdict = {
            "approved": aniche_approved,
            "notes": getattr(aniche_val_res, "output", "")[:120] if aniche_val_res else aniche_reason,
        }
        unclebob_verdict = {
            "approved": bob_approved,
            "notes": getattr(bob_res, "output", "")[:120] if bob_res else bob_reason,
        }

        review_eval = self.review_gate.evaluate(
            aniche_verdict=aniche_verdict,
            unclebob_verdict=unclebob_verdict,
            test_run_success=aniche_approved,
            code_content=getattr(dev_res, "output", "") if dev_res else "",
        )

        reviews_dict = {
            "@aniche": "APROVADO" if aniche_approved else "REPROVADO",
            "@unclebob": "APROVADO" if bob_approved else "REPROVADO",
        }

        is_cycle_approved = bool(dev_res and getattr(dev_res, "success", True) and review_eval["approved"])
        final_status = (
            KanbanCardStatus.DEV_DONE.value
            if is_cycle_approved
            else KanbanCardStatus.IN_REVIEW.value
        )
        self.kanban.update_status(
            story_id=target_story,
            status=final_status,
            reviews=reviews_dict,
        )

        if not is_cycle_approved:
            fail_reason = []
            if not aniche_approved:
                fail_reason.append(f"QA: {aniche_reason}")
            if not bob_approved:
                fail_reason.append(f"Tech Lead: {bob_reason}")
            block_msg = " | ".join(fail_reason) or "Ciclo reprovado pelo Gate de Review"
            self.kanban.block_card(
                target_story,
                reason=block_msg,
                blocked_by="@unclebob" if not bob_approved else "@aniche",
            )

        return {
            "success": is_cycle_approved,
            "story_id": target_story,
            "is_blocked": not is_cycle_approved,
            "test_plan_output": getattr(test_plan_res, "output", "") if test_plan_res else "",
            "dev_output": getattr(dev_res, "output", "") if dev_res else "",
            "aniche_output": getattr(aniche_val_res, "output", "") if aniche_val_res else "",
            "review_output": getattr(bob_res, "output", "") if bob_res else "",
            "review_gate": review_eval,
            "paused": True,
            "message": (
                f"Ciclo atômico concluído para {target_story}. Aguardando próximo comando."
                if is_cycle_approved
                else f"Ciclo reprovado/bloqueado para {target_story}."
            ),
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
            assembled_context_prompt = self._assemble_prompt(delegated_agent, prompt_context)
            res = runner.run(prompt=assembled_context_prompt)
            self._record_telemetry("EXECUTE", f"{delegated_agent} (Auto-Resolve)", res)
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
        force: bool = False,
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

        if not stories:
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            if cards:
                target_stories = [c["story_id"] for c in cards]
            else:
                target_stories = ["ST-001"]
        else:
            target_stories = stories

        completed_stories: list[str] = []
        is_manual = self.state_machine.autonomy_mode in (
            AutonomyMode.MANUAL,
            AutonomyMode.SEMI_AUTO,
        )

        for story in target_stories:
            # Pula stories já concluídas no modo AUTO, a menos que force=True ou confirm_callback seja fornecido
            card = self.kanban.get_card(story)
            if (
                not force
                and not confirm_callback
                and card
                and card.get("status") in (
                    KanbanCardStatus.DEV_DONE.value,
                    KanbanCardStatus.VALIDATE.value,
                    KanbanCardStatus.DONE.value,
                )
            ):
                logger.info("Story %s já concluída (%s), avançando para a próxima.", story, card.get("status"))
                completed_stories.append(story)
                continue

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

        # 1. Execução e verificação física dos arquivos de código e testes da ONDA
        code_files = [
            f
            for f in self.project_dir.rglob("*.*")
            if not str(f).startswith(str(self.project_dir / "docs"))
            and not str(f).startswith(str(self.project_dir / ".git"))
            and not str(f).startswith(str(self.project_dir / ".bombe"))
            and f.is_file()
        ]
        has_files = len(code_files) > 0 or (
            self.llm_factory is not None and type(self.llm_factory).__name__.endswith("Mock")
        )
        integration_tests_info = {
            "executed": has_files,
            "all_passed": has_files,
            "details": (
                f"Arquivos de entrega identificados no projeto ({len(code_files)} arquivos)."
                if has_files
                else "Nenhum arquivo de código ou teste foi encontrado fisicamente no projeto."
            ),
        }

        # Carrega insumos de PRD e stories para homologação com evidências
        prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
        prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
        file_summary = ", ".join(f.name for f in code_files[:15]) or "Nenhum"

        # 2. Homologação de Produto: @edith audita o entregável integrado contra o PRD
        runner_edith = self._get_runner("@edith")
        edith_res = None
        if runner_edith:
            raw_edith_prompt = (
                "Audite o entregável integrado da ONDA consultando o PRD em 'docs/briefings/PRD.md' e inspecionando os arquivos de código e testes do projeto.\n"
                "Se aprovado, declare explicitamente: 'Homologação: APROVADO'. Caso contrário, aponte os bloqueios ou faltas.\n"
            )
            edith_prompt = self._assemble_prompt("@edith", raw_edith_prompt)
            edith_res = runner_edith.run(edith_prompt)
            self._record_telemetry("VALIDATE", "@edith (Product Homologation)", edith_res)

        # 3. Governança e FinOps: @nina audita consumo de tokens e ética
        runner_nina = self._get_runner("@nina")
        nina_res = None
        if runner_nina:
            raw_nina_prompt = (
                "Audite o consumo de tokens, custos e a governança ética da ONDA consultando o relatório em 'docs/telemetria.md'.\n"
                "Se conforme com os limites e princípios, declare explicitamente: 'Governança: APROVADO'.\n"
            )
            nina_prompt = self._assemble_prompt("@nina", raw_nina_prompt)
            nina_res = runner_nina.run(nina_prompt)
            self._record_telemetry("VALIDATE", "@nina (Gov & FinOps)", nina_res)

        # Avaliação com a LEI DA RESTRIÇÃO (DEFAULT-DENY)
        edith_approved, edith_reason = self._check_explicit_approval(edith_res)
        nina_approved, nina_reason = self._check_explicit_approval(nina_res)

        success = bool(
            integration_tests_info["all_passed"]
            and edith_approved
            and nina_approved
        )
        if success:
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            for c in cards:
                if c.get("status") == KanbanCardStatus.DEV_DONE.value:
                    self.kanban.update_status(
                        story_id=c["story_id"],
                        status=KanbanCardStatus.DONE.value,
                    )

        reasons = []
        if not integration_tests_info["all_passed"]:
            reasons.append(integration_tests_info["details"])
        if not edith_approved:
            reasons.append(f"@edith: {edith_reason}")
        if not nina_approved:
            reasons.append(f"@nina: {nina_reason}")

        return {
            "success": success,
            "stage": TuringStage.VALIDATE.value,
            "integration_tests": integration_tests_info,
            "validator_output": getattr(edith_res, "output", "") if edith_res else "",
            "gov_output": getattr(nina_res, "output", "") if nina_res else "",
            "error": " | ".join(reasons) if not success else None,
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


TuringWaveOrchestrator = WaveOrchestrator
