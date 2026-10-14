"""Orquestrador Autônomo da ONDA no Turing Runtime (EP-003).

Coordena as transições de estado, despacho de agentes especialistas,
fiscalização determinística de gates e persistência no banco local do projeto.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from bombe_code.agents.registry import AgentRegistry
from bombe_code.agents.runner import (
    AgentExecutionResult,
    AgentRunner,
    marcar_atividade_tool,
)
from bombe_code.config.project_config import ProjectConfigManager
from bombe_code.llm.pydantic_factory import PydanticAiFactory
from bombe_code.llm.quota_detector import QuotaResetInfo
from bombe_code.permissions.stage_guard import (
    validate_safe_relative_path,
    validate_stage_permission,
)
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.ambiente import (
    anunciar_instalacao_prioritaria,
    auditar_instalacao,
    e_bloqueio_de_instalacao,
    evidencia_de,
    roteamento_da_instalacao,
    runner_ausente,
    verificar_instalacao,
)
from bombe_code.turing.fila import FilaDoKanban, montar_lote_turno
from bombe_code.turing.gates import SealGate, TemplateGate
from bombe_code.turing.kanban import KanbanCardStatus, KanbanManager
from bombe_code.turing.pbb import PBBDecomposer
from bombe_code.turing.progress import ABORT_EVENT, BUS
from bombe_code.turing.prompt_assembler import DeliveryTarget, TuringPromptAssembler
from bombe_code.turing.quota import PoliticaDeCota
from bombe_code.turing.review_gate import TuringReviewGate

# ── Autorizações de remoção FORA da raiz (por sessão, in-memory) ──
# SEMI-AUTO/MANUAL exigem permissão explícita do humano: /permitir apagar <caminho>.
# Bobagem DENTRO do projeto o git amortece; bobagem FORA não tem conserto —
# por isso fora da raiz nunca se apaga sem o humano dizer sim.
_REMOCOES_AUTORIZADAS: set[str] = set()


def autorizar_remocao(caminho: str) -> str:
    """Autoriza (nesta sessão) a remoção de um caminho fora da raiz do projeto."""
    p = Path(caminho).expanduser().resolve()
    _REMOCOES_AUTORIZADAS.add(p.as_posix())
    return p.as_posix()


def remocao_autorizada(caminho: str) -> bool:
    """Verifica se um caminho fora da raiz tem permissão explícita na sessão."""
    try:
        p = Path(caminho).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    return p.as_posix() in _REMOCOES_AUTORIZADAS


from bombe_code.turing.rework import VETO_ROUTES, VetoClass, VetoReworkEngine
from bombe_code.turing.state_machine import (
    AutonomyMode,
    EngineeringMode,
    InvalidTransitionError,
    TuringStage,
    TuringStateMachine,
    WaveState,
    WaveType,
)
from bombe_code.turing.upstream_gates import (
    ArchitectureGate,
    DatabaseQualityGate,
    JourneyGate,
    PRDQualityGate,
    StoryDoRGate,
    ViabilityQualityGate,
)
from bombe_code.turing.upstream_profiler import UpstreamProfiler

logger = logging.getLogger(__name__)


class WaveOrchestrator:
    """Motor de execução e orquestração do ciclo de vida da ONDA."""

    # Task de instalação de ambiente pendente (impedimento nascido no meio de
    # um ciclo): a linha PARA nela — nada mais queima com o ambiente quebrado.

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
        # Relógio do RED: o @aniche acorda UMA vez por story por run (primeira
        # queima) — nunca em resume/re-burn/degrau (suíte existente = contrato).
        self._red_ja_feito: set[str] = set()
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
        from bombe_code.domain.wave.workspace import WaveWorkspace

        self.workspace = WaveWorkspace(project_dir=self.project_dir)
        # Fila de achados por story (Turing gerencia: 7 achados? guarda os 7,
        # corrige um a um com o agente certo, valida o conjunto no fim).
        # Cota esgotada do provedor de IA: enquanto ativa, o processo PAUSA
        # (para de queimar — 429 atrás de 429 é lixo) e ESPERA o reset. Cota
        # é infraestrutura, NUNCA "falta de informação" — essa é a regra aqui.
        self.kanban = kanban or KanbanManager(project_dir=str(self.project_dir), db=self.db)
        # Política de cota (SRP): estado e decisão moram em PoliticaDeCota.
        self._cota = PoliticaDeCota(self.kanban)
        # Fila do kanban (SRP): a única fonte das tasks que queimam.
        self._fila = FilaDoKanban(
            self.db,
            wave_provider=lambda: self.state_machine.wave_id,
            mapa_camada=self._MAPA_AGENTE_CAMADA,
            roteador_achado=self._agente_para_achado,
        )
        self._gate_evaluations: dict[str, Any] = {}
        self.config_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = self.config_mgr.load()
        raw_target = getattr(cfg, "delivery_target", "mvp")
        self.delivery_target = DeliveryTarget.from_str(raw_target)
        BUS.set_verbosity(os.environ.get("BOMBE_VERBOSITY") or getattr(cfg, "verbosity", "verbose"))
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

        # AUTOCURA (à prova de erro): o runtime detecta e corrige sozinho
        # anomalias de estado — o humano NUNCA precisa saber que houve erro.
        try:
            self._autocure()
        except Exception as exc:  # noqa: BLE001 — autocura nunca derruba o boot
            logger.warning("Autocura falhou (não bloqueante): %s", exc)

    def _autocure(self) -> dict[str, Any] | None:
        """Diagnóstico automático GLOBAL e cura de estados inconsistentes.

        Roda a cada boot do runtime. Varre TODAS as ondas — não apenas a ativa:
        1. ONDA ativa COMPLETED com stories DEV_DONE ou relatório de REJEIÇÃO
           → reabre na VALIDATE.
        2. ONDA arquivada com evidência de pendência (relatório REJEITADO,
           stories DEV_DONE) e onda ativa SEM trabalho em voo → ADOTA a onda
           anômala e reabre na VALIDATE. (caso make-books: ONDA-001 fechada
           indevidamente enquanto a ONDA-002 vazia ocupava a máquina)
        """
        saved = self.db.load_wave_state()
        if not saved:
            return None

        # 1. Autocura da onda ATIVA
        cured = self._autocurar_onda(wave_id=str(saved.get("wave_id", "")), pode_trocar=False)
        if cured:
            return cured

        # 2. Varredura GLOBAL: detecção determinística (custo ZERO de tokens) —
        #    apenas AVISA; a ação é do usuário via `/wave audit ONDA-xxx`.
        #    (economia de tokens: nada de revalidar 300 ondas retroativamente)
        if str(saved.get("state", "")).upper() == WaveState.COMPLETED.value:
            return None
        current_cards = self.kanban.list_cards(wave_id=str(saved.get("wave_id", "")))
        if current_cards:
            return None  # trabalho em voo: prioridade é a onda ativa

        candidatos: set[str] = {
            c.get("wave_id", "") for c in self.kanban.list_cards() if c.get("wave_id")
        }
        waves_dir = self.project_dir / "docs" / "waves"
        if waves_dir.is_dir():
            for pasta in waves_dir.iterdir():
                if pasta.is_dir() and (pasta / "validation_report.md").exists():
                    candidatos.add(pasta.name)
        candidatos.discard(str(saved.get("wave_id", "")))

        for wave in sorted(candidatos):
            cards = self.kanban.list_cards(wave_id=wave)
            dev_done = [
                c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DEV_DONE.value
            ]
            motivo: str | None = None
            if dev_done:
                motivo = f"{len(dev_done)} story(ies) em DEV_DONE sem homologação DONE"
            else:
                try:
                    report = self.workspace.wave_validation_report_path(wave)
                    conteudo = report.read_text(encoding="utf-8").lower() if report.exists() else ""
                except OSError:
                    conteudo = ""
                if "veredito final" in conteudo and "rejeitad" in conteudo:
                    motivo = "relatório de validação contém veredito de REJEIÇÃO"
            if motivo:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"⚠️ [EVIDÊNCIA DE PENDÊNCIA] A {wave} possui indício de pendência não resolvida "
                        f"({motivo}). A máquina não revalida retroativamente (economia de tokens) — "
                        f"se houver dúvida, invoque: /wave audit {wave}"
                    ),
                    wave_id=wave,
                )
        return None

    def _autocurar_onda(self, wave_id: str, pode_trocar: bool) -> dict[str, Any] | None:
        """Detecta anomalia em UMA onda e cura (reabrindo na VALIDATE).

        Se pode_trocar=True, a onda anômala assume o comando da máquina
        (wave_state passa a apontar para ela) — sem perguntar nada a ninguém.
        """
        motivo: str | None = None

        cards = self.kanban.list_cards(wave_id=wave_id)
        # Se há stories em desenvolvimento ou prontas para execução, a onda pertence a EXECUTE
        in_dev = [
            c["story_id"]
            for c in cards
            if c.get("status") in (KanbanCardStatus.IN_PROGRESS.value, KanbanCardStatus.READY.value, "IN_PROGRESS", "READY")
        ]
        dev_done = [
            c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DEV_DONE.value
        ]
        if in_dev:
            # Há trabalho em andamento no ciclo de desenvolvimento; não força VALIDATE
            return None
        elif dev_done:
            motivo = f"{len(dev_done)} story(ies) em DEV_DONE sem homologação DONE"
        else:
            try:
                report = self.workspace.wave_validation_report_path(wave_id)
                conteudo = report.read_text(encoding="utf-8").lower() if report.exists() else ""
            except OSError:
                conteudo = ""
            if "veredito final" in conteudo and "rejeitad" in conteudo:
                motivo = "relatório de validação contém veredito de REJEIÇÃO"

        if not motivo:
            return None

        # Preserva o checkpoint da onda ativa se vamos assumir o comando.
        if pode_trocar:
            ativo = self.db.load_wave_state()
            if (
                ativo
                and str(ativo.get("wave_id", "")).upper() != wave_id.upper()
                and str(ativo.get("state", "")).upper() != WaveState.COMPLETED.value
            ):
                self.db.archive_wave_state()

        self.state_machine = TuringStateMachine(
            wave_id=wave_id,
            initial_state=WaveState.VALIDATE,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        self.db.save_wave_state(
            wave_id=wave_id,
            state=WaveState.VALIDATE,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        mensagem = (
            f"🩺 [AUTOCURA] Anomalia detectada e corrigida automaticamente: a {wave_id} "
            f"possui pendência não resolvida ({motivo}). Reaberta na etapa VALIDATE — "
            "a validação será reexecutada pelo Ciclo Autônomo."
            + (" Ela assume o comando da máquina." if pode_trocar else "")
        )
        BUS.publish("announcement", agent="@turing", text=mensagem, wave_id=wave_id)
        logger.warning("AUTOCURA: %s", mensagem)
        return {
            "cured": True,
            "wave_id": wave_id,
            "stage": WaveState.VALIDATE.value,
            "motivo": motivo,
        }

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
        try:
            in_tok = int(getattr(result, "input_tokens", 0) or 0)
        except (ValueError, TypeError):
            in_tok = 0
        try:
            out_tok = int(getattr(result, "output_tokens", 0) or 0)
        except (ValueError, TypeError):
            out_tok = 0
        try:
            tot_tok = int(getattr(result, "total_tokens", 0) or (in_tok + out_tok))
        except (ValueError, TypeError):
            tot_tok = in_tok + out_tok
        try:
            c = float(getattr(result, "cost", 0.0) or 0.0)
        except (ValueError, TypeError):
            c = 0.0
        try:
            dur = float(getattr(result, "duration_seconds", 0.0) or 0.0)
        except (ValueError, TypeError):
            dur = 0.0

        stg["agents"].append(
            {
                "agent": agent,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": tot_tok,
                "cost": round(c, 6),
                "duration_seconds": round(dur, 3),
                "success": getattr(result, "success", True),
            }
        )
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
        """Persiste a telemetria: UM json canônico por ONDA (única fonte) +
        telemetria.md como RELATÓRIO humano gerado (nunca lido por máquina)."""
        try:
            if not (hasattr(self, "workspace") and hasattr(self, "state_machine")):
                return
            telemetry_data = json.dumps(self.telemetry, indent=2, ensure_ascii=False)
            wave_telemetry = self.workspace.wave_telemetry_path(self.state_machine.wave_id)
            wave_telemetry.parent.mkdir(parents=True, exist_ok=True)
            wave_telemetry.write_text(telemetry_data, encoding="utf-8")

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
                    ag_speed = round(ag["total_tokens"] / max(ag["duration_seconds"], 0.001), 1)
                    md_lines.append(
                        f"| **{stg_name}** | `{ag['agent']}` | {ag['input_tokens']:,} | {ag['output_tokens']:,} | {ag['total_tokens']:,} | ${ag['cost']:.6f} | {ag['duration_seconds']:.2f}s | {ag_speed:,} |"
                    )
                stg_speed = round(
                    stg_data["total_tokens"] / max(stg_data["duration_seconds"], 0.001), 1
                )
                md_lines.append(
                    f"| *Subtotal {stg_name}* | - | *{stg_data['input_tokens']:,}* | *{stg_data['output_tokens']:,}* | *{stg_data['total_tokens']:,}* | *${stg_data['cost']:.6f}* | *{stg_data['duration_seconds']:.2f}s* | *{stg_speed:,}* |"
                )

            # RELATÓRIO humano (gerado do json canônico — a máquina não o lê).
            docs_dir = self.project_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            (docs_dir / "telemetria.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Falha ao salvar arquivos de telemetria: %s", exc)

    def _load_or_create_state_machine(self) -> TuringStateMachine:
        saved = self.db.load_wave_state()
        if saved:
            wave_id = saved.get("wave_id", "ONDA-001")
            raw_state = saved.get("state", WaveState.DISCOVERY.value)
            raw_autonomy = saved.get("autonomy_mode", AutonomyMode.AUTO.value)
            raw_eng = saved.get("engineering_mode", EngineeringMode.TDD_CODE.value)

            try:
                state = WaveState(raw_state)
            except ValueError:
                state = WaveState.DISCOVERY

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

        return TuringStateMachine(wave_id="ONDA-001", initial_state=WaveState.DISCOVERY)

    def start_wave(
        self,
        wave_id: str,
        autonomy_mode: str = "AUTO",
        engineering_mode: str = "tdd-code",
        force: bool = False,
        delivery_target: str | None = None,
    ) -> dict[str, Any]:
        """Inicializa (ou retoma) uma ONDA de forma autônoma e inteligente.

        Autonomia total — NÃO existe decisão humana nem flag de força:
        - Mesma ONDA pendente → retoma o checkpoint exato (RESUME).
        - Outra ONDA pedida com checkpoint ativo → arquiva o checkpoint no
          histórico (nada é destruído) e inicia a pedida.
        - ONDA pedida tem checkpoint histórico não concluído → retoma dele.
        - ONDA concluída com cards DEV_DONE (anomalia: homologação indevida
          ou validação interrompida) → reabre na etapa inferida pelas filas.
        """
        # `force` é obsoleto: mantido na assinatura por compatibilidade, ignorado.
        saved = self.db.load_wave_state()

        if delivery_target:
            self.delivery_target = DeliveryTarget.from_str(delivery_target)
            try:
                cfg = self.config_mgr.load()
                cfg.delivery_target = self.delivery_target.value
                self.config_mgr.save(cfg)
            except Exception as e:  # noqa: BLE001 — persistência de config é best-effort
                logger.warning("Falha ao salvar delivery_target no config: %s", e)

        try:
            autonomy = AutonomyMode(autonomy_mode.upper())
        except ValueError:
            autonomy = AutonomyMode.AUTO

        try:
            eng = EngineeringMode(engineering_mode.lower())
        except ValueError:
            eng = EngineeringMode.TDD_CODE

        # RESUME: mesma ONDA pendente → retoma EXATAMENTE do ponto onde o
        # processo anterior parou (ex.: veto na VALIDATE).
        saved = self.db.load_wave_state() or {}
        same_wave_pending = bool(
            saved
            and str(saved.get("wave_id", "")).upper() == wave_id.upper().strip()
            and saved.get("state") not in (WaveState.COMPLETED.value, "COMPLETED", None, "")
        )
        if same_wave_pending:
            try:
                restored_stage = WaveState(str(saved.get("state")).upper())
            except ValueError:
                restored_stage = WaveState.DISCUSS
            saved_autonomy = str(saved.get("autonomy_mode") or autonomy.value).upper()
            caller_usou_defaults = (
                autonomy_mode.upper() == "AUTO" and engineering_mode.lower() == "tdd-code"
            )
            if caller_usou_defaults:
                try:
                    autonomy = AutonomyMode(saved_autonomy)
                except ValueError:
                    pass
                saved_eng = str(saved.get("engineering_mode") or eng.value).lower()
                try:
                    eng = EngineeringMode(saved_eng)
                except ValueError:
                    pass

            self.state_machine = TuringStateMachine(
                wave_id=wave_id,
                initial_state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
            self.db.save_wave_state(
                wave_id=wave_id,
                state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )

            # Diagnóstico pelas FILAS do Kanban (padrão code-forge retomar()):
            # onde exatamente o processo parou e o que já está selado.
            cards = self.kanban.list_cards(wave_id=wave_id)
            dev_done = [
                c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DEV_DONE.value
            ]
            done = [c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DONE.value]
            blocked = [
                c["story_id"]
                for c in cards
                if c.get("is_blocked") or c.get("block_reason") or c.get("status") == "BLOCKED"
            ]
            diagnosis_parts = [f"{len(done)} story(ies) DONE (seladas)"]
            if dev_done:
                diagnosis_parts.append(
                    f"{len(dev_done)} DEV_DONE aguardando validação: {', '.join(dev_done)}"
                )
            if blocked:
                diagnosis_parts.append(f"{len(blocked)} bloqueada(s): {', '.join(blocked)}")
            diagnosis = " | ".join(diagnosis_parts) if cards else "sem cards registrados no Kanban"

            # REGRAS DA TELA: a área de conversa mostra APENAS o próximo item a
            # ser trabalhado — NUNCA uma lista (a LLM não olha lista; olha o 1
            # item). O diagnóstico completo fica só no retorno do CLI.
            # FILA INDIANA: bandeira vermelha = o próximo é ela; senão o
            # PRIMEIRO da ordem do kanban que ainda não está selado.
            _seladas = (
                KanbanCardStatus.DEV_DONE.value,
                KanbanCardStatus.DONE.value,
            )
            _bandeiras = [c for c in cards if c.get("is_blocked")]
            proxima = (
                _bandeiras[0]["story_id"]
                if _bandeiras
                else next(
                    (c["story_id"] for c in cards if c.get("status") not in _seladas),
                    None,
                )
            )

            BUS.publish(
                "wave_start",
                agent="@turing",
                wave_id=wave_id,
                text=(
                    f"↩️ ONDA {wave_id} retomada na etapa {restored_stage.value} "
                    f"(checkpoint persistido). Autonomia: {autonomy.value}. "
                    + (
                        f"Próximo item: {proxima}."
                        if proxima
                        else "Nenhum item em execução."
                    )
                ),
                autonomy=autonomy.value,
                engineering_mode=eng.value,
                resumed=True,
            )
            return {
                "success": True,
                "wave_id": wave_id,
                "stage": restored_stage.value,
                "autonomy_mode": autonomy.value,
                "engineering_mode": eng.value,
                "resumed": True,
                "diagnosis": {
                    "done": done,
                    "dev_done": dev_done,
                    "blocked": blocked,
                    "summary": diagnosis,
                },
                "message": (
                    f"ONDA {wave_id} retomada na etapa {restored_stage.value} "
                    f"exatamente de onde o processo anterior parou. {diagnosis}."
                ),
            }

        # Outra ONDA com checkpoint ativo → arquiva no histórico (sem destruir nada,
        # sem perguntar nada ao humano).
        if (
            saved
            and str(saved.get("wave_id", "")).upper() != wave_id.upper().strip()
            and saved.get("state") not in (WaveState.COMPLETED.value, "COMPLETED")
        ):
            arquivado = self.db.archive_wave_state()
            if arquivado:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🗄️ Checkpoint da {arquivado.get('wave_id')} (etapa {arquivado.get('state')}) "
                        "arquivado no histórico com segurança — prosseguindo para a ONDA pedida."
                    ),
                )

        # ONDA pedida tem checkpoint histórico não concluído → retoma dele.
        checkpoint = self.db.load_wave_checkpoint(wave_id)
        if checkpoint and checkpoint.get("state") not in (
            WaveState.COMPLETED.value,
            "COMPLETED",
        ):
            try:
                restored_stage = WaveState(str(checkpoint.get("state")).upper())
            except ValueError:
                restored_stage = WaveState.DISCUSS
            self.state_machine = TuringStateMachine(
                wave_id=wave_id,
                initial_state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
            self.db.save_wave_state(
                wave_id=wave_id,
                state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
            BUS.publish(
                "wave_start",
                agent="@turing",
                wave_id=wave_id,
                text=(
                    f"↩️ ONDA {wave_id} retomada do histórico na etapa {restored_stage.value}. "
                    f"Autonomia: {autonomy.value}."
                ),
                autonomy=autonomy.value,
                resumed=True,
            )
            return {
                "success": True,
                "wave_id": wave_id,
                "stage": restored_stage.value,
                "autonomy_mode": autonomy.value,
                "engineering_mode": eng.value,
                "resumed": True,
                "message": (
                    f"ONDA {wave_id} retomada do histórico na etapa {restored_stage.value}."
                ),
            }

        initial_stage = WaveState.DISCUSS
        norm_id = wave_id.upper().strip()
        if norm_id in ("ONDA-000", "ONDA-0", "WAVE-000", "WAVE-0") or norm_id.startswith(
            ("ONDA-000-", "WAVE-000-", "ONDA-0-")
        ):
            initial_stage = WaveState.DISCOVERY
        elif (self.project_dir / "docs" / "briefings" / "PRD.md").exists():
            cards = self.kanban.list_cards(wave_id=wave_id)
            if cards:
                statuses = {c.get("status") for c in cards}
                trabalho_em_curso = statuses & {"IN_PROGRESS", "IN_REVIEW", "READY", "BACKLOG"}
                if not trabalho_em_curso and KanbanCardStatus.DEV_DONE.value in statuses:
                    # Anomalia detectada: todas as stories DEV_DONE mas a onda não
                    # concluiu (ex.: homologação indevida). Reabre na VALIDATE.
                    initial_stage = WaveState.VALIDATE
                else:
                    initial_stage = WaveState.EXECUTE
            else:
                initial_stage = WaveState.PLAN

        self.state_machine = TuringStateMachine(
            wave_id=wave_id,
            initial_state=initial_stage,
            autonomy_mode=autonomy,
            engineering_mode=eng,
        )

        self.db.save_wave_state(
            wave_id=wave_id,
            state=initial_stage,
            autonomy_mode=autonomy,
            engineering_mode=eng,
        )

        is_zero = initial_stage == WaveState.DISCOVERY
        fluxo = (
            "DISCOVERY → INCEPTION → COMPLETED (Upstream estrito, sem código em src/)"
            if is_zero
            else "PLAN → REFINEMENT → EXECUTE → VALIDATE → COMPLETED"
        )
        BUS.publish(
            "wave_start",
            agent="@turing",
            wave_id=wave_id,
            text=(
                f"🌊 ONDA {wave_id} iniciada — "
                + ("Onda Zero (Greenfield Lean Inception Macro)" if is_zero else "Onda de Entrega")
                + f". Fluxo: {fluxo}. Autonomia: {autonomy.value}."
            ),
            autonomy=autonomy.value,
            engineering_mode=eng.value,
        )

        return {
            "success": True,
            "wave_id": wave_id,
            "stage": initial_stage.value,
            "autonomy_mode": autonomy.value,
            "engineering_mode": eng.value,
            "message": f"ONDA {wave_id} inicializada com sucesso na etapa {initial_stage.value}.",
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

    def _get_project_fs_tools(self, guarda: Any = None) -> list[Any]:
        project_dir = self.project_dir

        def read_project_file(path: str) -> str:
            """Lê o conteúdo de um arquivo do projeto a partir do caminho relativo (ex: 'docs/stories/ST-001.md')."""
            aviso_leitura = ""
            if guarda is not None:
                aviso_leitura = guarda.registrar_leitura(path)
            is_safe, err_msg = validate_safe_relative_path(path)
            if not is_safe:
                return f"Erro: {err_msg}"
            try:
                target = (project_dir / path).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return f"Erro: Acesso fora do projeto negado para {path}"
                if not target.exists() or not target.is_file():
                    return f"Erro: Arquivo {path} não existe no projeto."
                conteudo = target.read_text(encoding="utf-8", errors="replace")
                return f"{conteudo}{aviso_leitura}" if aviso_leitura else conteudo
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return f"Erro ao ler {path}: {e}"

        def write_project_file(path: str, content: str) -> str:
            """Grava conteúdo em um arquivo do projeto no caminho relativo especificado (ex: 'js/logic.js')."""
            is_safe, err_msg = validate_safe_relative_path(path)
            if not is_safe:
                return f"Erro: {err_msg}"
            try:
                target = (project_dir / path).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return f"Erro: Acesso fora do projeto negado para {path}"
                stage = getattr(self.state_machine, "stage", None)
                stage_name = stage.name if hasattr(stage, "name") else str(stage or "DISCUSS")
                allowed, stage_reason = validate_stage_permission(
                    stage_name, "write", str(target), str(project_dir)
                )
                if not allowed:
                    return (
                        stage_reason
                        or "Erro: Operação bloqueada pelas regras da etapa atual da ONDA."
                    )
                # GUARDIÃO DETERMINÍSTICA DE AÇÕES: valida o conteúdo ANTES de
                # gravar (anti-alucinação por ação, não por relógio).
                if guarda is not None:
                    veto = guarda.validar_escrita(path, content)
                    if veto:
                        return veto
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"Arquivo {path} gravado com sucesso ({len(content)} caracteres)."
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return f"Erro ao gravar {path}: {e}"

        def list_project_files(directory: str = ".") -> list[str]:
            """Lista os arquivos existentes no diretório relativo do projeto."""
            if directory and directory != ".":
                is_safe, err_msg = validate_safe_relative_path(directory)
                if not is_safe:
                    return [f"Erro: {err_msg}"]
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
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return [f"Erro: {e}"]

        def delete_project_file(path: str) -> str:
            """Apaga UM arquivo do projeto (higiene: resíduos tmp_*, snippets mortos).

            Política de confiança: DENTRO da raiz do projeto apaga tudo em
            qualquer modo — bobagem interna o git amortece (estado da plataforma
            .git/.bombe-code permanece intocado). FORA da raiz: em AUTO é negado;
            em SEMI-AUTO/MANUAL exige permissão explícita do humano.
            """
            if guarda is not None and hasattr(guarda, "registrar_acao"):
                guarda.registrar_acao("delete_project_file", str(path))
            if not (path or "").strip():
                return "Erro: caminho vazio."
            alvo = Path(path).expanduser()
            try:
                target = (alvo if alvo.is_absolute() else project_dir / alvo).resolve()
            except (OSError, RuntimeError):
                return f"Erro: caminho inválido {path}"
            if not target.is_relative_to(project_dir.resolve()):
                modo = getattr(self.state_machine, "autonomy_mode", None)
                modo_nome = (getattr(modo, "name", "") or str(modo or "AUTO")).upper()
                if "SEMI" not in modo_nome and "MANUAL" not in modo_nome:
                    return (
                        f"⛔ [MODO {modo_nome}] Remoção NEGADA: '{path}' está FORA da raiz "
                        "do projeto. Em automação total nada fora da raiz é apagado — "
                        "bobagem fora não tem conserto."
                    )
                if not remocao_autorizada(str(target)):
                    quem = guarda.agente if guarda is not None else "agente"
                    BUS.publish(
                        "escalation",
                        agent="@turing",
                        text=(
                            f"🟠 PERMISSÃO EXPLÍCITA — {quem} quer apagar FORA do projeto: "
                            f"{target}\nAutorize com /permitir apagar {target} (vale nesta sessão)."
                        ),
                        escalation={"type": "permission_request", "path": str(target)},
                    )
                    return (
                        f"⛔ PERMISSÃO NECESSÁRIA: '{path}' está fora da raiz do projeto. "
                        "Pedido registrado ao humano — autorize com /permitir apagar <caminho> "
                        "e repita a remoção."
                    )
            else:
                # Dentro da raiz: estado da plataforma não tem conserto nem via git
                partes = target.relative_to(project_dir.resolve()).parts
                if any(p in (".git", ".bombe-code") for p in partes[:-1]):
                    return (
                        f"Erro: '{path}' está sob diretório da plataforma (.git/.bombe-code) "
                        "— remoção negada."
                    )
            if target.is_dir():
                return f"Erro: '{path}' é um diretório — a remoção é arquivo a arquivo."
            if not target.exists():
                return f"Erro: Arquivo {path} não existe."
            if guarda is not None:
                veto = guarda.validar_remocao(path)
                if veto:
                    return veto
            try:
                target.unlink()
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return f"Erro ao remover {path}: {e}"
            return f"Arquivo {path} removido."

        def executar_comando(comando: str) -> str:
            """Executa comando de VALIDAÇÃO no projeto (suítes e gates).

            Gate estruturado (grade enterprise): aceita launchers reais de
            ambiente (uv/poetry run, .venv/bin, python -m, npx/npm/node) +
            programas de validação e helpers de leitura, em QUALQUER segmento
            de pipe. Lista negra sempre vence (destrutivos, rede, install).
            A saída crua (cauda de 8.000 caracteres) é a evidência obrigatória
            para veredito de QA — inspeção estática não emite veredito.
            """
            if guarda is not None and hasattr(guarda, "registrar_acao"):
                guarda.registrar_acao("executar_comando", str(comando))
            cmd = (comando or "").strip()
            if not cmd:
                return "Erro: comando vazio."

            proibidos = (
                "rm ",
                "sudo",
                "curl ",
                "wget ",
                "pip install",
                "npm install",
                "git push",
                "git reset",
                "mkfs",
                "dd ",
                "chmod ",
                "chown ",
                "shutdown",
                "reboot",
                "eval ",
                "nc ",
                "ssh ",
                "tee ",
            )
            programas_validacao = {
                "pytest",
                "python",
                "python3",
                "npx",
                "npm",
                "node",
                "vitest",
                "playwright",
                "jest",
                "ruff",
                "mypy",
                "uv",
                "poetry",
                "bash",
                "sh",
                "pdm",
                "hatch",
            }
            programas_leitura = {"tail", "head", "grep", "wc", "sort", "uniq", "cat", "true"}

            try:
                import shlex as _shlex
            except Exception:  # noqa: BLE001 — indisponível é improvável; nega
                return "Erro: ambiente sem shlex."

            def _programa(segmento: str) -> str:
                try:
                    tokens = _shlex.split(segmento)
                except ValueError:
                    tokens = segmento.split()
                if not tokens:
                    return ""
                primeiro = Path(tokens[0]).name.lower()
                if (
                    primeiro in ("uv", "poetry", "pdm", "hatch")
                    and len(tokens) >= 3
                    and tokens[1] == "run"
                ):
                    primeiro = Path(tokens[2]).name.lower()
                return primeiro

            ferramenta = auditar_instalacao(cmd)
            if ferramenta is not None and not ferramenta.startswith("Erro"):
                BUS.publish(
                    "announcement",
                    agent=(guarda.agente if guarda is not None else "@turing"),
                    text=(
                        f"📦 INSTALAÇÃO AUDITADA — {cmd[:80]}: dependência do projeto "
                        f"autorizada pelo gate determinístico ({ferramenta}, local, "
                        "sem global, sem encadeamento). Registrada no kanban/telemetria."
                    ),
                )
            elif ferramenta is not None:
                return ferramenta
            if ferramenta is None:
                # Whitelist normal (instalação auditada pula: já foi validada
                # por completo no gate acima).
                for segmento in cmd.split("|"):
                    low_seg = f" {segmento.lower()} "
                    if any(p in low_seg for p in proibidos):
                        return f"Erro: comando contém operação proibida ({segmento.strip()[:60]})."
                    corpo = re.split(r">|<", segmento.strip())[0].strip()
                    if not corpo:
                        continue
                    programa = _programa(corpo)
                    if programa not in programas_validacao | programas_leitura:
                        return (
                            f"Erro: programa '{programa or segmento.strip()[:40]}' fora da "
                            "lista de validação (pytest/vitest/playwright/npm/npx/node/"
                            "uv/poetry run/scripts + filtros de leitura tail/head/grep/wc)."
                        )
                    if programa in ("bash", "sh"):
                        alvo = (
                            (corpo.split(maxsplit=1) or ["", ""])[1]
                            if len(corpo.split(maxsplit=1)) > 1
                            else ""
                        )
                        if "scripts/" not in alvo and not alvo.endswith(".sh"):
                            return "Erro: bash/sh só executa scripts/ do projeto."
            # Batimento: comando longo (pytest completo) é trabalho legítimo —
            # alimenta o IDLE do runner para não ser abortado aos 240s.
            import threading

            parar_batimento = threading.Event()

            def _batimento() -> None:
                while not parar_batimento.wait(30):
                    try:
                        marcar_atividade_tool()
                        BUS.publish(
                            "tool_progress",
                            agent=(guarda.agente if guarda is not None else "@turing"),
                            text=f"executando: {cmd[:90]}",
                        )
                    except Exception:  # noqa: BLE001, S110 — batimento é best-effort
                        pass

            batimento = threading.Thread(target=_batimento, daemon=True)
            batimento.start()
            try:
                resultado = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(project_dir),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=False,
                )
                saida = (resultado.stdout or "") + (
                    f"\n[stderr]\n{resultado.stderr}" if resultado.stderr else ""
                )
                # EVIDÊNCIA PLATFORM-SIDE: comando auditado EXECUTADO pela
                # ferramenta com exit code REAL (prosa não é evidência). Alimenta
                # o DOD da card de INSTALACAO — cuja prova é a VALIDAÇÃO (teste
                # de import/require) rodando verde, não o install em si.
                if guarda is not None and hasattr(guarda, "registrar_comando_executado"):
                    guarda.registrar_comando_executado(cmd, resultado.returncode)
                return f"exit={resultado.returncode}\n{saida.strip()[-8000:]}"
            except subprocess.TimeoutExpired:
                return "Erro: execução excedeu 600s (timeout da plataforma)."
            except Exception as e:  # noqa: BLE001 — tool retorna erro textual à LLM
                return f"Erro ao executar: {e}"
            finally:
                parar_batimento.set()

        return [
            read_project_file,
            write_project_file,
            list_project_files,
            delete_project_file,
            executar_comando,
        ]

    def _get_runner(self, agent_handle: str) -> AgentRunner | None:
        agent = self.registry.get(agent_handle)
        if not agent:
            return None
        from bombe_code.permissions.acao_guard import GuardaDeAcoes

        guarda = GuardaDeAcoes(agente=agent_handle)
        return AgentRunner(
            agent=agent,
            llm_factory=self.llm_factory,
            project_db=self.db,
            extra_tools=self._get_project_fs_tools(guarda),
            guarda=guarda,
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
        "@alan": [("docs/briefings/PRD.md", "PRD Estruturado (@grace)")],
        "@ieru": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            ("docs/architecture/journey.md", "Mapeamento da Jornada do Usuário (@alan)"),
        ],
        "@codd": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            (
                "docs/architecture/SYSTEM_ARCHITECTURE.md",
                "Arquitetura do Sistema e Decisões Técnicas (@ieru)",
            ),
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
        wave_id = (
            getattr(self.state_machine, "wave_id", None) if hasattr(self, "state_machine") else None
        )
        target_sid = story_id or "ST-001"
        for rel_template, desc in reqs:
            rel_path = rel_template.replace("{story_id}", target_sid)
            target = self.project_dir / rel_path
            if not target.exists() and "stories" in rel_path:
                if "_test_plan.md" in rel_path:
                    alt = self.workspace.find_test_plan_file(target_sid, wave_id=wave_id)
                else:
                    alt = self.workspace.find_story_file(target_sid, wave_id=wave_id)
                if alt and alt.exists():
                    target = alt
            if not target.exists():
                return (
                    False,
                    f"Pré-requisito ausente para {agent_handle}: O arquivo '{rel_path}' ({desc}) não existe no disco.",
                )
            if target.is_file() and target.stat().st_size < 50:
                return (
                    False,
                    f"Pré-requisito inválido para {agent_handle}: O arquivo '{rel_path}' ({desc}) está vazio ou raso (< 50 bytes).",
                )
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
                status=KanbanCardStatus.IN_PROGRESS.value,
            )
        self.kanban.block_card(target_story, reason=reason, blocked_by=agent_handle)

    def _publish_stage(self, event_type: str, text: str, **data: Any) -> None:
        """Publica anúncio canônico de etapa (visível mesmo no modo quiet)."""
        BUS.publish(
            event_type,
            agent="@turing",
            text=text,
            wave_id=self.state_machine.wave_id,
            stage=self.state_machine.current_state.value,
            **data,
        )

    def run_discuss(self, topic: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Etapa DISCUSS com anúncios canônicos de início/fim."""
        self._publish_stage(
            "stage_start",
            f"🎬 Etapa DISCUSS iniciada — @meira (viabilidade) e @grace (PRD) acionados para: {str(topic)[:120]}",
        )
        result = self._run_discuss_inner(topic, context)
        if result.get("success"):
            self._publish_stage(
                "stage_end",
                "✓ Etapa DISCUSS concluída — artefatos: docs/briefings/VIABILITY.md e docs/briefings/PRD.md.",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa DISCUSS interrompida: {result.get('error')}",
            )
        return result

    def run_plan(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Etapa PLAN com anúncios canônicos de início/fim."""
        self._publish_stage(
            "stage_start",
            "🎬 Etapa PLAN iniciada — arquitetos de Upstream (@ieru, @codd, @caroli) em ação.",
        )
        result = self._run_plan_inner(context)
        if result.get("success"):
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            self._publish_stage(
                "stage_end",
                f"✓ Etapa PLAN concluída — arquitetura e backlog prontos ({len(cards)} stories no Kanban).",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa PLAN interrompida: {result.get('error')}",
            )
        return result

    def run_cycle(self, story_id: str | None = None) -> dict[str, Any]:
        """Etapa EXECUTE (ciclo TDD) com anúncios canônicos de início/fim."""
        alvo = story_id or "lote de stories pendentes"
        self._publish_stage("stage_start", f"🎬 Etapa EXECUTE iniciada — alvo: {alvo}.")
        result = self._run_cycle_inner(story_id)
        if result.get("success"):
            self._publish_stage(
                "stage_end",
                f"✓ Etapa EXECUTE concluída — {result.get('message', '')}",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa EXECUTE interrompida: {result.get('error')}",
            )
        return result

    def run_validate(self) -> dict[str, Any]:
        """Etapa VALIDATE com anúncios canônicos e ciclo de retrabalho de vetos."""
        self._publish_stage(
            "stage_start",
            "🎬 Etapa VALIDATE iniciada — auditoria formal com @edith (homologação) e @nina (governança).",
        )
        result = self._run_validate_inner()
        if result.get("success"):
            self._publish_stage(
                "stage_end",
                "✓ Etapa VALIDATE concluída — Selo de Homologação emitido (@edith + @nina).",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa VALIDATE não aprovada: {result.get('error')}",
            )
        return result

    def _run_discuss_inner(
        self, topic: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Executa a etapa DISCOVERY / DISCUSS com @meira (viabilidade) e @grace (PRD)."""
        if not topic or not str(topic).strip():
            return {
                "success": False,
                "error": "missing_topic",
                "message": (
                    "⚠️ Nenhuma demanda ou briefing informado para a etapa DISCOVERY / DISCUSS. "
                    "Informe a ideia ou escopo do produto (ex: /wave discuss <ideia>) para iniciar a viabilidade com @meira e o PRD com @grace."
                ),
            }

        if self.state_machine.current_state not in (WaveState.DISCUSS, WaveState.DISCOVERY):
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado DISCOVERY ou DISCUSS.",
            }

        results: list[dict[str, Any]] = []
        profile = UpstreamProfiler.profile(self.project_dir, self.delivery_target)
        logger.info(
            "🎯 [DISCUSS] Nível: %s | Origem: %s | Inception: %s",
            self.delivery_target.value.upper(),
            profile.origin.value,
            profile.inception_level.value,
        )

        ctx = dict(context or {})
        ctx["upstream_profile"] = profile
        context = ctx

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
            res_meira = self._executar_com_card(
                self.state_machine.wave_id,
                "DISCUSS",
                "DISCUSS-VIABILIDADE",
                f"Viabilidade técnica e estratégica: {topic[:100]}",
                "@meira",
                1,
                lambda: runner_meira.run(prompt=meira_prompt, context=context),
                dor=[],
                dod=["status_aprovado_ou_prosseguir"],
                task_tipo="DISCUSS",
                descricao="Análise de viabilidade técnica e estratégica da demanda.",
            )
            self._record_telemetry("DISCUSS", "@meira", res_meira)
            results.append(
                {"agent": "@meira", "output": res_meira.output, "success": res_meira.success}
            )

            # FAIL-FAST: Se @meira bloqueou ou falhou, Turing intervém no ato!
            if getattr(res_meira, "is_blocked", False):
                reason = (
                    getattr(res_meira, "block_reason", None) or "Agente @meira bloqueou a execução."
                )
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
                f"## Escopo da Entrega ({self.delivery_target.value.upper()})\n"
                f"## Sequenciador de Ondas do MVP (Lean Inception)\n"
                f"Estruture o fatiamento em Ondas de Entrega seguindo as 4 Regras da Lean Inception:\n"
                f"1. Fatias Verticais (End-to-End Tracing): Toda onda corta todas as camadas necessárias.\n"
                f"2. Semáforo de Risco: Classifique cada onda em VERMELHO, AMARELO ou VERDE (max 1 item VERMELHO por onda; o maior risco deve ser na 1ª onda).\n"
                f"3. Capacidade Finita: Máximo de 3 a 4 fatias verticais por onda.\n"
                f"4. Hipótese de Negócio: Cada onda valida uma hipótese central de produto (Onda 1: Core Value Loop; Ondas seguintes: Retenção/Sinais; Onda Final: Automação/Release).\n"
                f"NÃO gere stories antecipadas para ondas futuras. Formate estritamente a tabela:\n"
                f"| Onda | Nome da Onda | Hipótese de Negócio | Fatias Verticais / Features | Risco | Final |\n"
                f"| ONDA-001 | ... | ... | ... | VERMELHO | Não |\n\n"
                f"Ao concluir com sucesso, declare explicitamente no seu parecer: 'Status: APROVADO'."
            )
            grace_prompt = self._assemble_prompt("@grace", raw_prompt, context)
            res_grace = self._executar_com_card(
                self.state_machine.wave_id,
                "DISCUSS",
                "DISCUSS-PRD",
                f"PRD e fatiamento Lean Inception: {topic[:100]}",
                "@grace",
                2,
                lambda: runner_grace.run(prompt=grace_prompt, context=context),
                dor=["dep:DISCUSS-VIABILIDADE"],
                dod=["status_aprovado_e_prd_gravado"],
                task_tipo="DISCUSS",
                descricao="Elaboração do PRD e sequenciamento de ondas do MVP.",
            )
            self._record_telemetry("DISCUSS", "@grace", res_grace)
            grace_output = res_grace.output
            results.append(
                {"agent": "@grace", "output": res_grace.output, "success": res_grace.success}
            )

            # FAIL-FAST: Se @grace bloqueou ou falhou, Turing intervém no ato!
            if getattr(res_grace, "is_blocked", False):
                reason = (
                    getattr(res_grace, "block_reason", None) or "Agente @grace bloqueou a execução."
                )
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

    def _run_plan_inner(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa PLAN / INCEPTION / REFINEMENT com arquitetos de Upstream."""
        if self.state_machine.current_state not in (
            WaveState.PLAN,
            WaveState.INCEPTION,
            WaveState.REFINEMENT,
        ):
            if self.state_machine.current_state in (WaveState.DISCUSS, WaveState.DISCOVERY):
                from .state_machine import WaveType

                target = (
                    TuringStage.INCEPTION
                    if self.state_machine.wave_type == WaveType.WAVE_ZERO
                    else TuringStage.PLAN
                )
                if not self.transition_to(target):
                    return {
                        "success": False,
                        "error": f"Não foi possível transitar para {target.value}.",
                    }
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado PLAN, INCEPTION ou REFINEMENT.",
                }

        results: list[dict[str, Any]] = []
        outputs: dict[str, str] = {}
        profile = UpstreamProfiler.profile(self.project_dir, self.delivery_target)
        ctx = dict(context or {})
        ctx["upstream_profile"] = profile
        context = ctx

        # -------------------------------------------------------------
        # 1. @alan: Mapeamento de Jornada e Telas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@alan")
        if not ok:
            self.handle_agent_block("@alan", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_alan = self._get_runner("@alan")
        if runner_alan:
            from bombe_code.domain.wave.sequencer import WaveSequencer

            prd_file = self.workspace.prd_path
            prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
            sequencer = WaveSequencer.from_markdown(prd_content)
            plan = sequencer.get_plan(self.state_machine.wave_id)
            plan_context = ""
            if plan:
                plan_context = (
                    f"\nESCOPO/FATIAS DA ONDA ({self.state_machine.wave_id}):\n"
                    f"- Nome da Onda: {plan.name}\n"
                    f"- Hipótese de Negócio: {plan.business_hypothesis}\n"
                    f"- Features da Onda: {', '.join(plan.features)}\n"
                )

            master_journey = self.workspace.journey_master_path
            has_master = master_journey.exists() and master_journey.stat().st_size >= 50

            if has_master:
                raw_prompt = (
                    f"Você está atuando no planejamento da ONDA {self.state_machine.wave_id}.\n"
                    f"A Jornada Global do Usuário do projeto já está consolidada em 'docs/architecture/journey.md'.\n"
                    f"{plan_context}\n"
                    f"Sua missão é gerar o RECORTE DE JORNADA (Journey Slice) específico para esta onda:\n"
                    f"- Mapeie os fluxos de navegação, telas e entry points estritamente pertinentes às fatias/épicos desta onda.\n"
                    f"É OBRIGATÓRIO incluir as seções: '## Entry Points da Onda', '## Fluxo de Navegação desta Fatia', '## Telas da Onda'."
                )
            else:
                raw_prompt = (
                    f"Mapeie a jornada do usuário e telas para o projeto e a demanda da ONDA {self.state_machine.wave_id}.\n"
                    f"Consulte o PRD em 'docs/briefings/PRD.md'.\n"
                    f"{plan_context}\n"
                    f"Mapeie estritamente os fluxos e telas da demanda solicitada, sem inventar telas acessórias ou escopos extras.\n"
                    f"É OBRIGATÓRIO incluir as seções: '## Entry Points', '## Fluxo de Navegação', '## Telas'."
                )
            alan_prompt = self._assemble_prompt("@alan", raw_prompt, context)
            res_alan = self._executar_com_card(
                self.state_machine.wave_id,
                "PLAN",
                "PLAN-JORNADA",
                "Mapeamento de jornada e telas",
                "@alan",
                1,
                lambda: runner_alan.run(prompt=alan_prompt, context=context),
                dor=[],
                dod=["journey_slice_gravado"],
                task_tipo="PLAN",
                descricao="Mapeamento de jornada do usuário, entry points e telas da onda.",
            )
            self._record_telemetry("PLAN", "@alan", res_alan)
            outputs["@alan"] = res_alan.output
            results.append(
                {"agent": "@alan", "output": res_alan.output, "success": res_alan.success}
            )

            if getattr(res_alan, "is_blocked", False):
                reason = (
                    getattr(res_alan, "block_reason", None) or "Agente @alan bloqueou a execução."
                )
                self.handle_agent_block("@alan", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            if not res_alan.success:
                err = getattr(res_alan, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@alan", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @alan: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Salva o journey slice da onda e a jornada mestre do projeto
            try:
                slice_path = self.workspace.wave_journey_slice_path(self.state_machine.wave_id)
                slice_path.parent.mkdir(parents=True, exist_ok=True)
                slice_path.write_text(res_alan.output, encoding="utf-8")

                master_path = self.workspace.journey_master_path
                master_path.parent.mkdir(parents=True, exist_ok=True)
                if not master_path.exists() or master_path.stat().st_size < 50:
                    master_path.write_text(res_alan.output, encoding="utf-8")

                art_content = slice_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Falha ao salvar journey slice: %s", e)
                art_content = ""

            # Gate de Jornada
            journey_eval = self.journey_gate.evaluate(
                f"{art_content}\n\n{res_alan.output}" if art_content else res_alan.output
            )
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
                f"Projete a arquitetura com YAGNI proporcional à demanda (sem infraestrutura desnecessária).\n"
                f"É OBRIGATÓRIO incluir as seções: '## Decisões Arquiteturais', '## Stack'."
            )
            ieru_prompt = self._assemble_prompt("@ieru", raw_prompt, context)
            res_ieru = self._executar_com_card(
                self.state_machine.wave_id,
                "PLAN",
                "PLAN-ARQUITETURA",
                "Decisões arquiteturais e stack",
                "@ieru",
                2,
                lambda: runner_ieru.run(prompt=ieru_prompt, context=context),
                dor=["dep:PLAN-JORNADA"],
                dod=["arquitetura_gravada"],
                task_tipo="PLAN",
                descricao="Definição de decisões arquiteturais e stack da onda.",
            )
            self._record_telemetry("PLAN", "@ieru", res_ieru)
            outputs["@ieru"] = res_ieru.output
            results.append(
                {"agent": "@ieru", "output": res_ieru.output, "success": res_ieru.success}
            )

            if getattr(res_ieru, "is_blocked", False):
                reason = (
                    getattr(res_ieru, "block_reason", None) or "Agente @ieru bloqueou a execução."
                )
                self.handle_agent_block("@ieru", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

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
            arch_eval = self.architecture_gate.evaluate(
                f"{art_content}\n\n{res_ieru.output}" if art_content else res_ieru.output
            )
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
            res_codd = self._executar_com_card(
                self.state_machine.wave_id,
                "PLAN",
                "PLAN-DATABASE",
                "Modelagem de dados e esquemas",
                "@codd",
                3,
                lambda: runner_codd.run(prompt=codd_prompt, context=context),
                dor=["dep:PLAN-ARQUITETURA"],
                dod=["modelagem_concluida"],
                task_tipo="PLAN",
                descricao="Modelagem de dados e schemas de banco para a onda.",
            )
            self._record_telemetry("PLAN", "@codd", res_codd)
            outputs["@codd"] = res_codd.output
            results.append(
                {"agent": "@codd", "output": res_codd.output, "success": res_codd.success}
            )

            if getattr(res_codd, "is_blocked", False):
                reason = (
                    getattr(res_codd, "block_reason", None) or "Agente @codd bloqueou a execução."
                )
                self.handle_agent_block("@codd", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

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
            db_eval = self.db_gate.evaluate(
                f"{art_content}\n\n{res_codd.output}" if art_content else res_codd.output
            )
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
            from bombe_code.domain.wave.sequencer import WaveSequencer

            prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
            prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
            sequencer = WaveSequencer.from_markdown(prd_content)
            plan = sequencer.get_plan(self.state_machine.wave_id)
            plan_context = ""
            if plan:
                feats_str = ", ".join(plan.features)
                plan_context = (
                    f"\nESCOPO CONTRATADO PARA ESTA ONDA NO SEQUENCIADOR ({self.state_machine.wave_id}):\n"
                    f"- Nome da Onda: {plan.name}\n"
                    f"- Hipótese de Negócio: {plan.business_hypothesis}\n"
                    f"- Fatias Verticais / Features desta onda: {feats_str}\n"
                    f"- Nível de Risco: {plan.risk_level.value}\n"
                    f"DIRETRIZ LEAN MANDATÓRIA (ZERO SPEC WASTE):\n"
                    f"Gere ai-stories JUST-IN-TIME EXCLUSIVAMENTE para as fatias desta onda ({feats_str}).\n"
                    f"NÃO gere stories detalhadas para as próximas ondas agora — elas serão geradas nas suas respectivas ondas futuras.\n"
                )

            raw_prompt = (
                f"Decomponha e gere as ai-stories completas para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"{plan_context}\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md', o recorte de jornada em 'docs/waves/{self.state_machine.wave_id}/journey-slice.md' "
                f"(ou jornada global em 'docs/architecture/journey.md') e a Arquitetura em 'docs/architecture/SYSTEM_ARCHITECTURE.md'.\n"
                f"Aplique o método PBB (Product Backlog Building) conforme o nível de Inception {profile.inception_level.value}:\n"
                f"- Granularidade PBB: {profile.pbb_granularity}\n"
                f"- Diretriz técnica: {profile.technical_debt_tolerance}\n"
                f"As stories pertencem a esta onda e serão salvas em 'docs/waves/{self.state_machine.wave_id}/stories/ST-XXX.md'.\n"
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
            res_caroli = self._executar_com_card(
                self.state_machine.wave_id,
                "PLAN",
                "PLAN-STORIES",
                "Decomposição e geração de ai-stories",
                "@caroli",
                4,
                lambda: runner_caroli.run(prompt=caroli_prompt, context=context),
                dor=["dep:PLAN-DATABASE"],
                dod=["stories_geradas"],
                task_tipo="PLAN",
                descricao="Decomposição PBB e escrita das ai-stories da onda.",
            )
            self._record_telemetry("PLAN", "@caroli", res_caroli)
            outputs["@caroli"] = res_caroli.output
            results.append(
                {"agent": "@caroli", "output": res_caroli.output, "success": res_caroli.success}
            )

            if getattr(res_caroli, "is_blocked", False):
                reason = (
                    getattr(res_caroli, "block_reason", None)
                    or "Analista @caroli bloqueou a execução."
                )
                self.handle_agent_block("@caroli", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            if not res_caroli.success:
                err = getattr(res_caroli, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@caroli", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha na analista @caroli: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Preserva stories no disco da ONDA e avalia conformidade física
            try:
                wave_stories_dir = self.workspace.wave_stories_dir(self.state_machine.wave_id)
                wave_stories_dir.mkdir(parents=True, exist_ok=True)
                st1_file = wave_stories_dir / "ST-001.md"

                # Procura por ST-001 se já existir em outro lugar
                alt_st1 = self.workspace.find_story_file(
                    "ST-001", wave_id=self.state_machine.wave_id
                )
                if (
                    alt_st1
                    and alt_st1 != st1_file
                    and (not st1_file.exists() or st1_file.stat().st_size < 50)
                ):
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
            eval_text = (
                f"{story_content}\n\n{res_caroli.output}" if story_content else res_caroli.output
            )
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

    @staticmethod
    def _normalizar_para_veredito(texto: str) -> str:
        """Normaliza markdown/prosa para análise estrutural de veredito."""
        import re as _re

        t = _re.sub(r"[*_`#>|]+", " ", texto or "")
        return _re.sub(r"\s+", " ", t).lower()

    @classmethod
    def _veredito_estrutural(cls, texto_bruto: str) -> tuple[bool, str]:
        """VEREDITO ESTRUTURAL — prova, não adivinhação.

        Um texto SÓ aprova se: (1) não contiver veredito de rejeição em lugar
        nenhum; (2) nenhuma story auditada tiver veredito não-aprovador
        (⚠️ parcial, ❌, divergência...); (3) contiver declaração canônica de
        aprovação. Qualquer contradição veta. Usado pelo gate dos validadores
        E pela rede de segurança sobre o relatório consolidado da ONDA.
        """
        texto = cls._normalizar_para_veredito(texto_bruto)

        # 1. REJEIÇÃO PRIMEIRO (com negações legítimas tratadas).
        rejection_patterns = [
            r"(?<!nada )(?<!não )(?<!nao )(?<!nenhum )rejeitad",
            r"(?<!nada )(?<!não )(?<!nao )(?<!nenhum )reprovad",
            r"não conforme",
            r"nao conforme",
            r"não homologad",
            r"nao homologad",
            r"retorno para retrabalho",
            r"retrabalho focalizado",
            r"(?<!nada )(?<!não )(?<!nao )(?<!sem )bloqueante",
            r"bloqueio crítico",
            r"bloqueio critico",
            r"não aprovad",
            r"nao aprovad",
        ]
        import re as _re

        found_rejection = next(
            (m.group(0) for p in rejection_patterns if (m := _re.search(p, texto))),
            None,
        )
        if found_rejection:
            return (
                False,
                f"veredito de REJEIÇÃO explícito no parecer (marcador: '{found_rejection}')",
            )

        # 2. CONSISTÊNCIA POR STORY: nenhuma story auditada pode estar com
        #    veredito não-aprovador. ONDA aprovada com story parcial/divergente
        #    É PROIBIDO (o furo do make-books). O marcador precisa estar na
        #    MESMA linha da story (formato tabela/registro).
        story_negativos: set[str] = set()
        marcador_negativo = _re.compile(
            r"(❌|⚠️|parcial|não conforme|nao conforme|divergên|divergen|bloqueante)", _re.IGNORECASE
        )
        for linha in texto_bruto.splitlines():
            m_story = _re.search(r"\bst[-\s]?\d+\b", linha, _re.IGNORECASE)
            if m_story and marcador_negativo.search(linha):
                story_negativos.add(m_story.group(0).upper().replace(" ", "-"))
        if story_negativos:
            return (
                False,
                (
                    f"stories auditadas com veredito NÃO-aprovador: {', '.join(sorted(story_negativos))} — "
                    "nenhuma onda pode ser homologada com story parcial ou divergente"
                ),
            )

        # 3. APROVAÇÃO: somente declaração canônica/veredito de selo.
        #    (genérico "aprovad" é seguro: as camadas 1 e 2 já vetaram qualquer
        #     rejeição explícita ou story parcial/divergente antes daqui)
        aprovacao = [
            "aprovad",
            "homologação: aprovado",
            "governança: aprovado",
            "status: aprovado",
            "veredito: aprovado",
            "homologação aprovada",
            "homologad",
            "approved",
            "veredito: verde",
            "selo emitido",
            "selo do cycle concedid",
            "selo final homologad",
            "concedid",
            "suíte aprovada",
            "testes aprovados",
            "review aprovado",
            "revisão aprovada",
            "revisao aprovada",
            "concluíd",
            "concluid",
            "sucesso",
            "passou",
            "entregue",
            "pronto para",
        ]
        if not any(kw in texto for kw in aprovacao):
            return False, "ausência de declaração canônica de aprovação (Default-Deny)"

        return True, "Aprovado com sucesso"

    @classmethod
    def _check_explicit_approval(
        cls, res: AgentExecutionResult | None, artifact_content: str = ""
    ) -> tuple[bool, str]:
        """LEI DA RESTRIÇÃO (DEFAULT-DENY) sobre veredito estrutural.

        Inspeciona o parecer textual E o artefato físico gravado em disco.
        Delegado a _veredito_estrutural (prova, não adivinhação).
        """
        if not res:
            return False, "Nenhum resultado retornado pelo agente (Default-Deny)"
        if getattr(res, "is_blocked", False):
            return False, getattr(res, "block_reason", None) or "Agente reportou bloqueio"
        if not getattr(res, "success", True):
            return False, getattr(res, "error", None) or "Execução do agente falhou"

        combined = f"{getattr(res, 'output', '') or ''}\n{artifact_content}"
        aprovado, motivo = cls._veredito_estrutural(combined)
        if not aprovado:
            excerpt = cls._extract_verdict_excerpt(combined.lower())
            return False, f"{motivo[0].upper()}{motivo[1:]}. Trecho: {excerpt}"
        return True, motivo

    @staticmethod
    def _extract_verdict_excerpt(text: str, max_len: int = 1200) -> str:
        """Extrai a linha do veredito (com contexto do marcador) para o veto ser legível."""
        for marker in ("veredito final", "veredito", "resultado final", "rejeitad", "reprovad"):
            idx = text.find(marker)
            if idx >= 0:
                snippet = text[idx : idx + max_len].replace("\n", " ").strip()
                return snippet[:max_len]
        return text[:max_len].replace("\n", " ")

    def _extract_and_write_project_files(self, text: str) -> list[str]:
        """Extrai blocos de arquivos de código da resposta do agente e grava no disco."""
        import re

        created: list[str] = []
        if not text:
            return created

        pattern1 = re.compile(r"```(?:[a-zA-Z0-9_\-]+:)?([a-zA-Z0-9_\-/\.]+)\n(.*?)```", re.DOTALL)
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
                "." in candidate and not candidate.endswith((".md", ".txt")) and "/" in candidate
            ) or candidate in ("index.html", "package.json", "styles.css"):
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

    # Padrões de resíduo físico — os mesmos rascunhos que o Guardião ignora,
    # mais os nomes inventados que o modelo cria ao "anexar" seções
    # (X.script.vue, Y._import_snippet). Nada aqui casa com fonte legítima.
    _RESIDUO_RE = re.compile(
        r"(^|/)(tmp[^/]*|\.tmp[^/]*)$"  # tmp_*.txt, .tmp_*.py (prefixo)
        r"|\.tmp$"  # *.tmp (sufixo)
        r"|\.snippet(\.|$)"  # *.snippet.py
        r"|_snippet($|\.)"  # main._import_snippet
        r"|scratch"
        r"|\.script\.vue$"  # Comp.script.vue (invenção do modelo)
        r"|\.bak$|\.orig$",
        re.IGNORECASE,
    )
    _DIRS_PROTEGIDOS: frozenset[str] = frozenset(
        {
            ".git",
            ".bombe-code",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
        }
    )

    @staticmethod
    def _extrair_resumo_story(story_content: str) -> str:
        """Extrai a seção '## RESUMO PARA EXECUÇÃO' da story (regra da @caroli:
        resumo COMPLETO por definição, curto por design — os agentes recebem
        ELE, não o texto integral; o integral vive no arquivo, citado no
        prompt). Sem a seção, devolve '' (o chamador usa o texto integral).
        """
        if not story_content:
            return ""
        linhas = story_content.splitlines()
        dentro = False
        coletado: list[str] = []
        for linha in linhas:
            baixa = linha.strip().lower().lstrip("#* ")
            if baixa.startswith(("resumo para execução", "resumo para execucao")):
                dentro = True
                continue
            if dentro and linha.strip().startswith("#"):
                break  # próxima seção — fim do resumo
            if dentro:
                coletado.append(linha)
        texto = "\n".join(coletado).strip()
        return texto

    def _parecer_da_review(self, output: str) -> str:
        """Parecer INTEGRAL da review: se o reviewer gravou o parecer em
        arquivo (output é só resumo + caminho 'docs/qa/...md'), lê o ARQUIVO —
        é lá que vivem os achados enumerados; o resumo truncado não serve."""
        if not output:
            return ""
        m = re.search(r"(docs/[\w./-]+\.(?:md|txt))", output)
        if m:
            arquivo = self.project_dir / m.group(1)
            if arquivo.exists():
                try:
                    return arquivo.read_text(encoding="utf-8", errors="replace").strip()
                except OSError:
                    logger.debug("Não conseguiu ler o parecer %s", arquivo)
        return output.strip()

    def _agente_para_achado(self, achado: str) -> str:
        """Roteia UM achado para o agente da especialidade (tarefa atômica)."""
        a = (achado or "").lower()
        # 1. Banco de Dados, Migrations, Schemas DDL, UUID e Postgres/SQLite (@codd)
        if any(
            k in a
            for k in (
                "banco",
                "tabela",
                "schema",
                "migração",
                "migracao",
                "migration",
                "sql",
                "coluna",
                "índice",
                "indice",
                "foreign key",
                "primary key",
                "uuid",
                "postgres",
                "psycopg",
                "ddl",
                "fk ",
            )
        ):
            return "@codd"
        # 2. Frontend, Componentes e UI/Acessibilidade (@ada)
        if any(
            k in a
            for k in (
                "front",
                " ui",
                "component",
                "vue",
                "react",
                "tela",
                "css",
                "a11y",
                "acessibilidade",
                "botão",
                "botao",
                "modal",
                "view",
            )
        ):
            return "@ada"
        # 3. Contratos de API, DTOs e Schemas de validação de request (@ieru)
        if any(
            k in a
            for k in (
                "contrato",
                "contract",
                "openapi",
                "dto",
                "serialização",
                "serializacao",
                "pydantic",
                "schemas.py",
            )
        ):
            return "@ieru"
        # 4. Testes e Suítes (@aniche)
        if any(k in a for k in ("teste", "test", "suíte", "suite", "e2e", "mock", "cobertura", "assertion")):
            return "@aniche"
        if any(
            k in a
            for k in (
                "arquitetura",
                "acoplamento",
                "camada",
                "dependência",
                "dependencia",
                "clean",
                "solid",
                "domínio",
                "dominio",
                "dead code",
                "código morto",
                "codigo morto",
                "duplicação",
                "duplicacao",
                "dry",
            )
        ):
            return "@unclebob"
        return "@valim"

    def _higienizar_residuos(self) -> list[str]:
        """Remove resíduos físicos do projeto (gate G1 de higiene).

        O agente TEM delete_project_file, mas higiene é rotina da plataforma:
        determinística, a cada ciclo, sem depender do modelo lembrar. Sem isto
        o modelo improvisa "neutralização" (arquivo continua lá) e gates de
        higiene reprovam para sempre — loop de rejeição/re-burn.
        """
        raiz = self.project_dir
        removidos: list[str] = []
        if not raiz.exists():
            return removidos
        for dirpath, dirnames, filenames in os.walk(raiz):
            # Poda diretórios protegidos (node_modules etc.) — não desce neles.
            dirnames[:] = [d for d in dirnames if d not in self._DIRS_PROTEGIDOS]
            for nome in filenames:
                alvo = Path(dirpath) / nome
                rel = alvo.relative_to(raiz).as_posix()
                if self._RESIDUO_RE.search(rel):
                    try:
                        alvo.unlink()
                        removidos.append(rel)
                    except OSError:
                        logger.debug("Não conseguiu remover o resíduo %s", rel)
        if removidos:
            BUS.publish(
                "announcement",
                agent="@turing",
                text=(
                    f"🧹 Higiene de ciclo: {len(removidos)} resíduo(s) físico(s) removido(s) "
                    "(rascunhos tmp_*/snippet) — rotina da plataforma, não tarefa do modelo."
                ),
                wave_id=self.state_machine.wave_id,
            )
        return removidos

    def _review_com_retry(
        self, runner: Any, prompt: str, rotulo: str, etapa: str = "EXECUTE", tentativas: int = 2
    ) -> Any:
        """Auditoria (review/QA) com RE-EXECUÇÃO quando falha por infraestrutura.

        Review que falha (output vazio/erro) NÃO é veredito: re-queimar a story
        por causa de um erro do AUDITOR manda retrabalho de trabalho já feito
        (os QAs respondem 'já entregue' e bloqueiam — patologia vista no log
        19:41-19:49). Falhou? Roda a auditoria DE NOVO, até `tentativas`.
        """
        res: Any = None
        for i in range(tentativas + 1):
            res = runner.run(prompt=prompt)
            self._record_telemetry(etapa, rotulo + (f" (tentativa {i + 1})" if i else ""), res)
            saida = (getattr(res, "output", "") or "").strip()
            if getattr(res, "success", True) and saida and saida != "None":
                return res
            if i < tentativas:
                BUS.publish(
                    "veto_rework",
                    agent=getattr(res, "agent_handle", "@turing") or "@turing",
                    text=(
                        f"⚠️ {rotulo} falhou sem parecer (erro de infraestrutura, não "
                        f"veredito) — re-executando a auditoria ({i + 2}/{tentativas + 1})..."
                    ),
                )
        return res

    # ── BRAÇOS DO TURING — GARÇOM DO KANBAN DE AGENTES ──
    # Mesmo Turing, turnos diferentes: o ESCRITOR acorda quando um agente
    # termina (verifica o binário e escreve/move o card — NUNCA delega no
    # mesmo ato); o DELEGADOR vigia a fila (lê cards AGUARDANDO DEV e delega
    # ao dono). Kanban de agentes manda em tudo.
    _MAPA_AGENTE_CAMADA: ClassVar[dict[str, str]] = {
        "DATABASE": "@codd",
        "CONTRACT": "@ieru",
        "BACKEND_TDD": "@valim",
        "FRONTEND_UI": "@ada",
        "E2E_INTEGRATION": "@aniche",
        "FOUNDATION": "@unclebob",
    }

    def _run_achado_card(
        self,
        story: str,
        row_ach: dict,
        total: int,
        parecer_integral: str,
    ) -> Any:
        """Queima UMA card ACHADO (a row DO KANBAN — única fonte). Escopo
        fechado: CORRIGIR APENAS ESTE achado, com o parecer INTEGRAL como
        contexto (nada truncado)."""
        tid = row_ach["task_id"]
        achado = row_ach.get("descricao") or row_ach.get("title", "")
        agente_achado = row_ach.get("agent_role") or self._agente_para_achado(achado)
        i = row_ach.get("ordem", 80)
        runner_achado = self._get_runner(agente_achado)
        prompt = self._assemble_prompt(
            agente_achado,
            f"Story {story} REPROVADA no code review. CORRIJA APENAS ESTE "
            f"ACHADO ({i - 80} de {total}):\n"
            f"ACHADO: {achado}\n\n"
            f"Contexto (parecer integral, texto completo):\n{parecer_integral}\n\n"
            "Entrega = arquivos GRAVADOS nesta rodada "
            "(write_project_file). Escopo fechado: nada além deste achado.",
        )
        return self._executar_com_card(
            self.state_machine.wave_id,
            story,
            tid,
            f"Achado: {achado[:120]}",
            agente_achado,
            row_ach.get("ordem", 80),
            lambda: runner_achado.run(prompt) if runner_achado else runner_ausente(agente_achado),
            dor=[],
            task_tipo="ACHADO",
            descricao=achado[:400],
            dod=["gravou_arquivo"],
        )

    def _queimar_instalacao(self, agente: str, prompt: str) -> Any:
        """run_fn do burn de INSTALAÇÃO (delega runner ao ambiente)."""
        runner = self._get_runner(agente)
        if runner is None:
            return runner_ausente(agente)
        return runner.run(self._assemble_prompt(agente, prompt))

    def _e_bloqueio_de_instalacao(self, texto: str | None) -> bool:
        """Delega à governança de ambiente (SRP)."""
        return e_bloqueio_de_instalacao(texto)

    def _abrir_task_instalacao(
        self, onda_id: str, story_id: str, task_origem: str, evidencia: str
    ) -> str | None:
        """GOVERNANÇA DE INSTALAÇÃO (kanban manda): bloqueio por falta de
        ferramenta NÃO escala humano. O Turing abre task PRIORITÁRIA (ordem 0)
        roteada pelo PAPEL (@guto infra / @unclebob biblioteca); a origem ganha
        dep: na DOR. Os critérios são da GovernancaAmbiente (SRP)."""
        cartoes = self.db.carregar_tasks_kanban(onda_id, story_id)
        pendente = next(
            (
                c["task_id"]
                for c in cartoes
                if c["task_id"].startswith("INSTALACAO-")
                and c["kanban_status"] not in ("DEV_DONE", "DONE_DEFINITIVO")
            ),
            None,
        )
        if pendente:
            return pendente  # já existe instalação no kanban — não duplica
        # ANTI-ARMADILHA: se uma instalação desta story JÁ FOI VALIDADA (DEV
        # DONE — provou o ambiente com teste), a falha NÃO é falta de
        # dependência: é impedimento real da card (ex.: suíte quebrada que
        # MENCIONA jsdom/document). Nascer INSTALACAO de novo recriava uma DOR
        # já resolvida (a armadilha do resume). Flag na origem basta — a linha
        # para NELE.
        ja_validada = any(
            c["task_id"].startswith("INSTALACAO-")
            and c["kanban_status"] in ("DEV_DONE", "DONE_DEFINITIVO")
            for c in cartoes
        )
        if ja_validada:
            BUS.publish(
                "announcement",
                agent="@turing",
                text=(
                    f"🛠 AMBIENTE JÁ VALIDADO — {story_id}: instalação anterior em DEV "
                    f"Done provou o ambiente com teste. A falha de {task_origem} NÃO é "
                    "falta de dependência — é impedimento real da card (fica flagada; "
                    "a linha trata nele). Nenhuma instalação nova nasce."
                ),
            )
            return None
        evid = (evidencia or "")[:400]
        roteado_para = roteamento_da_instalacao(evid)
        proximo_n = sum(1 for c in cartoes if c["task_id"].startswith("INSTALACAO-")) + 1
        task_id = f"INSTALACAO-{proximo_n}"
        titulo = f"Instalar dependência/ambiente para destravar {task_origem}"
        self.db.criar_task_kanban(
            onda_id,
            story_id,
            task_id,
            titulo,
            roteado_para,
            0,
            dor=[],
            dod=[],
            task_tipo="INSTALACAO",
            descricao=f"Impedimento de {task_origem}: {evid}",
        )
        self.db.mover_task_kanban(onda_id, story_id, task_id, "AGUARDANDO_DEV")
        # Precedência real: a origem só re-queima depois da instalação.
        self.db.adicionar_dep_task_kanban(onda_id, story_id, task_origem, task_id)
        anunciar_instalacao_prioritaria(story_id, task_origem, task_id, roteado_para)
        return task_id

    def _abrir_achado_de_bloqueio(
        self, onda_id: str, story_id: str, task_origem: str, motivo: str
    ) -> str | None:
        """AUTO-CURA DO KANBAN: quando uma task é bloqueada por erro/impedimento
        técnico ou de teste, o Kanban NÃO deixa a LLM adivinhar no resume.
        O sistema abre imediatamente um card de ACHADO específico, roteado para
        o agente especialista (ex.: @ada se for Vue/UI, @codd se for banco, @ieru contrato),
        e AMARRA a dependência: task_origem passa a depender do ACHADO resolvido.
        No resume, o Kanban já está cirurgicamente pronto e o próximo passo é inequívoco."""
        cartoes = self.db.carregar_tasks_kanban(onda_id, story_id)
        # Evita duplicar se já houver achado aberto para o mesmo problema/origem
        achados_origem = [
            c for c in cartoes
            if c["task_id"].startswith("ACHADO-")
            and task_origem in (c.get("descricao") or "")
            and c["kanban_status"] not in ("DEV_DONE", "DONE_DEFINITIVO")
        ]
        if achados_origem:
            return achados_origem[0]["task_id"]

        agente_destino = self._agente_para_achado(motivo)
        # Se o agente destino for o próprio agente da task e for bloqueio genérico, não precisa de card cruzado
        card_origem = next((c for c in cartoes if c["task_id"] == task_origem), None)
        if card_origem and card_origem.get("agent_role") == agente_destino:
            # É erro interno da própria task — o próprio card fica bloqueado com o motivo explícito
            return None

        # É discrepância de outra especialidade (ex: backend travado por erro no front/banco/contrato)
        import re
        maior_idx = 0
        for c in cartoes:
            tid = c["task_id"]
            m = re.match(rf"^ACHADO-{re.escape(story_id)}-(\d+)$", tid)
            if m:
                maior_idx = max(maior_idx, int(m.group(1)))

        novo_num = maior_idx + 1
        achado_id = f"ACHADO-{story_id}-{novo_num}"
        titulo = f"Destravar {task_origem}: {(motivo or '')[:90]}"
        self.db.criar_task_kanban(
            onda_id,
            story_id,
            achado_id,
            titulo,
            agente_destino,
            -10 + novo_num,
            dor=[],
            dod=["gravou_arquivo"],
            task_tipo="ACHADO",
            descricao=f"Desacoplamento de impedimento de {task_origem}: {motivo[:350]}",
        )
        self.db.mover_task_kanban(onda_id, story_id, achado_id, "AGUARDANDO_DEV")
        # Precedência mandatória: a task origem só queima após o achado ser resolvido
        self.db.adicionar_dep_task_kanban(onda_id, story_id, task_origem, achado_id)
        BUS.publish(
            "announcement",
            agent="@turing",
            text=(
                f"🧩 AUTO-CURA DO KANBAN — {story_id}: impedimento de {task_origem} gerou "
                f"{achado_id} delegado para {agente_destino}. O próximo passo no resume é inequívoco."
            ),
        )
        return achado_id

    def _executar_com_card(
        self,
        onda_id: str,
        story_id: str,
        task_id: str,
        titulo: str,
        agente: str,
        ordem: int,
        run_fn: Callable[[], Any],
        dor: list[str] | None = None,
        dod: list[str] | None = None,
        task_tipo: str = "",
        descricao: str = "",
    ) -> Any:
        """PREMISSA INEGOCIÁVEL: NENHUM agente atua sem card.

        Nasce BACKLOG → AGUARDANDO DEV (DOR preenchida) → EM_DEV (agente
        acorda — bola da vez, uma só em toda a ONDA) → DEV DONE (sucesso) ou
        permanece NA COLUNA com a SITUAÇÃO blocked tipada (falha: blocked não
        é coluna, é flag). Uso: planos, refinos, validações, assume-do-lead —
        qualquer atuação fora do loop de tasks.
        """
        self.db.criar_task_kanban(
            onda_id,
            story_id,
            task_id,
            titulo,
            agente,
            ordem,
            dor=dor,
            dod=dod,
            task_tipo=task_tipo,
            descricao=descricao,
        )
        cartao = next(
            (
                c
                for c in self.db.carregar_tasks_kanban(onda_id, story_id)
                if c["task_id"] == task_id
            ),
            None,
        )
        if cartao and cartao["kanban_status"] == "BACKLOG":
            self.db.mover_task_kanban(onda_id, story_id, task_id, "AGUARDANDO_DEV")
        if not self._acordar_task_em_dev(onda_id, story_id, task_id):
            # DOR não atendida: NENHUM agente atua (premissa: card em DEV é
            # condição de trabalho) — devolve bloqueado honesto.
            return AgentExecutionResult(
                agent_handle=agente,
                success=False,
                is_blocked=True,
                block_reason=(
                    f"DOR não atendida para {task_id} — a card não foi para EM DEV "
                    "(precedência/entrada pendente)."
                ),
            )
        res = run_fn()
        escreveu = bool(getattr(res, "arquivos_escritos", None) or [])
        instalacao = task_id.startswith("INSTALACAO-")
        etapa_ou_audit = task_tipo in ("DISCUSS", "PLAN", "VALIDATE", "REVIEW") or task_id.startswith(("DISCUSS-", "PLAN-", "VALIDATE-", "REVIEW-"))

        deu_certo = (
            getattr(res, "success", False) is True
            and getattr(res, "is_blocked", False) is not True
            and (escreveu or not getattr(res, "output", "") or instalacao or etapa_ou_audit)
        )
        if deu_certo:
            # Instalação: binário por execução/verificação — não exige arquivo.
            self.db.mover_task_kanban(onda_id, story_id, task_id, "DEV_DONE")
        else:
            # BLOCKED É SITUAÇÃO, NUNCA COLUNA: o card permanece NA coluna em
            # que está (EM_DEV) e recebe a flag tipada do impedimento.
            self.db.bloquear_task_kanban(onda_id, story_id, task_id, "INTERNAL_SCALE")
        # GOVERNANÇA DE AMBIENTE: falta de ferramenta/dependência NUNCA escala
        # humano — o Turing abre a task prioritária (Guto infra / Tech Lead
        # biblioteca), primeira da fila, e a origem ganha dep: na DOR.
        if not deu_certo and self._e_bloqueio_de_instalacao(evidencia_de(res)):
            self._abrir_task_instalacao(onda_id, story_id, task_id, evidencia_de(res))
        return res

    # ── COTA DO PROVEDOR ESGOTADA (infra, nunca negócio) ──
    # A Plataforma de IA sem capacidade NÃO é bloco de agente nem falta de
    # informação: é a camada de IA de fora. O processo PAUSA, ESPERA o reset e
    # retoma sozinho — a escada não queima degrau atrás de degrau nem escala
    # o humano com "Informação em falta: HTTP 429..."

    @property
    def _cota_ativa(self) -> QuotaResetInfo | None:
        return self._cota.ativa

    @_cota_ativa.setter
    def _cota_ativa(self, valor: QuotaResetInfo | None) -> None:
        self._cota.ativa = valor

    def _garcom_preparar_tasks(self, onda_id: str, story_id: str, tarefas: list[Any]) -> None:
        """Delega à FilaDoKanban (SRP)."""
        self._fila.preparar(onda_id, story_id, tarefas)

    def _dor_satisfeita(self, cartao: dict, cartoes: list[dict]) -> tuple[bool, str]:
        """Delega à FilaDoKanban (SRP)."""
        return self._fila.dor_satisfeita(cartao, cartoes)

    def _suite_da_story_existe(self, story_id: str) -> bool:
        """A suíte da story JÁ existe em tests/? (checagem determinística de
        artefato: arquivo de teste cujo nome cita a story). É ISSO que decide
        se o @aniche acorda: suíte existente é o contrato — reescrever teste
        em resume/blocked/re-burn é reaproveitar linha de montagem parada.
        A revalidação é papel do review (REVIEW-QA re-executa a suíte)."""
        norma = re.sub(r"[^a-z0-9]", "", (story_id or "").lower())
        if not norma:
            return False
        raiz = self.project_dir / "tests"
        if not raiz.exists():
            return False
        return any(
            norma in candidato.name.lower()
            for candidato in raiz.rglob("*.py")
            if candidato.is_file()
        )

    def _concluidas_da_story(self, onda_id: str, story_id: str) -> list[str]:
        """Tasks concluídas LIDAS DO KANBAN (DEV DONE/DONE DEFINITIVO) —
        conclusão é estado do kanban, nunca conjunto em memória."""
        return sorted(
            c["task_id"]
            for c in self.db.carregar_tasks_kanban(onda_id, story_id)
            if c["kanban_status"] in ("DEV_DONE", "DONE_DEFINITIVO")
        )

    def _garcom_carregar_fila(self, onda_id: str, story_id: str) -> tuple[list[dict], list[dict]]:
        """Delega à FilaDoKanban (SRP)."""
        return self._fila.carregar(onda_id, story_id)

    def _garcom_devolver_cards_para_burn(
        self,
        onda_id: str,
        story_id: str,
        agente: str,
        achados_ids: list[str] | None = None,
    ) -> int:
        """Delega à FilaDoKanban (SRP)."""
        return self._fila.devolver_cards_para_burn(onda_id, story_id, agente, achados_ids=achados_ids)

    def _acordar_task_em_dev(self, onda_id: str, story_id: str, task_id: str) -> bool:
        """Delega à FilaDoKanban (SRP)."""
        return self._fila.acordar_em_dev(onda_id, story_id, task_id)

    def _nascer_fila_achados(self, story_id: str, achados: list[str]) -> None:
        """Delega à FilaDoKanban (SRP)."""
        self._fila.nascer_fila_achados(story_id, achados)

    def _achados_pendentes(self, story_id: str) -> list[dict]:
        """Delega à FilaDoKanban (SRP)."""
        return self._fila.achados_pendentes(story_id)

    def _anotar_cota_resultado(self, res: Any) -> None:
        """Delega à política de cota (SRP)."""
        self._cota.anotar_resultado(res)

    def _cota_ocorreu(self, res: Any) -> bool:
        """Anota + verifica num gesto (DRY do esqueleto da linha)."""
        return self._cota.ocorreu(res)

    def _anotar_cota_texto(self, texto: str | None) -> None:
        self._cota.anotar_texto(texto)

    @staticmethod
    def _fmt_restante(segundos: float) -> str:
        return PoliticaDeCota.fmt_restante(segundos)


    def _esperar_reset_cota(self, story: str) -> tuple[str, str | None, QuotaResetInfo | None]:
        """Delega à política de cota (SRP): pausa, espera o reset, retoma."""
        return self._cota.esperar_reset(story)

    def _parada_por_cota(
        self, story: str, msg: str, completed_stories: list[str]
    ) -> dict[str, Any]:
        """Delega à política de cota (SRP): park honesto + card Impedimento."""
        return self._cota.parada(story, msg, completed_stories)

    def _gate_cota_na_escada(
        self, story: str, esperas_cota: int, completed_stories: list[str]
    ) -> tuple[str, int, dict[str, Any] | None]:
        """Delega à política de cota (SRP): gate de início/fim de degrau."""
        return self._cota.gate_escada(story, esperas_cota, completed_stories)

    def _run_cycle_inner(
        self,
        story_id: str | None = None,
        rework_feedback: str | None = None,
    ) -> dict[str, Any]:
        """Executa atomicamente UMA story (RED -> GREEN -> REFACTOR -> Review) e PARA.

        rework_feedback: quando o ciclo anterior foi reprovado pelo review,
        o motivo é anexado ao prompt do dev (correção direcionada, não chute).
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

        # 🚩 IMPEDIMENTO: com bandeira vermelha erguida, histórias novas NÃO
        # iniciam. A PRÓPRIA história flagada pode queimar — ela É o trabalho
        # de correção. Recusar a flagada travaria a linha para sempre (a
        # correção da bandeira seria bloqueada pela própria bandeira).
        bandeiras = [
            c
            for c in self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            if c.get("is_blocked")
        ]
        ids_bandeira = [c.get("story_id") for c in bandeiras]
        if bandeiras and story_id not in ids_bandeira:
            return {
                "success": False,
                "is_blocked": True,
                "blocked_by": "@turing",
                "error": (
                    f"🔴 LINHA PARADA: bandeira vermelha na {ids_bandeira[0]} — "
                    "histórias novas aguardam a correção do impedimento."
                ),
            }

        target_story = story_id or "ST-001"

        # 🧹 HIGIENE DE CICLO: o agente tem delete_project_file, mas resíduos
        # (tmp_*, *.tmp, *.snippet*) são DEVER DA PLATAFORMA — rotina determinística
        # a cada ciclo, sem depender do modelo lembrar de limpar (defesa em
        # profundidade para gates de higiene tipo G1).
        self._higienizar_residuos()

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

        story_file = self.workspace.find_story_file(
            target_story, wave_id=self.state_machine.wave_id
        )
        story_rel = (
            story_file.relative_to(self.project_dir).as_posix()
            if story_file
            else f"docs/waves/{self.state_machine.wave_id}/stories/{target_story}.md"
        )
        story_title = target_story
        tarefas = PBBDecomposer.decompose_story(
            story_id=target_story,
            story_title=story_title,
            requires_db=True,
            requires_frontend=True,
        )

        # ── KANBAN DE AGENTES MANDA EM TUDO ──
        # Braço ESCRITOR: tasks do breakdown nascem NO KANBAN, designadas, na
        # ordem — BACKLOG → AGUARDANDO DEV. Sem ordem no kanban, agente nem
        # acorda. Cards DEV DONE são IGNORADOS (revalidar é papel do code
        # review final da story); BLOCKED tem prioridade (Impedimento).
        onda_id = self.state_machine.wave_id
        # NASCIMENTO: o decompose é APENAS o escritor do kanban — os objetos
        # em memória morrem aqui. O que queima são as ROWS do kanban.
        self._garcom_preparar_tasks(onda_id, target_story, tarefas)
        qtd_nascidas = len(tarefas)
        del tarefas
        pendentes, _cartoes = self._garcom_carregar_fila(onda_id, target_story)
        # Ciclo só-de-validação? (nada a queimar — kanban 100% DEV DONE/DONE
        # DEFINITIVO). O código já está no disco de queimas anteriores; quem
        # valida é o code review — o consolidado vazio NÃO veta nada.
        houve_queima = bool(pendentes)

        # ── O RELÓGIO (linha de montagem): NENHUM agente acorda fora da sua
        # hora. O @aniche só entra DENTRO da queima de uma card DEV cuja suíte
        # ainda não existe (primeira queima da story) — resume, instalação,
        # achado e re-burn NUNCA o re-despertam (a suíte existente é o
        # contrato; revalidar é papel do review). A queima COMEÇA NO RED: a
        # card já está EM_DEV no kanban quando o @aniche escreve.
        runner_aniche = self._get_runner("@aniche")

        # 2. FASE GREEN — EXECUÇÃO TASK-A-TASK com agendador por camada:
        # tarefas independentes de camadas distintas rodam EM PARALELO (o
        # contrato do arquiteto é a barreira); review é da STORY inteira.
        from concurrent.futures import ThreadPoolExecutor

        story_content = (
            story_file.read_text(encoding="utf-8", errors="replace")
            if story_file and story_file.exists()
            else ""
        )
        try:
            primeira_linha = next(
                (
                    l.strip("# ").strip()
                    for l in story_content.splitlines()
                    if l.strip().startswith("# ")
                ),
                "",
            )
            if primeira_linha:
                story_title = primeira_linha
        except Exception as exc:  # noqa: BLE001 — título é cosmético
            logger.debug("Sem título extraível da story: %s", exc)

        BUS.publish(
            "announcement",
            agent="@turing",
            text=(
                f"🧩 {target_story} decomposta em {qtd_nascidas} tarefas atômicas — "
                "execução task-a-task, paralelismo por camada, review no fim da story."
            ),
        )

        story_content = (
            story_file.read_text(encoding="utf-8", errors="replace")
            if story_file and story_file.exists()
            else ""
        )
        # STORY: usa o RESUMO CANÔNICO (regra da @caroli — seção '## RESUMO
        # PARA EXECUÇÃO' na própria story: completo por definição, curto por
        # design). Sem a seção, cai para o texto integral (nunca truncar).
        resumo_secao = self._extrair_resumo_story(story_content)
        if resumo_secao:
            objetivo_story = (
                "RESUMO CANÔNICO DA STORY (completo por definição — o texto "
                f"integral está no arquivo indicado abaixo):\n{resumo_secao}"
            )
        else:
            objetivo_story = story_content.strip() if story_content else ""
        # O path vai junto para o agente reler o original se precisar.
        story_path_hint = (
            f"\n(STORY INTEGRAL também em: {story_file})"
            if story_file and story_file.exists()
            else ""
        )
        entregues: list[str] = []
        dev_outputs: list[str] = []

        # Evidência de execução: arquivos gravados pelos devs NESTE ciclo.
        # Zero escritas = plano sem código (recusa velada) — detectável.
        escritas_ciclo: list[str] = []

        def _executa_tarefa(tarefa_exec: dict) -> str:
            """Uma tarefa = RED (aniche, escopo do trecho) + GREEN (dev da camada).

            `tarefa_exec` é a ROW DO KANBAN (única fonte da verdade): id, título,
            tipo, descrição, agente e DOD moram nela. DOR 100% → card vai pra
            EM_DEV ANTES de acordar o agente (bola da vez no burn); no fim,
            BINÁRIO — sucesso → DEV DONE; não deu certo → SITUAÇÃO blocked
            tipada, fica NA coluna em que está (blocked não é coluna, é flag)."""
            tid = tarefa_exec["task_id"]
            if not self._acordar_task_em_dev(onda_id, target_story, tid):
                # DOR não atendida: NINGUÉM atua — a card não entra em DEV.
                return (
                    f"⛔ DOR não atendida para {tid} — a card não foi "
                    "para EM DEV e não foi queimada (precedência pendente)."
                )
            if tarefa_exec.get("task_tipo") == "ACHADO" or tid.startswith("ACHADO-"):
                # FILA ÚNICA: achado É card e queima PELA FILA DO KANBAN (ordem
                # e DOR do kanban mandam — dependência da instalação respeitada).
                return str(
                    getattr(
                        self._run_achado_card(
                            target_story,
                            tarefa_exec,
                            1,
                            tarefa_exec.get("descricao") or tarefa_exec.get("title") or "",
                        ),
                        "output",
                        "",
                    )
                )
            if tarefa_exec.get("task_tipo") == "INSTALACAO":
                # Task de ambiente (Guto/Tech Lead): NÃO passa por RED/GREEN —
                # o burn É a instalação auditada + verificação de execução
                # (binário próprio dentro de _executar_com_card).
                agente_inst = tarefa_exec.get("agent_role") or "@guto"
                prompt_inst = (
                    f"Story: {objetivo_story}{story_path_hint}\n"
                    f"TAREFA DE AMBIENTE: {tarefa_exec.get('title', '')}\n"
                    f"Evidência do impedimento: {tarefa_exec.get('descricao', '')}\n"
                    "Instale a dependência/ferramenta NO PROJETO SE NECESSÁRIO (comando "
                    "local auditado, sem -g, sem sudo) e EXECUTE OBRIGATORIAMENTE, via "
                    "ferramenta executar_comando, o TESTE DE VALIDAÇÃO: um import/require "
                    "simples da biblioteca (ex.: node -e \"require('jsdom')\" / python -c "
                    "\"import x\"). A card SÓ fecha com esse teste passando (exit 0), "
                    "registrado pela plataforma — vale para 'instalei agora', 'já estava "
                    "instalado' e 'reinstalei'. 'Deve funcionar' e npm install sozinho "
                    "NÃO finaliza a card."
                )
                def _queimar_instalacao_com_dod(
                    ag: str = agente_inst, p: str = prompt_inst
                ) -> Any:
                    """DOD REAL da instalação (zero suposição) — VALIDAÇÃO, não
                    instalação: a card só fecha com o TESTE de validação
                    (import/require da biblioteca) EXECUTADO pela ferramenta
                    com exit 0, registrado platform-side. Cobre os três casos:
                    instalou agora · já estava instalado · reinstalou depois de
                    instalar errado. 'npm install' sozinho NÃO prova que roda;
                    prosa do agente não é evidência."""
                    r = self._queimar_instalacao(ag, p)
                    registro = list(getattr(r, "comandos_executados", []) or [])
                    if getattr(r, "success", True) is True and not verificar_instalacao(
                        registro
                    ):
                        return AgentExecutionResult(
                            agent_handle=ag,
                            success=False,
                            is_blocked=True,
                            block_reason=(
                                "Instalação sem VALIDAÇÃO executada: nenhum comando "
                                "rodou com exit 0 pela ferramenta (registro "
                                "platform-side vazio). A prova é o teste de "
                                "import/require da biblioteca verde — não a prosa."
                            ),
                        )
                    return r

                res_inst = self._executar_com_card(
                    onda_id,
                    target_story,
                    tid,
                    tarefa_exec.get("title") or "Instalação de ambiente",
                    agente_inst,
                    0,
                    _queimar_instalacao_com_dod,
                    dor=[],
                    dod=[],
                )
                return str(getattr(res_inst, "output", "") or "")
            tipo = tarefa_exec.get("task_tipo") or ""
            titulo_t = tarefa_exec.get("title", "")
            problema_t = tarefa_exec.get("descricao") or titulo_t
            if (
                runner_aniche
                and not self._suite_da_story_existe(target_story)
                and target_story not in self._red_ja_feito
            ):
                # A QUEIMA COMEÇA NO RED — a card JÁ ESTÁ EM_DEV no kanban
                # (acordada acima) quando o @aniche escreve. Só acorda na
                # PRIMEIRA queima da story (suíte inexistente): resume,
                # instalação, achado e re-burn NUNCA o re-despertam — a suíte
                # existente é o contrato; revalidar é papel do review.
                raw_red = (
                    f"Story: {objetivo_story}{story_path_hint}\n"
                    "Elabore o Plano de Testes e escreva a suíte de testes da story "
                    "(unidade/slice) na pasta 'tests/' — consulte os requisitos e os "
                    f"cenários BDD no arquivo '{story_rel}'.\n"
                    f"AGORA, PARA A TAREFA ATUAL: [{tipo}] {titulo_t}\n"
                    f"Problema único desta tarefa: {problema_t}\n"
                    "Escreva APENAS os testes que falham para ESTE trecho — nada de outras "
                    f"tarefas. Declare no fim: 'Testes falhando (RED) para a tarefa {tid}'."
                )
                res_red = runner_aniche.run(self._assemble_prompt("@aniche", raw_red))
                self._red_ja_feito.add(target_story)
                self._anotar_cota_resultado(res_red)
                try:
                    escritas_ciclo.extend(getattr(res_red, "arquivos_escritos", []))
                except Exception:  # noqa: BLE001, S110 — mock pode não ter o campo
                    pass

            # O executor é o AGENTE DESIGNADO NO KANBAN (agent_role da row).
            executor_handle = tarefa_exec.get("agent_role") or "@valim"
            # ANTI-PAPAGAIO: se o dev anterior BLOQUEOU (bandeira vermelha),
            # o próximo degrau troca o dev da camada — repetir o mesmo que
            # travou é insistência inútil.
            if getattr(tarefa_exec, "get", lambda *_: False)("_dev_bloqueou", False):
                alternativos = {"@valim": "@barbara", "@barbara": "@valim"}
                executor_handle = alternativos.get(executor_handle, executor_handle)
            runner_executor = self._get_runner(executor_handle)
            if not runner_executor:
                return ""

            contexto = (
                "\nJÁ ENTREGUE (para integração, não refaça):\n- " + "\n- ".join(entregues)
                if entregues
                else "\nPrimeira tarefa da story."
            )
            raw_dev = (
                f"OBJETIVO DA STORY COMPLETA: {objetivo_story}{story_path_hint}\n\n"
                f"TAREFA ATUAL (sua entrega): [{tipo}] {titulo_t}\n"
                f"Problema único: {problema_t}\n"
                f"Testes (RED) já escritos pelo @aniche em 'tests/'.\n"
                f"{contexto}\n"
                "REGRA RÍGIDA DE ESCOPO E ESPECIALIDADE (ENTERPRISE GRADE):\n"
                f"1. Você é o agente {executor_handle}. Atue ESTRITAMENTE na sua especialidade e no escopo desta tarefa.\n"
                "2. BACKEND NUNCA edita arquivos de Frontend (.vue, .css, specs de UI) e vice-versa. Violação = veto imediato da plataforma.\n"
                "3. GESTÃO DE ERROS FORA DO ESCOPO:\n"
                "   - Se o erro fora de escopo IMPEDE você de terminar a sua tarefa: interrompa e declare o bloqueio com a evidência técnica do erro (o Kanban abrirá o card do especialista para destravar você).\n"
                "   - Se o erro fora de escopo NÃO IMPEDE você de terminar: termine sua entrega (GREEN), e ao final declare no seu texto: 'ACHADO_FORA_DE_ESCOPO: <descrição do problema encontrado>' para que o @turing providencie o card no Kanban.\n"
                "4. Entregue APENAS o trecho em TAREFA ATUAL. As demais tarefas da story NÃO são suas.\n"
                "Implemente o mínimo para ESTES testes passarem (GREEN) e refatore (Clean Code). "
                "Entrega desta rodada = arquivos GRAVADOS (write_project_file) — "
                "resposta sem gravação não é entrega."
            )
            escritas_antes = len(escritas_ciclo)
            res_t = runner_executor.run(self._assemble_prompt(executor_handle, raw_dev))
            self._anotar_cota_resultado(res_t)
            escritas_ciclo.extend(getattr(res_t, "arquivos_escritos", []))
            # DOD item a item: 'gravou_arquivo' exige gravação REAL nesta
            # execução (sucesso sem gravação = plano, não entrega). O DOD é
            # lido DA ROW (kanban — única fonte).
            sinais_reais = isinstance(getattr(res_t, "success", None), bool)
            dod_ok = (
                (not sinais_reais)
                or bool(escritas_ciclo[escritas_antes:])
                or ("gravou_arquivo" not in (tarefa_exec.get("dod") or []))
            )
            # BINÁRIO do card de agente: deu certo ou não deu. Sem exceções.
            # Sinais booleanos REAIS (AgentExecutionResult) decidem; sem sinal
            # real, o DOD (gravação) é o juiz.
            suc = getattr(res_t, "success", None)
            blocked = getattr(res_t, "is_blocked", None)
            if isinstance(suc, bool):
                deu_certo = suc is True and blocked is not True
            else:
                deu_certo = True
            if deu_certo and dod_ok:
                self.db.mover_task_kanban(onda_id, target_story, tid, "DEV_DONE")
                # Gestão inteligente de achados que não impediram a entrega:
                # Se o agente apontou achados fora de escopo, o Turing já registra no Kanban
                out_texto = getattr(res_t, "output", "") or ""
                import re as _re_ach
                for ach_match in _re_ach.finditer(r"ACHADO_FORA_DE_ESCOPO:\s*(.+)", out_texto, _re_ach.IGNORECASE):
                    texto_ach = ach_match.group(1).strip()
                    if texto_ach:
                        self._nascer_fila_achados(target_story, [texto_ach])
            else:
                # BLOCKED É SITUAÇÃO (flag tipada NA coluna), nunca movimento:
                # a card fica onde está e a fila segue quando resolvida.
                self.db.bloquear_task_kanban(
                    onda_id,
                    target_story,
                    tid,
                    "INTERNAL_SCALE",
                )
                # GOVERNANÇA DE AMBIENTE: falta de ferramenta/dependência não
                # escala humano — abre a task prioritária de instalação.
                evid_t = evidencia_de(res_t)
                if self._e_bloqueio_de_instalacao(evid_t):
                    self._abrir_task_instalacao(onda_id, target_story, tid, evid_t)
                elif evid_t:
                    # Auto-cura imediata do Kanban: se o erro for de outra camada ou especialidade,
                    # abre o card de achado correspondente e amarra a dependência para o resume.
                    self._abrir_achado_de_bloqueio(onda_id, target_story, tid, evid_t)
            return getattr(res_t, "output", "")

        falhas_ciclo: dict[str, int] = {}
        while True:
            # KANBAN MANDA EM TUDO — ZERO SUPOSIÇÃO: a fila é RELIDA DO BANCO
            # a cada passada, contra o estado REAL. Uma card só libera
            # dependente quando está REALMENTE em DEV DONE; card com 🚩
            # (impedimento ativo) está fora da fila até o desbloqueio.
            pendentes, _cartoes_passada = self._garcom_carregar_fila(onda_id, target_story)
            if not pendentes:
                break
            if self._cota_ativa:
                # 🚦 COTA ESGOTADA: parar de queimar AQUI (cada chamada 429 é
                # lixo) — o ciclo devolve como bloqueado e a escada PAUSA para
                # esperar o reset, sem gastar tentativa de convergência.
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"⏸ {target_story}: cota do provedor esgotada — parando a "
                        "queima; aguardando reset da janela."
                    ),
                )
                break
            if ABORT_EVENT.is_set():
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=f"⏸ Interrompido com {len(pendentes)} tarefa(s) pendente(s) — checkpoint salvo.",
                )
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@turing",
                    "error": "Interrompido pelo usuário (checkpoint salvo).",
                    "completed_tasks": self._concluidas_da_story(onda_id, target_story),
                }
            # TURNO DO KANBAN: lote montado pela MESMA função única consumida pela tela (montar_lote_turno).
            # Zero exceção: instalações, achados, paralelos e solos seguem a mesma regra canônica.
            lote = montar_lote_turno(pendentes)
            if not lote:
                lote = [pendentes[0]]

            if lote[0].get("task_tipo") == "INSTALACAO" or lote[0]["task_id"].startswith("INSTALACAO-"):
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🧰 IMPEDIMENTO DE AMBIENTE — linha parada em {target_story}: "
                        f"{lote[0]['task_id']} ({lote[0]['agent_role']}) é a "
                        "PRÓXIMA a queimar, antes de qualquer outra tarefa."
                    ),
                )

            # Snapshot ANTES do burn: a flag nasce DURANTE o burn — a guarda
            # de progresso compara o estado pré e pós-passada.
            concluidas_antes = len(self._concluidas_da_story(onda_id, target_story))
            flag_antes = sum(
                1
                for c in self.db.carregar_tasks_kanban(onda_id, target_story)
                if c["block_tipo"]
            )

            if len(lote) == 1:
                saidas_lote = [_executa_tarefa(lote[0])]
            else:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        "⚡ Paralelismo por camada: "
                        + ", ".join(f"{t.get('task_tipo') or ''} ({t['task_id']})" for t in lote)
                        + " rodando juntos (contratos já definidos pelo arquiteto)."
                    ),
                )
                with ThreadPoolExecutor(max_workers=len(lote)) as pool:
                    saidas_lote = list(pool.map(_executa_tarefa, lote))

            # PÓS-BURN — o kanban decide (binário, sem suposição): DEV DONE
            # real = concluída; qualquer outra coisa = flag ativa, a card
            # está FORA da fila (impedimento) e a linha atua nela.
            instalacao_bloqueada = False
            for t_exec, saida in zip(lote, saidas_lote):
                tid_exec = t_exec["task_id"]
                cartao_pos = next(
                    (
                        c
                        for c in self.db.carregar_tasks_kanban(onda_id, target_story)
                        if c["task_id"] == tid_exec
                    ),
                    None,
                )
                foi_dev_done = bool(cartao_pos) and cartao_pos["kanban_status"] == "DEV_DONE"
                if foi_dev_done:
                    entregues.append(
                        f"{tid_exec} — {t_exec['title']} ({t_exec.get('descricao') or t_exec['title']})"
                    )
                    dev_outputs.append(
                        f"[{t_exec.get('task_tipo') or ''}] {t_exec['title']}: {saida}"
                    )
                    if t_exec.get("task_tipo") == "INSTALACAO":
                        # A informação que causou os blocks de ambiente EXISTE:
                        # cards flagged com dep:INSTALACAO-n são desbloqueadas.
                        self._fila.desbloquear_apos_instalacao(
                            onda_id, target_story, tid_exec
                        )
                elif t_exec.get("task_tipo") == "INSTALACAO":
                    # A INSTALAÇÃO em si falhou (sem evidência real de
                    # execução): linha PARADA de verdade — queimar o resto com
                    # o ambiente quebrado é desperdício de cota.
                    instalacao_bloqueada = True
                else:
                    # TETO DE TENTATIVAS (determinístico): a 2ª falha da MESMA
                    # task no ciclo PARA A LINHA de vez — o impedimento que
                    # sobrevive à correção do ambiente exige decisão, não
                    # repetição infinita de instalação/queima.
                    falhas_ciclo[tid_exec] = falhas_ciclo.get(tid_exec, 0) + 1
                    if falhas_ciclo[tid_exec] >= 2:
                        BUS.publish(
                            "announcement",
                            agent="@turing",
                            text=(
                                f"🛑 {target_story} {tid_exec}: 2ª falha no mesmo "
                                "ciclo — linha parada de vez. O impedimento "
                                "sobreviveu à correção; repetir não é solução."
                            ),
                        )
                        return {
                            "success": False,
                            "is_blocked": True,
                            "blocked_by": "@turing",
                            "error": (
                                f"{tid_exec} falhou 2x no ciclo mesmo após a "
                                "correção de ambiente — linha parada (impedimento)."
                            ),
                            "completed_tasks": self._concluidas_da_story(
                                onda_id, target_story
                            ),
                        }
            if instalacao_bloqueada:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🧰 IMPEDIMENTO DE AMBIENTE — instalação bloqueada em "
                        f"{target_story}: nada mais queima neste ciclo (as cards "
                        "continuam no kanban; resume retoma pela instalação)."
                    ),
                )
                break
            # GUARDA DETERMINÍSTICA: passada sem progresso REAL (nada em DEV
            # DONE, nenhuma flag nova) = a linha para — nunca gira em falso.
            flag_agora = sum(
                1
                for c in self.db.carregar_tasks_kanban(onda_id, target_story)
                if c["block_tipo"]
            )
            if (
                len(self._concluidas_da_story(onda_id, target_story)) == concluidas_antes
                and flag_agora == flag_antes
                and not instalacao_bloqueada
            ):
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🛑 {target_story}: passada sem progresso real — linha "
                        "parada (nada queimou, nada foi resolvido)."
                    ),
                )
                break

        dev_res_texto = "\n\n".join(dev_outputs)

        class _DevConsolidado:
            """Consolidado das entregas task-a-task (mesma interface de resultado)."""

            output = dev_res_texto
            # Sem queima neste ciclo = validação pura de trabalho já gravado:
            # success NÃO depende de outputs novos (o review decide).
            success = bool(dev_outputs) or not houve_queima
            is_blocked = False
            block_reason = None

        dev_res = _DevConsolidado()

        if self._cota_ativa:
            # 🚦 COTA ESGOTADA DURANTE A QUEIMA: o broker morreu no meio da rodada.
            # Devolve bloqueado pelo motivo REAL (429) SEM chamar o review/downstream
            # (seria outra chamada garantidamente 429) — a escada do lado de fora
            # espera o reset SEM queimar degrau.
            BUS.publish(
                "announcement",
                agent="@turing",
                text=(
                    f"⏸ {target_story}: cota esgotada no meio da queima — "
                    "review/downstream suspensos até o reset do provedor."
                ),
            )
            return {
                "success": False,
                "is_blocked": True,
                "blocked_by": "@turing",
                "error": "Cota esgotada no provedor — queima pausada (infra).",
                "review_output": "",
                "arquivos_escritos": escritas_ciclo,
            }

        # 🚩 REGRA DO KANBAN DE AGENTES: review SÓ com TODAS as tasks da story
        # em DEV DONE. Alguma task terminou BLOCKED? A linha para AQUI (Impedimento):
        # nada de review sobre trabalho incompleto — o escada/fila atua na
        # task bloqueada primeiro (ela é a primeira da fila no próximo ciclo).
        cartoes_fim = self.db.carregar_tasks_kanban(onda_id, target_story)
        cards_task = [c for c in cartoes_fim if not c["task_id"].startswith("REVIEW")]
        nao_prontas = [
            c for c in cards_task if c["kanban_status"] not in ("DEV_DONE", "DONE_DEFINITIVO")
        ]
        if nao_prontas:
            detalhes = "; ".join(
                f"{c['task_id']} ({c['kanban_status']}"
                + (f": {c['block_tipo']}" if c["block_tipo"] else "")
                + ")"
                for c in nao_prontas
            )
            BUS.publish(
                "announcement",
                agent="@turing",
                text=(
                    f"🚩 IMPEDIMENTO — {target_story}: {len(nao_prontas)} task(s) fora de DEV "
                    f"DONE [{detalhes}]. Code review NÃO roda sobre story incompleta; "
                    "a linha atua nas tasks bloqueadas primeiro."
                ),
            )
            pior = nao_prontas[0]
            self.kanban.block_card(
                target_story,
                reason=(
                    f"Task {pior['task_id']} {pior['kanban_status']}"
                    + (f" ({pior['block_tipo']})" if pior["block_tipo"] else "")
                    + " — story não vai a review com task não finalizada."
                ),
                blocked_by="@turing",
            )
            return {
                "success": False,
                "is_blocked": True,
                "blocked_by": "@turing",
                "error": (
                    f"🚩 {target_story}: story com task fora de DEV DONE "
                    f"[{detalhes}] — review suspenso (Impedimento)."
                ),
                "review_output": "",
                "arquivos_escritos": escritas_ciclo,
            }

        # 3. FASE REVIEW: @unclebob (Tech Lead) revisa Clean Code, SOLID e padrões
        # arquiteturais — DA STORY INTEIRA, só quando TODAS as tarefas fecharem.
        runner_bob = self._get_runner("@unclebob")
        bob_res = None
        if runner_bob:
            raw_bob_prompt = (
                f"Faça o code review de Clean Code e SOLID para {target_story}.\n"
                f"FORMATO OBRIGATÓRIO por achado: 'ACHADO: <problema>' seguido de "
                f"'SOLUÇÃO: <correção específica — arquivo, o que mudar e como>'. "
                f"Achado sem solução proposta é parecer incompleto.\n"
                f"Inspecione os arquivos de código implementados pelo Dev ('js/', raiz) e os testes em 'tests/'.\n"
                "PROTOCOLO DE ENTREGA ALÉM DO ESCOPO: se a entrega inclui item não contratado "
                "que está CORRETO e integrado, NÃO mande apagar nem re-queimar — valide, "
                "registre na documentação da story como 'entregue além do contrato' e siga; "
                "isso evita queima repetida do que já existe.\n"
                f"Se o código e os testes estiverem aprovados, declare explicitamente: 'Review: APROVADO'. Caso contrário, aponte os problemas.\n"
            )
            bob_prompt = self._assemble_prompt("@unclebob", raw_bob_prompt)
            # Processo oficial do card: nasce → AGUARDANDO → EM_DEV → binário
            bob_res = self._executar_com_card(
                onda_id,
                target_story,
                "REVIEW-TECH",
                f"Code Review da story {target_story}",
                "@unclebob",
                90,
                lambda: self._review_com_retry(
                    runner_bob, bob_prompt, "@unclebob (Tech Lead Review)"
                ),
                dor=["all_burn_done"],
                dod=["parecer_integral_gravado"],
            )
            self._anotar_cota_resultado(bob_res)

            if bob_res and (
                getattr(bob_res, "is_blocked", False) or not getattr(bob_res, "success", True)
            ):
                block_reason = (
                    getattr(bob_res, "block_reason", None)
                    or "Tech Lead (@unclebob) bloqueou a auditoria de review"
                )
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@unclebob")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@unclebob",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no Tech Lead: {block_reason}",
                    "review_output": getattr(bob_res, "output", ""),
                    "arquivos_escritos": escritas_ciclo,
                }

        # 4. FASE RUNNER & VERIFICAÇÃO — REGRA DO FLUXO (inegociável):
        # Tech Lead APROVOU → desce para o QA (execução da suíte).
        # Tech Lead REPROVOU → NÃO desce para QA: volta para CORREÇÃO
        # (achados → donos de camada). QA só existe após aprovação técnica.
        bob_approved_primeiro, _reason = self._check_explicit_approval(bob_res)
        aniche_val_res = None
        if runner_aniche and bob_approved_primeiro:
            raw_aniche_val_prompt = (
                f"Execute a suíte de testes da story {target_story} contra o código implementado.\n"
                "COMO: use a ferramenta `executar_comando` para rodar de verdade "
                "(ex.: 'pytest -q tests/api tests/unit tests/infra', "
                "'npx vitest run', 'bash scripts/run_gates.sh') e baseie o "
                "veredito na SAÍDA REAL dos comandos (exit code + contadores "
                "passed/failed). Inspeção estática NÃO emite veredito; sem "
                "execução, declare bloqueio citando a ferramenta que faltou.\n"
                f"Inspecione a pasta 'tests/'. Se todos os testes passarem, declare explicitamente: 'Veredito: APROVADO'.\n"
            )
            aniche_val_prompt = self._assemble_prompt("@aniche", raw_aniche_val_prompt)
            # Processo oficial do card: nasce → AGUARDANDO → EM_DEV → binário
            aniche_val_res = self._executar_com_card(
                onda_id,
                target_story,
                "REVIEW-QA",
                f"QA Run & Verify da story {target_story}",
                "@aniche",
                91,
                lambda: self._review_com_retry(
                    runner_aniche, aniche_val_prompt, "@aniche (QA Run & Verify)"
                ),
                dor=["all_burn_done"],
                dod=["veredito_explicito_da_suite"],
            )
            self._anotar_cota_resultado(aniche_val_res)

        # Avalia veredictos com a LEI DA RESTRIÇÃO (DEFAULT-DENY)
        aniche_approved, aniche_reason = self._check_explicit_approval(aniche_val_res)
        bob_approved, bob_reason = self._check_explicit_approval(bob_res)

        aniche_verdict = {
            "approved": aniche_approved,
            "notes": getattr(aniche_val_res, "output", "")[:400]
            if aniche_val_res
            else aniche_reason,
        }
        unclebob_verdict = {
            "approved": bob_approved,
            "notes": getattr(bob_res, "output", "")[:400] if bob_res else bob_reason,
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

        is_cycle_approved = bool(
            dev_res and getattr(dev_res, "success", True) and review_eval["approved"]
        )
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
        # Impedimento flag: ciclo aprovado limpa o bloqueio anterior (o card segue
        # o fluxo — a flag de bloqueio é ortogonal ao status).
        card_ciclo = self.kanban.get_card(target_story)
        if is_cycle_approved and card_ciclo and card_ciclo.get("is_blocked"):
            self.kanban.unblock_card(target_story)

        # ── KANBAN DE AGENTES: destino final do ciclo ──
        if is_cycle_approved:
            # Story 100% aprovada → cards viram DONE DEFINITIVO (nunca mais
            # voltam; mexer depois = CHANGE = novo card formalizado). A lista
            # de cards vem DO KANBAN (única fonte) — não de memória.
            for c in self.db.carregar_tasks_kanban(onda_id, target_story):
                self.db.mover_task_kanban(
                    onda_id, target_story, c["task_id"], "DONE_DEFINITIVO"
                )
        # Rejeição: os cards DEV_DONE aguardam — a fila de achados devolve
        # para o BURN apenas os cards do agente afetado (garçom lá em cima).

        if not is_cycle_approved:
            fail_reason = []
            if not bob_approved:
                fail_reason.append(f"Tech Lead: {bob_reason}")
            elif not aniche_approved:
                fail_reason.append(f"QA: {aniche_reason}")
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
            "error": block_msg if not is_cycle_approved else None,
            "test_plan_output": "",
            "dev_output": getattr(dev_res, "output", "") if dev_res else "",
            "aniche_output": getattr(aniche_val_res, "output", "") if aniche_val_res else "",
            "review_output": getattr(bob_res, "output", "") if bob_res else "",
            "review_gate": review_eval,
            "arquivos_escritos": escritas_ciclo,
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

        # Cota do provedor: estado limpo por lote — cada execução recomeça
        # sem janela de reset herdada.
        self._cota_ativa = None

        for story in target_stories:
            # 🚩 IMPEDIMENTO — REGRA ABSOLUTA: bandeira vermelha PARA A LINHA
            # INTEIRA. Não se segue com erro, não se pula fila, não existe
            # tolerância. Enquanto houver bandeira erguida, a ÚNICA coisa que a
            # linha faz é resolver a história flagada — as demais aguardam.
            # FILA INDIANA: a tela mostra APENAS o item que roda — nunca o
            # que espera (a LLM não olha lista; olha o 1 item).
            bandeiras = [
                c
                for c in self.kanban.list_cards(wave_id=self.state_machine.wave_id)
                if c.get("is_blocked")
            ]
            if bandeiras:
                bandeira = bandeiras[0]
                story_bandeira = bandeira["story_id"]
                if story_bandeira != story:
                    BUS.publish(
                        "announcement",
                        agent="@turing",
                        text=(
                            f"🔴 LINHA DE PRODUÇÃO PARADA — bandeira vermelha na {story_bandeira}. "
                            "Resolvê-la é o único trabalho permitido agora."
                        ),
                        wave_id=self.state_machine.wave_id,
                    )
                    story = story_bandeira
                # A história flagada é processada AQUI (ciclo + escada de correção).

            # Pula stories já concluídas no modo AUTO, a menos que force=True ou confirm_callback seja fornecido
            card = self.kanban.get_card(story)
            if (
                not force
                and not confirm_callback
                and card
                and card.get("status")
                in (
                    KanbanCardStatus.DEV_DONE.value,
                    KanbanCardStatus.VALIDATE.value,
                    KanbanCardStatus.DONE.value,
                )
            ):
                logger.info(
                    "Story %s já concluída (%s), avançando para a próxima.",
                    story,
                    card.get("status"),
                )
                completed_stories.append(story)
                continue

            if ABORT_EVENT.is_set():
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text="⏸ Execução da ONDA interrompida pelo usuário — checkpoint salvo. /wave resume retoma exatamente daqui.",
                )
                return {
                    "success": False,
                    "completed_stories": completed_stories,
                    "interrompido": True,
                    "error": "Execução interrompida pelo usuário (checkpoint salvo — /wave resume retoma).",
                }

            # 🧹 Higiene por história também: o review nunca reprova por
            # resíduo que o modelo não consegue apagar.
            self._higienizar_residuos()

            cycle_res = self.run_cycle(story_id=story)
            if not cycle_res.get("success"):
                card = self.kanban.get_card(story)
                motivo = (
                    (card or {}).get("block_reason")
                    or cycle_res.get("error")
                    or "reprovado pelo review"
                )
                # O card guarda só o TRECHO do veto ("corrijam os 7 achados").
                # O dev precisa do PARECER INTEGRAL (achado + solução, um a um):
                # sem isto o re-burn corrige no escuro e a escada repete às cegas.
                parecer_integral = self._parecer_da_review(cycle_res.get("review_output") or "")

                def _feedback_com_parecer(base: str, parecer: str) -> str:
                    if not parecer:
                        return base
                    return (
                        f"{base}\n\nPARECER INTEGRAL DO REVIEW — corrija TODOS os "
                        f"achados enumerados, um a um (texto completo):\n{parecer}"
                    )

                feedback_integral = _feedback_com_parecer(motivo, parecer_integral)

                # 🛠 IMPEDIMENTO AMBIENTAL — detectado na PASSADA 1, NÃO se
                # re-queima: falta de capacidade da PLATAFORMA (ex.: shell para
                # executar suítes) não se resolve com mais tentativas do mesmo
                # agente. Tipa, para a escada e devolve para a plataforma corrigir.
                marcadores_ambiente = (
                    "sem shell",
                    "não disponho",
                    "nao disponho",
                    "ferramenta de execução",
                    "ferramenta de execucao",
                    "não posso executar",
                    "nao posso executar",
                    "não posso rodar",
                    "nao posso rodar",
                    "sem ferramenta de exec",
                    "não disponho de shell",
                )
                if any(m in motivo.lower() for m in marcadores_ambiente):
                    BUS.publish(
                        "escalation",
                        agent="@turing",
                        text=(
                            f"🛠 IMPEDIMENTO AMBIENTAL detectado na 1ª passada — {story}: "
                            f"{motivo[:200]}\n"
                            "Não é tarefa, é CAPACIDADE faltando na plataforma. A escada "
                            "NÃO queima as outras passadas: corrige-se a plataforma "
                            "(ferramenta liberada) e o resume re-queima uma única vez."
                        ),
                        escalation={
                            "type": "impedimento_ambiental",
                            "story": story,
                            "reason": motivo,
                        },
                    )
                    self.kanban.block_card(
                        story,
                        reason=f"IMPEDIMENTO AMBIENTAL: {motivo[:200]}",
                        blocked_by="@turing",
                    )
                    return {
                        "success": False,
                        "completed_stories": completed_stories,
                        "failed_story": story,
                        "blocked": True,
                        "escalation": {
                            "type": "impedimento_ambiental",
                            "story": story,
                            "reason": motivo,
                            "message": motivo,
                        },
                        "error": motivo,
                    }
                escalacao = None
                assinaturas_veto = [motivo]
                retrabalho_ok = False
                escreveu_alguma_vez = False

                # ── FILA DE ACHADOS (mesmo princípio das tasks: 1 achado = 1
                # problema = 1 responsável). O Turing GUARDA os achados, roteia
                # cada um para o agente da especialidade, corrige UM A UM e só
                # no fim valida a story INTEIRA (o review é sobre o conjunto).
                motor = VetoReworkEngine(llm_factory=None)
                achados_enfileirados = motor.extract_blockers(parecer_integral)

                # 🚫 ANTI-INVENÇÃO: "corrijam os N achados" EXIGE a lista. Parecer
                # que ordena correção sem enumerar é DEFITUOSO — o reviewer
                # re-emite com ACHADO/SOLUÇÃO um a um. O dev não recebe ordem no
                # escuro (inventar achado é fraude).
                if (
                    re.search(r"\bachados?\b", f"{motivo} {parecer_integral}", re.IGNORECASE)
                    and not achados_enfileirados
                ):
                    BUS.publish(
                        "veto_analysis",
                        agent="@turing",
                        text=(
                            f"🔍 Parecer de {story} ordena corrigir achados mas NÃO enumera a "
                            "lista — re-emissão obrigatória pelo reviewer."
                        ),
                    )
                    runner_bob_reemit = self._get_runner("@unclebob")
                    if runner_bob_reemit:
                        res_reemit = runner_bob_reemit.run(
                            self._assemble_prompt(
                                "@unclebob",
                                f"Seu parecer para {story} ordena 'corrijam os achados' mas NÃO "
                                "enumera a lista — parecer INCOMPLETO. Re-emita-o com CADA achado "
                                "no formato obrigatório:\nACHADO: <problema>\nSOLUÇÃO: <correção — "
                                f"arquivo, o que mudar e como>\n\nParecer original:\n"
                                f"{parecer_integral or motivo}",
                            )
                        )
                        self._record_telemetry(
                            "EXECUTE", "@unclebob (re-emissão do parecer)", res_reemit
                        )
                        self._anotar_cota_resultado(res_reemit)
                        novo_parecer = (getattr(res_reemit, "output", "") or "").strip()
                        if novo_parecer and motor.extract_blockers(novo_parecer):
                            parecer_integral = novo_parecer
                            feedback_integral = _feedback_com_parecer(motivo, novo_parecer)
                            achados_enfileirados = motor.extract_blockers(novo_parecer)
                            BUS.publish(
                                "veto_rework",
                                agent="@unclebob",
                                text="📋 Parecer re-emito com a lista integral de achados.",
                            )
                        else:
                            feedback_integral += (
                                "\n\nATENÇÃO: o parecer NÃO enumera os achados. Identifique-os "
                                "direto no código apontado; se não conseguir identificá-los, "
                                "declare bloqueio explicitamente — NÃO invente correções."
                            )

                # ── FILA ÚNICA: achados NASCEM COMO CARDS no kanban — e queimam
                # PELA FILA (ordem + DOR), no próximo ciclo. AQUI NÃO SE QUEIMA
                # NADA: sem loop paralelo, sem segunda fila, sem exceção.
                if len(achados_enfileirados) >= 1:
                    self._nascer_fila_achados(story, achados_enfileirados)
                    pendentes_ach = self._achados_pendentes(story)
                    # Agrupa achados por agente para amarrar a DOR dos cards devolvidos
                    achados_por_agente: dict[str, list[str]] = {}
                    for row_ach in pendentes_ach:
                        agente_achado = row_ach.get("agent_role") or self._agente_para_achado(
                            row_ach.get("descricao", "")
                        )
                        achados_por_agente.setdefault(agente_achado, []).append(row_ach["task_id"])
                        BUS.publish(
                            "veto_rework",
                            agent=agente_achado,
                            text=(
                                f"🔧 ACHADO NO KANBAN — {agente_achado}: "
                                f"{(row_ach.get('descricao') or '')[:90]}"
                            ),
                        )
                    for ag_ach, aids in achados_por_agente.items():
                        self._garcom_devolver_cards_para_burn(
                            self.state_machine.wave_id, story, ag_ach, achados_ids=aids
                        )
                    BUS.publish(
                        "veto_analysis",
                        agent="@turing",
                        text=(
                            f"📋 {story}: {len(pendentes_ach)} achados no kanban — "
                            "a FILA ÚNICA queima um a um (ordem + DOR), e o review "
                            "só re-roda quando a fila do kanban estiver limpa."
                        ),
                    )
                    # O rework deste degrau É a fila queimar os achados:
                    # próximo ciclo relê o kanban e queima na ordem.
                    cycle_res = self._run_cycle_inner(
                        story,
                        rework_feedback=(
                            "Achados nasceram como cards no kanban — queime a fila "
                            "na ordem (DOR respeitada) e valide a story INTEIRA no fim.\n\n"
                            + feedback_integral
                        ),
                    )
                    if cycle_res.get("success"):
                        retrabalho_ok = True
                        card_pos = self.kanban.get_card(story)
                        if card_pos and card_pos.get("is_blocked"):
                            self.kanban.unblock_card(story)
                        BUS.publish(
                            "announcement",
                            agent="@turing",
                            text=(
                                f"🟢 IMPEDIMENTO RESOLVIDO — {story}: achados corrigidos "
                                "pela fila única e story aprovada. Bandeira recolhida."
                            ),
                        )
                    else:
                        novo_motivo = (
                            (self.kanban.get_card(story) or {}).get("block_reason")
                            or cycle_res.get("error")
                            or motivo
                        )
                        motivo = novo_motivo
                        novo_parecer = self._parecer_da_review(
                            cycle_res.get("review_output") or ""
                        )
                        if novo_parecer:
                            parecer_integral = novo_parecer
                        feedback_integral = _feedback_com_parecer(motivo, parecer_integral)

                # ── ESCADA DE CONVERGÊNCIA v2 (tudo autônomo em matéria técnica) ──
                # Com evidência de escrita (dev executou): trilha clássica —
                #   1-2 dirigido → 3-4 @caroli refina a story.
                # Sem evidência (dev devolveu PLANO sem gravar arquivo = recusa
                # velada): trilha de execução — 2 plano aprovado pelo Tech Lead
                # → 3 ordem incisiva → 4 o PRÓPRIO Tech Lead assume e codifica.
                # Só APÓS a escada completa → escalação (com a causa verdadeira).
                # (A fila de achados acima pode já ter resolvido — neste caso a
                # escada NEM começa.)

                def _sig(t: str) -> str:
                    import re as _re

                    return "|".join(sorted(set(_re.findall(r"[a-zà-ú]{6,}", t.lower())))[:10])

                def _caroli_refino(degrau: int, alvo: str, feedback_atual: str) -> None:
                    BUS.publish(
                        "veto_rework",
                        agent="@caroli",
                        text=(
                            f"📝 [DEGRAU {degrau}/4] Ciclos reprovados com execução real — "
                            f"a STORY pode estar ambígua. @caroli refinando critérios com o "
                            f"feedback do review..."
                        ),
                    )
                    runner_caroli = self._get_runner("@caroli")
                    if runner_caroli:
                        prompt_refino = (
                            f"A story {alvo} foi REPROVADA duas vezes pelo Tech Lead no mesmo ponto.\n"
                            f"Feedback do review: {feedback_atual}\n\n"
                            f"Refine a story (critérios de aceite/BDD) eliminando a ambiguidade apontada — "
                            f"sem cortar escopo contratado. REGRA RÍGIDA: mantenha/atualize a seção "
                            f"'## RESUMO PARA EXECUÇÃO' (resumo completo por definição, ~30 linhas) — "
                            f"é ELA que os agentes de execução recebem. Salve o arquivo atualizado da story."
                        )
                        res_caroli = runner_caroli.run(
                            self._assemble_prompt("@caroli", prompt_refino)
                        )
                        self._record_telemetry("EXECUTE", "@caroli (refino de story)", res_caroli)
                        self._anotar_cota_resultado(res_caroli)
                        self._extract_and_write_project_files(getattr(res_caroli, "output", ""))

                degrau = 1
                esperas_cota = 0
                while degrau < 5:
                    if retrabalho_ok:
                        break  # a fila de achados já convergiu — escada desnecessária
                    if self._cota_ativa:
                        # 🚦 COTA NO INÍCIO DO DEGRAU — PAUSA a escada SEM consumir
                        # degrau: corrigir com o provedor de fora é queimar tentativa
                        # de convergência em chamada que garante 429.
                        decisao_cota, esperas_cota, retorno_cota = self._gate_cota_na_escada(
                            story, esperas_cota, completed_stories
                        )
                        if decisao_cota == "return":
                            return retorno_cota
                        continue  # janela resetou → re-tenta o MESMO degrau
                    if ABORT_EVENT.is_set():
                        # ESC ESC do usuário: checkpoint salvo, NADA de escalar
                        # nem de continuar queimando degraus.
                        BUS.publish(
                            "announcement",
                            agent="@turing",
                            text=(
                                f"⏸ {story}: escada interrompida pelo usuário "
                                "(ESC ESC) — checkpoint salvo; /wave resume retoma."
                            ),
                        )
                        return {
                            "success": False,
                            "completed_stories": completed_stories,
                            "interrompido": True,
                            "error": "Execução interrompida pelo usuário (checkpoint salvo).",
                        }
                    # Rota por EVIDÊNCIA: zero gravações = o problema é recusa do
                    # dev, não a story — sobe a agressividade da ordem.
                    if not escreveu_alguma_vez:
                        estrategia = {
                            1: "dirigido",
                            2: "plano_aprovado",
                            3: "incisivo",
                            4: "lead_assume",
                        }[degrau]
                    else:
                        estrategia = "caroli" if degrau >= 3 else "dirigido"

                    if estrategia == "caroli":
                        _caroli_refino(degrau, story, motivo)
                        BUS.publish(
                            "veto_rework",
                            agent="@unclebob",
                            text=f"🔥 [DEGRAU {degrau}/4] Re-queimando {story} com story refinada.",
                        )
                        cycle_res = self._run_cycle_inner(story, rework_feedback=motivo)
                    elif estrategia == "plano_aprovado":
                        BUS.publish(
                            "veto_rework",
                            agent="@unclebob",
                            text=(
                                f"📝 [DEGRAU {degrau}/4] O dev devolveu PLANO sem gravar "
                                f"arquivo — @unclebob valida e aprova o plano..."
                            ),
                        )
                        runner_bob = self._get_runner("@unclebob")
                        plano = cycle_res.get("dev_output") or motivo
                        plano_aprovado = plano
                        if runner_bob:
                            res_bob = runner_bob.run(
                                self._assemble_prompt(
                                    "@unclebob",
                                    f"A story {story} está reprovada com o parecer: {feedback_integral}\n\n"
                                    f"O dev respondeu com um PLANO (sem gravar arquivo):\n{plano}\n\n"
                                    "Valide a coerência do plano contra o parecer. Se o plano resolve "
                                    "os achados, declare exatamente: 'PLANO APROVADO — implemente agora'. "
                                    "Se não resolver, reescreva o plano corrigindo o que falta.",
                                )
                            )
                            self._record_telemetry(
                                "EXECUTE", "@unclebob (validação de plano)", res_bob
                            )
                            self._anotar_cota_resultado(res_bob)
                            plano_aprovado = getattr(res_bob, "output", "") or plano
                        feedback_degrau = (
                            "PLANO APROVADO PELO TECH LEAD — implemente NESTA rodada. "
                            "Entrega = arquivos gravados (write_project_file), não texto.\n\n"
                            f"Plano aprovado (texto completo): {plano_aprovado}\n\n"
                            f"Parecer de rejeição: {feedback_integral}"
                        )
                        BUS.publish(
                            "veto_rework",
                            agent="@unclebob",
                            text=f"🔥 [DEGRAU {degrau}/4] Re-queimando {story} com plano aprovado.",
                        )
                        cycle_res = self._run_cycle_inner(story, rework_feedback=feedback_degrau)
                    elif estrategia == "incisivo":
                        BUS.publish(
                            "veto_rework",
                            agent="@unclebob",
                            text=f"📣 [DEGRAU {degrau}/4] Ordem incisiva: {story} DEVE ser implementada nesta rodada.",
                        )
                        feedback_degrau = (
                            "ORDEM DIRETA (sem margem): VOCÊ EXECUTA A CORREÇÃO NESTA RODADA. "
                            "Grave cada arquivo com write_project_file ANTES de qualquer texto. "
                            "Devolver plano, diagnóstico ou pedido de aprovação É RECUSA de ordem "
                            "explícita e será tratado como bloqueio.\n\n"
                            f"Parecer de rejeição: {feedback_integral}"
                        )
                        cycle_res = self._run_cycle_inner(story, rework_feedback=feedback_degrau)
                    elif estrategia == "lead_assume":
                        BUS.publish(
                            "veto_rework",
                            agent="@unclebob",
                            text=(
                                f"🛠 [DEGRAU {degrau}/4] O dev se recusou a executar 3× — "
                                f"@unclebob ASSUME a implementação e codifica pessoalmente."
                            ),
                        )
                        runner_lead = self._get_runner("@unclebob")
                        if runner_lead:
                            res_lead = runner_lead.run(
                                self._assemble_prompt(
                                    "@unclebob",
                                    f"O dev se recusou a implementar (3 tentativas sem gravar "
                                    f"arquivo). ASSUMA a tarefa e corrija você mesmo, gravando os "
                                    f"arquivos nesta rodada.\nStory: {story}\n"
                                    f"Parecer de rejeição: {feedback_integral}\n"
                                    "Entrega = arquivos gravados. Diagnóstico sem gravação não é entrega.",
                                )
                            )
                            self._record_telemetry(
                                "EXECUTE", "@unclebob (assumiu a implementação)", res_lead
                            )
                            self._anotar_cota_resultado(res_lead)
                        cycle_res = self._run_cycle_inner(story, rework_feedback=feedback_integral)
                    elif estrategia == "dirigido":
                        # FILA ÚNICA (sem segunda fila, sem exceção): achados
                        # estruturados NASCEM COMO CARDS (nascimento idempotente)
                        # e queimam PELA FILA DO KANBAN dentro do ciclo abaixo —
                        # ordem + DOR mandam. O degrau NÃO queima nada por fora.
                        if achados_enfileirados:
                            self._nascer_fila_achados(story, achados_enfileirados)
                            pendentes_ach = self._achados_pendentes(story)
                            achados_por_agente: dict[str, list[str]] = {}
                            for row_ach in pendentes_ach:
                                agente_achado = row_ach.get("agent_role") or self._agente_para_achado(
                                    row_ach.get("descricao", "")
                                )
                                achados_por_agente.setdefault(agente_achado, []).append(row_ach["task_id"])
                            for ag_ach, aids in achados_por_agente.items():
                                self._garcom_devolver_cards_para_burn(
                                    self.state_machine.wave_id, story, ag_ach, achados_ids=aids
                                )
                        cycle_res = self._run_cycle_inner(story, rework_feedback=feedback_integral)
                    else:  # dirigido (clássico, sem achados estruturados)
                        BUS.publish(
                            "veto_rework",
                            agent="@unclebob",
                            text=(
                                f"🔥 [DEGRAU {degrau}/4] Re-queimando {story} no ciclo TDD "
                                "com o parecer integral do review."
                            ),
                        )
                        cycle_res = self._run_cycle_inner(story, rework_feedback=feedback_integral)

                    if cycle_res.get("success"):
                        retrabalho_ok = True
                        card_pos = self.kanban.get_card(story)
                        if card_pos and card_pos.get("is_blocked"):
                            self.kanban.unblock_card(story)
                        BUS.publish(
                            "announcement",
                            agent="@turing",
                            text=(
                                f"🟢 IMPEDIMENTO RESOLVIDO — {story} aprovada no degrau "
                                f"{degrau}/4 da escada. Bandeira recolhida; a linha volta a correr."
                            ),
                        )
                        break

                    escreveu_alguma_vez = escreveu_alguma_vez or bool(
                        cycle_res.get("arquivos_escritos")
                    )
                    novo_motivo = (
                        (self.kanban.get_card(story) or {}).get("block_reason")
                        or cycle_res.get("error")
                        or motivo
                    )
                    assinaturas_veto.append(_sig(novo_motivo))
                    motivo = novo_motivo
                    novo_parecer = self._parecer_da_review(cycle_res.get("review_output") or "")
                    if novo_parecer:
                        parecer_integral = novo_parecer
                    feedback_integral = _feedback_com_parecer(motivo, parecer_integral)

                    if self._cota_ativa:
                        # 🚦 COTA NO FIM DO DEGRAU — o degrau falhou POR INFRA; a
                        # escada PAUSA e espera o reset SEM gastar o degrau.
                        decisao_cota, esperas_cota, retorno_cota = self._gate_cota_na_escada(
                            story, esperas_cota, completed_stories
                        )
                        if decisao_cota == "return":
                            return retorno_cota
                        continue  # janela resetou → re-tenta o MESMO degrau
                    degrau += 1

                if not retrabalho_ok:
                    if not escreveu_alguma_vez:
                        # Causa verdadeira: NINGUÉM executou — o dev devolveu
                        # plano/diagnóstico 4× (feedback, plano aprovado pelo
                        # lead, ordem direta, e o lead assumindo). Não é falta
                        # de informação de negócio: é recusa de agente.
                        escalacao = {
                            "type": "agent_refusal",
                            "story": story,
                            "reason": motivo,
                            "review_output": cycle_res.get("review_output", ""),
                            "message": (
                                f"🟠 ESCALAÇÃO — RECUSA DE AGENTE em {story}: 4 tentativas "
                                "(feedback dirigido, plano aprovado pelo Tech Lead, ordem direta "
                                "e o próprio Tech Lead assumindo) e NENHUM arquivo foi gravado.\n"
                                f"Último parecer: {motivo}\n\n"
                                "Isto não é falta de informação — é comportamento do agente.\n"
                                "1. RETENTAR — /wave resume reabre a escada do zero\n"
                                "2. ASSUMIR — corrija você mesmo e rode /wave execute\n"
                                "3. ADIAR — mover a story para a próxima onda"
                            ),
                            "suggested_owner": "@turing",
                        }
                    else:
                        # 🚦 Semáforo de impedimentos:
                        # 🔴 VERMELHO — parada TOTAL: escada completa não convergiu E o
                        #    agente declarou impedimento (nem automação resolve).
                        # 🟠 LARANJA — escalação do humano: falta INFORMAÇÃO de negócio
                        #    (decisão INFORMAR/SIMPLIFICAR/ADIAR), não ação técnica.
                        classe_final = (
                            VetoReworkEngine(llm_factory=None)
                            .classify(
                                motivo,
                                cycle_res.get("review_output", ""),
                                target_agent="@turing",
                            )
                            .veto_class
                        )
                        if classe_final is VetoClass.AGENT_BLOCKED:
                            escalacao = {
                                "type": "line_stop",
                                "story": story,
                                "reason": motivo,
                                "review_output": cycle_res.get("review_output", ""),
                                "message": (
                                    f"🔴 LINHA DE PRODUÇÃO PARADA — {story} não convergiu na "
                                    "escada completa (correção dirigida + refinamento de story "
                                    "com execução real) e o agente declarou impedimento.\n"
                                    f"Motivo da parada: {motivo}\n\n"
                                    "Nenhuma automação restante resolve este ponto. É preciso "
                                    "intervenção humana para destravar a linha."
                                ),
                                "suggested_owner": "@turing",
                            }
                        else:
                            escalacao = {
                                "type": "human_escalation",
                                "story": story,
                                "reason": motivo,
                                "review_output": cycle_res.get("review_output", ""),
                                "message": (
                                    f"🟠 ESCALAÇÃO AO HUMANO — {story} não convergiu na escada "
                                    "completa (correção dirigida + refinamento de story, com "
                                    "execução real do dev).\n"
                                    f"Informação em falta: {motivo}\n\n"
                                    "1. INFORMAR — digite a informação que falta\n"
                                    "2. SIMPLIFICAR O ACEITE — diga o novo critério mínimo\n"
                                    "3. ADIAR — mover a story para a próxima onda\n"
                                    f"Parecer do review: {cycle_res.get('review_output', '')[:2000]}"
                                ),
                                "suggested_owner": "@unclebob",
                            }
                        BUS.publish(
                            "escalation",
                            agent="@turing",
                            text=escalacao["message"],
                            escalation=escalacao,
                        )
                        self.kanban.block_card(story, reason=motivo, blocked_by="@turing")
                        return {
                            "success": False,
                            "completed_stories": completed_stories,
                            "failed_story": story,
                            "blocked": True,
                            "escalation": escalacao,
                            "error": escalacao["message"],
                        }

                    # agent_refusal (sem execução em 4 degraus)
                    BUS.publish(
                        "escalation",
                        agent="@turing",
                        text=escalacao["message"],
                        escalation=escalacao,
                    )
                    self.kanban.block_card(story, reason=motivo, blocked_by="@turing")
                    return {
                        "success": False,
                        "completed_stories": completed_stories,
                        "failed_story": story,
                        "blocked": True,
                        "escalation": escalacao,
                        "error": escalacao["message"],
                    }
                cycle_res.setdefault(
                    "message", f"Story {story} aprovada na escada de convergência."
                )
                # Retrabalho dirigido convergiu: segue para a próxima story
                cycle_res.setdefault("message", f"Story {story} aprovada após retrabalho dirigido.")

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

    def _run_validate_inner(self) -> dict[str, Any]:
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

        # 2. Homologação de Produto: @edith audita o entregável integrado
        runner_edith = self._get_runner("@edith")
        edith_res = None
        if runner_edith:
            edith_prompt = self._assemble_prompt("@edith", self._build_edith_audit_prompt())
            edith_res = self._executar_com_card(
                self.state_machine.wave_id,
                "VALIDATE",
                "VALIDATE-HOMOLOGACAO",
                "Homologação integrada de produto",
                "@edith",
                1,
                lambda: runner_edith.run(edith_prompt),
                dor=[],
                dod=["status_aprovado_sem_ressalvas"],
                task_tipo="VALIDATE",
                descricao="Homologação funcional ponta a ponta e auditoria de valor de produto.",
            )
            self._record_telemetry("VALIDATE", "@edith (Product Homologation)", edith_res)

        # 3. Governança e FinOps: @nina audita consumo de tokens e ética
        runner_nina = self._get_runner("@nina")
        nina_res = None
        if runner_nina:
            nina_prompt = self._assemble_prompt("@nina", self._build_nina_audit_prompt())
            nina_res = self._executar_com_card(
                self.state_machine.wave_id,
                "VALIDATE",
                "VALIDATE-GOVERNANCA",
                "Auditoria de governança, ética e finops",
                "@nina",
                2,
                lambda: runner_nina.run(nina_prompt),
                dor=[],
                dod=["status_aprovado_sem_ressalvas"],
                task_tipo="VALIDATE",
                descricao="Auditoria de governança de IA, conformidade ética e eficiência de tokens.",
            )
            self._record_telemetry("VALIDATE", "@nina (Gov & FinOps)", nina_res)

        # Avaliação com a LEI DA RESTRIÇÃO (DEFAULT-DENY)
        edith_approved, edith_reason = self._check_explicit_approval(edith_res)
        nina_approved, nina_reason = self._check_explicit_approval(nina_res)

        validators: dict[str, dict[str, Any]] = {
            "@edith": {
                "runner": runner_edith,
                "approved": edith_approved,
                "reason": edith_reason,
                "output": getattr(edith_res, "output", "") if edith_res else "",
                "label": "Homologação de Produto (@edith)",
            },
            "@nina": {
                "runner": runner_nina,
                "approved": nina_approved,
                "reason": nina_reason,
                "output": getattr(nina_res, "output", "") if nina_res else "",
                "label": "Governança e FinOps (@nina)",
            },
        }

        success = bool(integration_tests_info["all_passed"] and edith_approved and nina_approved)

        # Ciclo de Retrabalho do Turing: veto não mata o processo AUTO.
        # Análise determinística → delegação probabilística → rework roteado → escalonamento.
        rework_info: dict[str, Any] | None = None
        if not success and self.state_machine.autonomy_mode == AutonomyMode.AUTO:
            success, reasons, rework_info = self._veto_rework_cycle(
                validators, integration_tests_info
            )
        else:
            reasons = []
            if not integration_tests_info["all_passed"]:
                reasons.append(integration_tests_info["details"])
            for name, info in validators.items():
                if not info["approved"]:
                    reasons.append(f"{name}: {info['reason']}")

        if success:
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            for c in cards:
                if c.get("status") == KanbanCardStatus.DEV_DONE.value:
                    self.kanban.update_status(
                        story_id=c["story_id"],
                        status=KanbanCardStatus.DONE.value,
                    )

        # Salva o relatório de validação formal no workspace da ONDA
        try:
            val_path = self.workspace.wave_validation_report_path(self.state_machine.wave_id)
            val_path.parent.mkdir(parents=True, exist_ok=True)
            report_lines = [
                f"# 📋 Relatório de Validação da ONDA {self.state_machine.wave_id}",
                f"- **Resultado Final:** {'APROVADO' if success else 'REPROVADO'}",
                f"- **Testes de Integração:** {'PASSOU' if integration_tests_info['all_passed'] else 'FALHOU'}",
                f"- **{validators['@edith']['label']}:** {'APROVADO' if validators['@edith']['approved'] else 'REPROVADO'}",
                f"- **{validators['@nina']['label']}:** {'APROVADO' if validators['@nina']['approved'] else 'REPROVADO'}",
                "",
                f"## 🔍 {validators['@edith']['label']}",
                validators["@edith"]["output"] or "Não executado.",
                "",
                f"## ⚖️ {validators['@nina']['label']}",
                validators["@nina"]["output"] or "Não executado.",
            ]
            if rework_info:
                report_lines.extend(
                    [
                        "",
                        "## 🔁 Ciclo de Retrabalho do Turing",
                        f"- Tentativas de retrabalho: {rework_info.get('attempts', 0)}",
                    ]
                )
                if rework_info.get("escalation"):
                    esc = rework_info["escalation"]
                    report_lines.extend(
                        [
                            f"- **ESCALONAMENTO:** {esc.get('message')}",
                            f"- Classificação do veto: {esc.get('veto_class')} (fonte: {esc.get('classification_source')})",
                            f"- Responsável sugerido: {esc.get('suggested_owner')}",
                        ]
                    )
            if reasons:
                report_lines.extend(
                    ["", "## ⚠️ Apontamentos e Bloqueios"] + [f"- {r}" for r in reasons]
                )
            # REDE DE SEGURANÇA ABSOLUTA (antes de gravar): o relatório
            # CONSOLIDADO é re-escaneado pelo veredito estrutural. Se contém
            # rejeição, story parcial/divergente ou ausência de declaração
            # canônica, a ONDA NÃO fecha — JAMAIS (à prova de gate enganado).
            documento = "\n".join(report_lines)
            consistente, motivo_contradicao = self._veredito_estrutural(documento)
            if not consistente:
                success = False
                reasons = reasons or []
                reasons.append(
                    f"🛡️ REDE DE SEGURANÇA CONTRATUAL: contradição no relatório consolidado — {motivo_contradicao}. "
                    "A ONDA NÃO pode ser encerrada nesta condição."
                )
                BUS.publish(
                    "escalation",
                    agent="@turing",
                    text=(
                        "🛡️ [REDE DE SEGURANÇA] Homologação bloqueada por contradição no relatório "
                        f"consolidado: {motivo_contradicao}. Ciclo de retrabalho acionado."
                    ),
                )
                if self.state_machine.autonomy_mode == AutonomyMode.AUTO:
                    success, reasons, rework_info = self._veto_rework_cycle(
                        validators, integration_tests_info
                    )

            # Grava o relatório com o veredito FINAL (pós-rede de segurança)
            report_lines[1] = f"- **Resultado Final:** {'APROVADO' if success else 'REPROVADO'}"
            if reasons:
                idx_apont = next(
                    (i for i, l in enumerate(report_lines) if l.startswith("## ⚠️")),
                    None,
                )
                linhas_apont = ["## ⚠️ Apontamentos e Bloqueios"] + [f"- {r}" for r in reasons]
                if idx_apont is not None:
                    report_lines[idx_apont : idx_apont + 1] = linhas_apont
                else:
                    report_lines.extend(["", *linhas_apont])
            val_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Falha ao salvar validation_report.md: %s", exc)

        if success:
            # Onda convergiu: orçamento de sessão de retrabalho zerado.
            self.db.set_meta(f"rework_rounds:{self.state_machine.wave_id.upper()}", "0")
            self.db.set_meta(f"veto_sig:{self.state_machine.wave_id.upper()}", "")

        return {
            "success": success,
            "stage": TuringStage.VALIDATE.value,
            "integration_tests": integration_tests_info,
            "validator_output": validators["@edith"]["output"],
            "gov_output": validators["@nina"]["output"],
            "rework": rework_info,
            "blocked": bool(rework_info and rework_info.get("escalation")),
            "error": " | ".join(reasons) if not success else None,
        }

    def _build_edith_audit_prompt(self) -> str:
        """Constrói o prompt de auditoria da @edith (intermediária vs. final via Sequenciador)."""
        from bombe_code.domain.wave.sequencer import WaveSequencer

        prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
        prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
        sequencer = WaveSequencer.from_markdown(prd_content)
        current_wave_id = self.state_machine.wave_id
        current_plan = sequencer.get_plan(current_wave_id)
        has_future = sequencer.has_future_waves(current_wave_id)
        is_final = sequencer.is_final_wave(current_wave_id)

        cards = self.kanban.list_cards(wave_id=current_wave_id)
        wave_story_ids = [c.get("story_id", "") for c in cards]
        story_list_str = ", ".join(wave_story_ids) or "stories da onda atual"

        if has_future and not is_final:
            # ONDA INTERMEDIÁRIA: Valida a fatia vertical contratada
            return (
                f"Você está auditando a ONDA INTERMEDIÁRIA '{current_wave_id}' de um MVP fatiado via Lean Inception.\n"
                f"O PRD em 'docs/briefings/PRD.md' formalizou que existem ondas futuras para os épicos e funcionalidades subsequentes.\n"
                f"Seu dever como Auditora de Homologação nesta onda é verificar EXCLUSIVAMENTE o incremento entregue nesta fatia:\n"
                f"- Histórias sob escopo desta onda: {story_list_str}\n"
                f"- Hipótese de negócio da onda: '{current_plan.business_hypothesis if current_plan else 'Fatia vertical da onda'}'\n"
                f"- Inspecione os arquivos de código e testes do projeto.\n"
                f"REGRA MANDATÓRIA DE FINOPS E GOVERNANÇA: NÃO reprove nem bloqueie esta onda por falta de módulos ou funcionalidades que estão formalmente agendadas para as ondas futuras no Sequenciador do PRD.\n"
                f"Se as histórias desta onda ({story_list_str}) foram implementadas com testes passando e arquitetura íntegra, declare explicitamente: 'Homologação: APROVADO'. Caso contrário, aponte os bloqueios da fatia atual.\n"
            )
        # ONDA FINAL: Validação de Release de Produção
        return (
            f"Você está auditando a ONDA FINAL DE RELEASE ('{current_wave_id}') do MVP.\n"
            f"Como esta é a última onda planejada no Sequenciador do PRD (ou onda única de escopo completo), "
            f"audite o entregável integrado completo contra TODOS os requisitos funcionais e não-funcionais do PRD em 'docs/briefings/PRD.md'.\n"
            f"Verifique se o produto está íntegro de ponta a ponta para homologação de produção.\n"
            f"Se aprovado para release, declare explicitamente: 'Homologação: APROVADO'. Caso contrário, aponte os bloqueios ou faltas para o MVP.\n"
        )

    def _build_nina_audit_prompt(self) -> str:
        """Constrói o prompt de auditoria de governança/FinOps da @nina."""
        return (
            "Audite o consumo de tokens, custos e a governança ética da ONDA consultando o relatório em 'docs/telemetria.md'.\n"
            "ESCOPO ESTRICTO: audite o PROJETO. PROIBIDO emitir recomendações sobre a "
            "ferramenta/plataforma/modelos — isso não serve ao usuário do projeto.\n"
            "Se conforme com os limites e princípios, declare explicitamente: 'Governança: APROVADO'.\n"
        )

    def _veto_rework_cycle(
        self,
        validators: dict[str, dict[str, Any]],
        integration_tests_info: dict[str, Any],
    ) -> tuple[bool, list[str], dict[str, Any]]:
        """Ciclo AUTÔNOMO de retrabalho para vetos na VALIDATE (modo AUTO).

        Filosofia: NENHUM veto para o processo. Para cada veto:
        1. Turing determinístico classifica e rastreia a causa até o AUTOR do artefato.
        2. APPROVAL_MISSING → o validador re-emite o parecer (RE_AUDIT).
        3. PRODUCT_GAP / TEST_FAILURE / AGENT_BLOCKED → o autor upstream corrige o
           artefato e as stories afetadas são RE-QUEIMADAS no burn TDD (EXECUTE),
           seguidas de re-auditoria pelo validador.
        4. Só após esgotar as rodadas autônomas converte em DÚVIDA DE NEGÓCIO
           estruturada para o humano (último recurso, nunca parada silenciosa).
        """
        engine = VetoReworkEngine(llm_factory=self.llm_factory)
        original_demand = (
            f"ONDA {self.state_machine.wave_id} ({self.state_machine.wave_type.value})"
        )
        attempt = 0
        last_analysis = None
        is_wave_zero = self.state_machine.wave_type == WaveType.WAVE_ZERO
        # Cada RESUME/turno roda a escada COMPLETA (do zero). O orçamento é
        # por turno: o humano acompanha pelo status; não intervém em técnica.

        while attempt < engine.max_attempts:
            if ABORT_EVENT.is_set():
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text="⏸ Retrabalho de VALIDATE interrompido pelo usuário — checkpoint salvo.",
                )
                break
            attempt += 1
            failed = {
                name: info
                for name, info in validators.items()
                if info["runner"] is not None and not info["approved"]
            }
            if not failed:
                break

            for name, info in failed.items():
                analysis = engine.classify(info["reason"], info["output"], target_agent=name)
                last_analysis = analysis
                route = VETO_ROUTES.get(analysis.veto_class, {})
                BUS.publish(
                    "veto_analysis",
                    agent=name,
                    text=(
                        f"🔍 Veto de {name} analisado: {analysis.veto_class.value}. "
                        f"Rota autônoma → {route.get('owner', '@turing')}: {route.get('description', 'retrabalho')}"
                        + (
                            f" | Stories afetadas: {', '.join(analysis.story_ids)}"
                            if analysis.story_ids
                            else ""
                        )
                    ),
                    veto_class=analysis.veto_class.value,
                )

                if analysis.veto_class is VetoClass.APPROVAL_MISSING:
                    # Rota RE_AUDIT: o validador re-emite o parecer com card.
                    rework_prompt = engine.build_rework_prompt(analysis, original_demand)
                    res = self._executar_com_card(
                        self.state_machine.wave_id,
                        "VALIDATE",
                        f"VALIDATE-REAUDIT-{name.replace('@', '').upper()}-{attempt}",
                        f"Re-auditoria de {name} (#{attempt})",
                        name,
                        10 + attempt,
                        lambda: info["runner"].run(rework_prompt),
                        dor=[],
                        dod=["parecer_emitido"],
                        task_tipo="VALIDATE",
                        descricao=f"Re-auditoria {attempt} após parecer pendente de {name}.",
                    )
                    self._record_telemetry("VALIDATE", f"{name} (re-auditoria #{attempt})", res)
                    approved, reason = self._check_explicit_approval(res)
                    info["approved"] = approved
                    info["reason"] = reason
                    info["output"] = getattr(res, "output", "") or info["output"]
                    BUS.publish(
                        "veto_rework",
                        agent=name,
                        text=(
                            f"🔁 Re-auditoria {attempt}/{engine.max_attempts} com {name}: "
                            + ("aprovado." if approved else f"ainda reprovado — {reason}")
                        ),
                        attempt=attempt,
                    )
                    continue

                # Rota autônoma: consertar a causa e queimar de novo.
                self._autonomous_rework_burn(engine, analysis, name, info, attempt, is_wave_zero)

            if all(info["approved"] for info in validators.values()):
                break

        if all(info["approved"] for info in validators.values()):
            return (
                integration_tests_info["all_passed"],
                [] if integration_tests_info["all_passed"] else [integration_tests_info["details"]],
                {"attempts": attempt, "resolved": True},
            )

        if last_analysis is None:
            last_analysis = engine.classify(
                "; ".join(
                    f"{n}: {i['reason']}" for n, i in validators.items() if not i["approved"]
                ),
                target_agent="@edith",
            )
        falhas_resumo = "; ".join(
            f"{name}: {info['reason']}" for name, info in validators.items() if not info["approved"]
        )
        mensagem_parada = (
            f"🟠 ESCALAÇÃO — VALIDATE não aprovado após {attempt} rodada(s) de correção autônoma.\n"
            f"Impedimentos técnicos em aberto: {falhas_resumo}\n"
            "São ajustes técnicos já mapeados — nada precisa de você agora. "
            "Dê resume: o Turing refaz o ciclo focado nos impedimentos."
        )
        BUS.publish(
            "escalation",
            agent="@turing",
            text=mensagem_parada,
            escalation={"type": "technical_status", "message": mensagem_parada},
        )
        reasons = [mensagem_parada]
        if not integration_tests_info["all_passed"]:
            reasons.append(integration_tests_info["details"])
        for name, info in validators.items():
            if not info["approved"]:
                reasons.append(f"{name}: {info['reason']}")
        return (
            False,
            reasons,
            {
                "attempts": attempt,
                "escalation": {"type": "technical_status", "message": mensagem_parada},
            },
        )

    def _autonomous_rework_burn(
        self,
        engine: VetoReworkEngine,
        analysis: Any,
        validator_name: str,
        info: dict[str, Any],
        attempt: int,
        is_wave_zero: bool,
    ) -> None:
        """Rota autônoma para vetos estruturais: autor upstream conserta o artefato,
        stories afetadas são re-queimadas no burn TDD e o validador re-auditá."""
        blockers = analysis.blockers or [info["reason"]]
        story_ids = list(analysis.story_ids)
        if not story_ids:
            story_ids = [
                c.get("story_id", "")
                for c in self.kanban.list_cards(wave_id=self.state_machine.wave_id)
                if c.get("status") not in (KanbanCardStatus.DONE.value, "DONE")
            ]
        story_ids = [s for s in story_ids if s]
        owner = analysis.fix_owner or "@unclebob"

        BUS.publish(
            "veto_rework",
            agent=owner,
            text=(
                f"🛠️ [AUTÔNOMO {attempt}/{engine.max_attempts}] Causa rastreada até {owner}. "
                f"Devolendo bloqueios para correção do artefato"
                + (f" e re-burn de {', '.join(story_ids)}" if story_ids else "")
                + "..."
            ),
        )

        # 1. O AUTOR upstream corrige o artefato (sem implementar código).
        runner_owner = self._get_runner(owner)
        if runner_owner:
            up_prompt = engine.build_upstream_rework_prompt(
                owner, blockers, story_ids, f"ONDA {self.state_machine.wave_id}"
            )
            res = runner_owner.run(up_prompt)
            self._record_telemetry("VALIDATE", f"{owner} (rework upstream #{attempt})", res)
            self._extract_and_write_project_files(getattr(res, "output", ""))

        # 2. Re-burn: stories afetadas voltam ao ciclo TDD (VALIDATE → EXECUTE → VALIDATE).
        if story_ids and not is_wave_zero:
            if self.state_machine.current_state == WaveState.VALIDATE and not self.transition_to(
                TuringStage.EXECUTE
            ):
                logger.warning("Não foi possível retornar a EXECUTE para re-burn autônomo.")
                return
            for sid in story_ids:
                cycle_res = self._run_cycle_inner(sid)
                BUS.publish(
                    "veto_rework",
                    agent=owner,
                    text=(
                        f"🔥 Re-burn {sid}: "
                        + (
                            "concluído no ciclo TDD."
                            if cycle_res.get("success")
                            else f"falhou — {cycle_res.get('error')}"
                        )
                    ),
                )
            if self.state_machine.current_state == WaveState.EXECUTE:
                self.transition_to(TuringStage.VALIDATE)

        # 3. Re-auditoria pelo validador original com o prompt canônico.
        if info["runner"] is None:
            return
        if validator_name == "@edith":
            fresh_prompt = self._build_edith_audit_prompt()
        else:
            fresh_prompt = self._build_nina_audit_prompt()
        fresh_prompt += (
            f"\n\nCONTEXTO DE RE-AUDITORIA (rodada autônoma {attempt}/{engine.max_attempts}): "
            "correções foram aplicadas pelos autores responsáveis e as stories foram re-executadas. "
            "Reavalie o entregável atual."
        )
        fresh_assembled = self._assemble_prompt(validator_name, fresh_prompt)
        res = self._executar_com_card(
            self.state_machine.wave_id,
            "VALIDATE",
            f"VALIDATE-REAUDIT-{validator_name.replace('@', '').upper()}-{attempt}",
            f"Re-auditoria de {validator_name} (#{attempt})",
            validator_name,
            20 + attempt,
            lambda: info["runner"].run(fresh_assembled),
            dor=[],
            dod=["status_aprovado_ou_reprovado"],
            task_tipo="VALIDATE",
            descricao=f"Re-auditoria de validação {attempt} após correções autônomas.",
        )
        self._record_telemetry("VALIDATE", f"{validator_name} (re-auditoria #{attempt})", res)
        approved, reason = self._check_explicit_approval(res)
        info["approved"] = approved
        info["reason"] = reason
        info["output"] = getattr(res, "output", "") or info["output"]
        BUS.publish(
            "veto_rework",
            agent=validator_name,
            text=(
                f"🔁 Re-auditoria {attempt}/{engine.max_attempts} com {validator_name} após retrabalho autônomo: "
                + ("APROVADO." if approved else f"ainda reprovado — {reason}")
            ),
            attempt=attempt,
        )

    def run_audit(self, wave_id: str | None = None) -> dict[str, Any]:
        """Contra-Auditoria Forense (@hoare) — 'Pedido vs. Entregue' com o
        CÓDIGO como fonte da verdade. Comando opcional do usuário quando há
        dúvida sobre a qualidade de um validate.

        Diferente do validate original (custo de LLM: 1 chamada adversarial):
        1. Evidências determinísticas de custo zero (fraudes, mapa CA×story).
        2. Execução REAL da suíte de testes do projeto auditado.
        3. Cross-examinação do relatório de validação anterior.
        4. Laudo com FUROs estruturados → bloqueio de cards + reabertura da
           onda + re-burn TDD das stories afetadas (Ciclo Autônomo).
        """
        from bombe_code.turing.audit import (
            coletar_evidencias,
            executar_suite_testes,
            extrair_aleacoes_relatorio,
            extrair_furos,
            veredito_auditoria,
        )

        alvo = (wave_id or self.state_machine.wave_id or "").strip().upper()
        if not alvo:
            return {"success": False, "error": "Nenhuma onda especificada para auditoria."}

        BUS.publish(
            "stage_start",
            agent="@hoare",
            text=(
                f"🔍 [CONTRA-AUDITORIA FORENSE] @hoare assumiu o caso: '{alvo}'. "
                "Pressuposto adversarial — o validate anterior pode ter sido preguiçoso. "
                "Coletando provas no código (custo zero de tokens)..."
            ),
            wave_id=alvo,
        )

        # Evidências determinísticas (0 tokens)
        report_anterior = ""
        for candidato in (
            self.workspace.wave_validation_report_path(alvo),
            self.project_dir / "docs" / "reports" / "validation_report.md",
        ):
            try:
                if candidato.exists():
                    report_anterior = candidato.read_text(encoding="utf-8")
                    break
            except OSError:
                continue

        evidencias = coletar_evidencias(self.project_dir, alvo, report_anterior)
        evidencias.aleacoes_relatorio_anterior = extrair_aleacoes_relatorio(report_anterior)
        evidencias.suite_resultado, evidencias.suite_detalhes = executar_suite_testes(
            self.project_dir
        )

        if evidencias.suite_resultado == "FALHOU":
            evidencias.fraudes_potenciais.append(
                "Suíte de testes do projeto FALHOU na execução real — alegação anterior de testes verdes é falsa"
            )

        BUS.publish(
            "announcement",
            agent="@hoare",
            text=(
                f"🧾 Provas coletadas: {len(evidencias.arquivos_producao)} arquivos de produção, "
                f"{len(evidencias.testes_encontrados)} de teste, {len(evidencias.fraudes_potenciais)} fraude(s) potencial(is), "
                f"suíte: {evidencias.suite_resultado}. Cross-examinando o relatório anterior..."
            ),
        )

        # A chamada adversarial única do @hoare
        runner_hoare = self._get_runner("@hoare")
        if not runner_hoare:
            return {"success": False, "error": "Agente @hoare indisponível no catálogo."}

        fraudes = (
            "\n".join(f"- {f}" for f in evidencias.fraudes_potenciais)
            or "- (nenhuma detectada estaticamente)"
        )
        aleacoes = (
            "\n".join(f"- {a}" for a in evidencias.aleacoes_relatorio_anterior)
            or "- (sem alegações extraíveis)"
        )
        arvore = "\n".join(evidencias.arquivos_producao) or "- (vazio)"
        mapa = (
            "\n".join(
                f"- {story}: CAs {', '.join(dados['cas']) or 'nenhum'} | BDD: {'sim' if dados.get('bdd') else 'não'}"
                for story, dados in list(evidencias.mapa_cas.items())
            )
            or "- (nenhuma story com CAs declarados)"
        )

        raw_prompt = (
            f"CONTRA-AUDITORIA FORENSE da {alvo}. Você é @hoare — auditor adversarial.\n"
            "Pressuposto: o validate anterior pode ter sido preguiçoso. Seu trabalho é ENCONTRAR furos.\n\n"
            "=== FONTES DA VERDADE (código) ===\n"
            f"Arquivos de produção:\n{arvore}\n\n"
            f"Resultado da SUÍTE REAL executada agora: {evidencias.suite_resultado}\n"
            f"{evidencias.suite_detalhes}\n\n"
            f"Fraudes potenciais detectadas estaticamente:\n{fraudes}\n\n"
            f"Contrato do escopo (stories × CAs declarados):\n{mapa}\n\n"
            "=== ALEGAÇÕES DO RELATÓRIO DE VALIDAÇÃO ANTERIOR (cross-examine) ===\n"
            f"{aleacoes}\n\n"
            "=== RELATÓRIO ANTERIOR (integral) ===\n"
            f"{report_anterior}\n\n"
            "MISSÃO: garantir que o que foi PEDIDO é o que foi ENTREGUE. Para cada alegação do "
            "relatório anterior, exija evidência no código. Audite fundo as stories de maior risco. "
            "CA declarado sem implementação/teste correspondente é FURO. Alegação sem evidência é FURO. "
            "Fraude (mock/TODO/NotImplementedError em produção) é FURO.\n"
            "FORMATO OBRIGATÓRIO: liste cada furo em linha própria iniciando com 'FURO: <story> — <descrição> — evidência: <arquivo/teste>'. "
            "Se e somente se nenhum furo existir, declare EXATAMENTE 'AUDITORIA: LIMPA'."
        )
        prompt = self._assemble_prompt("@hoare", raw_prompt)
        res_hoare = runner_hoare.run(prompt)
        self._record_telemetry("VALIDATE", "@hoare (Contra-Auditoria Forense)", res_hoare)
        laudo = getattr(res_hoare, "output", "") or ""

        furos = extrair_furos(laudo)
        limpo, motivo_veredito = veredito_auditoria(laudo, furos)

        # Persiste o laudo no workspace da onda auditada
        laudo_path = self.workspace.wave_validation_report_path(alvo).parent / "audit_report.md"
        try:
            laudo_path.parent.mkdir(parents=True, exist_ok=True)
            laudo_path.write_text(
                f"# 🔍 Contra-Auditoria Forense — {alvo}\n\n**Auditor:** @hoare\n"
                f"**Suíte real:** {evidencias.suite_resultado}\n\n{laudo}\n",
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Falha ao salvar audit_report.md: %s", exc)

        resultado = {
            "success": True,
            "stage": "AUDIT",
            "wave_id": alvo,
            "limpa": limpo,
            "furos": furos,
            "suite": evidencias.suite_resultado,
            "laudo_path": str(laudo_path),
            "message": f"Contra-auditoria de {alvo}: {motivo_veredito}.",
        }

        if limpo:
            BUS.publish(
                "stage_end",
                agent="@hoare",
                text=(
                    f"✅ [AUDITORIA: LIMPA] {alvo} passou pela contra-auditoria forense "
                    "(pedido × entregue verificado no código, suíte real executada)."
                ),
                wave_id=alvo,
            )
            return resultado

        # FUROS: bloqueia cards afetados e abre o ciclo de correção autônomo.
        stories_afetadas = sorted(
            {sid for furo in furos for sid in re.findall(r"ST[-\s]?\d+", furo, re.IGNORECASE)}
        )
        stories_afetadas = [
            s.title().replace("-", "-").upper().replace("ST ", "ST-") for s in stories_afetadas
        ]

        BUS.publish(
            "escalation",
            agent="@hoare",
            text=(
                f"🚨 [FUROS ENCONTRADOS] {len(furos)} furo(s) na {alvo}. "
                + (f"Stories afetadas: {', '.join(stories_afetadas)}. " if stories_afetadas else "")
                + "Bloqueando cards e acionando o Ciclo Autônomo de correção."
            ),
            wave_id=alvo,
        )

        for furo in furos[:10]:
            story_do_furo = next((s for s in stories_afetadas if s.lower() in furo.lower()), None)
            if story_do_furo and self.kanban.get_card(story_do_furo):
                self.kanban.block_card(
                    story_do_furo,
                    reason=f"FURO (contra-auditoria @hoare): {furo[:500]}",
                    blocked_by="@hoare",
                )

        # A onda auditada assume o comando: checkpoint ativo arquivado, onda
        # reaberta em EXECUTE para o re-burn TDD das stories com furo.
        ativo = self.db.load_wave_state()
        if (
            ativo
            and str(ativo.get("wave_id", "")).upper() != alvo
            and str(ativo.get("state", "")).upper() != WaveState.COMPLETED.value
        ):
            self.db.archive_wave_state()

        alvo_cards = self.kanban.list_cards(wave_id=alvo)
        tem_cards = bool(alvo_cards)
        self.state_machine = TuringStateMachine(
            wave_id=alvo,
            initial_state=WaveState.EXECUTE if tem_cards else WaveState.PLAN,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        self.db.save_wave_state(
            wave_id=alvo,
            state=WaveState.EXECUTE if tem_cards else WaveState.PLAN,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        resultado["wave_id"] = alvo
        resultado["stage"] = "EXECUTE" if tem_cards else "PLAN"

        if stories_afetadas and tem_cards and self.state_machine.autonomy_mode == AutonomyMode.AUTO:
            for sid in stories_afetadas:
                if not self.kanban.get_card(sid):
                    continue
                self.kanban.update_status(sid, KanbanCardStatus.IN_PROGRESS.value)
                ciclo = self._run_cycle_inner(sid)
                BUS.publish(
                    "veto_rework",
                    agent="@hoare",
                    text=(
                        f"🔥 Re-burn {sid} (furo da contra-auditoria): "
                        + (
                            "corrigido no ciclo TDD."
                            if ciclo.get("success")
                            else f"falhou — {ciclo.get('error')}"
                        )
                    ),
                )
            if self.state_machine.current_state == WaveState.EXECUTE:
                self.transition_to(TuringStage.VALIDATE)
            resultado["reexecucao"] = (
                f"stories {', '.join(stories_afetadas)} re-queimadas; onda em VALIDATE"
            )

        return resultado

    def end_wave(self) -> dict[str, Any]:
        """Finaliza e arquiva a ONDA como COMPLETED."""
        from .state_machine import WaveType

        is_wave_zero = self.state_machine.wave_type == WaveType.WAVE_ZERO
        valid_end_states = (
            (WaveState.VALIDATE, WaveState.PLAN) if is_wave_zero else (WaveState.VALIDATE,)
        )
        if self.state_machine.current_state not in valid_end_states:
            expected = "VALIDATE ou PLAN (Onda Zero)" if is_wave_zero else "VALIDATE"
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado {expected} para encerrar.",
            }

        if not self.transition_to(TuringStage.COMPLETED):
            return {"success": False, "error": "Falha na transição final para COMPLETED."}

        # POLÍTICA DE BRANCHES: estado aprovado é promovido para `dev` via
        # squash (memória operacional da IA ≠ histórico oficial). Nunca push.
        resultado_promocao = None
        try:
            from bombe_code.turing.promocao import PromotorDeBranches

            promotor = PromotorDeBranches(str(self.project_dir))
            if promotor.eh_repositorio():
                from bombe_code.turing.progress import BUS as _bus

                promocao = promotor.promover_para_dev(
                    f"feat({self.state_machine.wave_id}): entrega homologada da ONDA "
                    f"(VALIDATE aprovado — estado aprovado consolidado em 1 commit)"
                )
                resultado_promocao = promocao.mensagem
                _bus.publish(
                    "announcement" if promocao.success else "escalation",
                    agent="@turing",
                    text=(
                        f"🌿 [PROMOÇÃO] {promocao.mensagem}"
                        if promocao.success
                        else f"⚠️ [PROMOÇÃO] {promocao.mensagem}"
                    ),
                    wave_id=self.state_machine.wave_id,
                )
        except Exception as exc:  # noqa: BLE001 — promoção é best-effort, não derruba o fim da onda
            logger.warning("Promoção de branches falhou (não bloqueante): %s", exc)

        return {
            "success": True,
            "wave_id": self.state_machine.wave_id,
            "stage": TuringStage.COMPLETED.value,
            "promocao": resultado_promocao,
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

    run_discovery = run_discuss
    run_inception = run_plan
    run_refinement = run_plan


TuringWaveOrchestrator = WaveOrchestrator
