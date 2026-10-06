"""VetoReworkEngine — Ciclo Autônomo de Retrabalho para Vetos da ONDA.

Filosofia (visão do Bombe Code): o runtime é autônomo ao máximo permitido.
NENHUM veto pode parar o processo. O Turing determinístico classifica o veto,
rastreia a causa até o artefato e o AGENTE AUTOR responsável (upstream ou
downstream), devolve o problema para esse agente consertar, re-queima as
stories afetadas no ciclo TDD e re-auditá. O humano só é convocado como
ÚLTIMO recurso, com uma DÚVIDA DE NEGÓCIO estruturada.

Fluxo: veto → análise determinística → (opcional) LLM em ambiguidade →
rota para o autor responsável → artefato corrigido → burn TDD → re-auditoria.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class VetoClass(str, Enum):
    """Classificação determinística da causa do veto."""

    APPROVAL_MISSING = "APPROVAL_MISSING"  # Parecer sem aprovação explícita (formato)
    PRODUCT_GAP = "PRODUCT_GAP"  # Bloqueios reais de produto/requisitos
    TEST_FAILURE = "TEST_FAILURE"  # Suíte de testes/verificação falhou
    AGENT_BLOCKED = "AGENT_BLOCKED"  # Agente declarou bloqueio/impedimento


# Rota de autonomia: cada classe de veto tem responsável e ação no próprio framework.
VETO_ROUTES: dict[VetoClass, dict[str, str]] = {
    VetoClass.APPROVAL_MISSING: {
        "action": "RE_AUDIT",
        "owner": "validator",
        "description": "Validador re-emite o parecer com declaração explícita",
    },
    VetoClass.PRODUCT_GAP: {
        "action": "REWORK_IMPLEMENTATION",
        "owner": "@unclebob",
        "description": "Autor upstream corrige o artefato e o Tech Lead re-queima as stories no ciclo TDD",
    },
    VetoClass.TEST_FAILURE: {
        "action": "FIX_TESTS",
        "owner": "@aniche",
        "description": "QA arquitecto corrige suíte/implementação e reexecuta a verificação",
    },
    VetoClass.AGENT_BLOCKED: {
        "action": "RESOLVE_IMPEDIMENT",
        "owner": "@turing",
        "description": "Orquestrador resolve o impedimento com o agente que detém o artefato faltante",
    },
}


@dataclass
class VetoAnalysis:
    """Resultado da análise de um veto."""

    veto_class: VetoClass
    source: str = "deterministic"  # deterministic | llm
    reason: str = ""
    target_agent: str | None = None
    rework_prompt: str | None = None
    blockers: list[str] = field(default_factory=list)
    story_ids: list[str] = field(default_factory=list)
    fix_owner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class VetoReworkEngine:
    """Analisa vetos, rastreia a autoria da causa e produz as rotas de correção."""

    # Rastreamento de autoria upstream por palavras-chave do bloqueio
    UPSTREAM_TRACES: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (
            re.compile(r"\bprd\b|requisito|\brf[- ]?\d|\brnf|escopo|persona|rice", re.IGNORECASE),
            "@grace",
        ),
        (
            re.compile(r"jornada|journey|entry point|navega|mapeamento de tela", re.IGNORECASE),
            "@alan",
        ),
        (
            re.compile(
                r"arquitetura|\badr\b|camada|porta\b|seam|mon[oó]lito|limpeza de arquitetura",
                re.IGNORECASE,
            ),
            "@ieru",
        ),
        (
            re.compile(
                r"schema|modelagem|migra|\bbd\b|banco de dados|\bsql\b|tabela|\bmer\b|foreign key",
                re.IGNORECASE,
            ),
            "@codd",
        ),
        (re.compile(r"\bnosql\b|vetorial|graph|documento", re.IGNORECASE), "@claudia"),
        (re.compile(r"amea[çc]a|stride|cripto|seguran[çc]a|owasp", re.IGNORECASE), "@barreto"),
        (
            re.compile(
                r"story|h[íi]storia|backlog|crit[ée]rio de aceite|\bbdd\b|\bdor\b|\binvest\b|fatia",
                re.IGNORECASE,
            ),
            "@caroli",
        ),
        (re.compile(r"wireframe|design|usabilidad|heur[íi]stica|ui/ux", re.IGNORECASE), "@norman"),
    ]

    _BLOCKER_ITEM_RE = re.compile(r"^\s*(?:\d+\s*[\.\)\-]|[-*•])\s+(.+)$")
    _BLOCKER_HEADER_RE = re.compile(r"^\**\s*bloqueios?\b[^\n:]*:?\**\s*$", re.IGNORECASE)

    def __init__(
        self,
        llm_factory: Any = None,
        max_attempts: int = 2,
        permitir_llm: bool | None = None,
    ) -> None:
        self.llm_factory = llm_factory
        self.max_attempts = max_attempts
        # None = automático (desligado sob pytest para determinismo)
        import os

        self.permitir_llm = (
            permitir_llm
            if permitir_llm is not None
            else not bool(os.environ.get("PYTEST_CURRENT_TEST"))
        )

    # ------------------------------------------------------------ extração
    def extract_blockers(self, output: str) -> list[str]:
        """Extrai bloqueios de pareceres reais: prefixo 'BLOQUEIO:', seções
        'Bloqueios (...):' com listas numeradas/bullets."""
        if not output:
            return []
        blockers: list[str] = []
        collecting = False
        for raw_line in output.splitlines():
            stripped = raw_line.strip()
            low = stripped.lower().lstrip("*#>- ")
            if low.startswith("bloqueio:"):
                blockers.append(stripped.split(":", 1)[1].strip(" -*"))
                collecting = True
                continue
            if self._BLOCKER_HEADER_RE.match(stripped):
                collecting = True
                continue
            if collecting:
                item_match = self._BLOCKER_ITEM_RE.match(stripped)
                if item_match:
                    item = item_match.group(1).strip()
                    if item:
                        blockers.append(item)
                    continue
                if not stripped:
                    continue  # linha em branco dentro da seção
                collecting = False  # fim da seção de bloqueios
        return blockers

    def extract_story_ids(self, text: str) -> list[str]:
        """Extrai IDs de stories (ST-001, ST 2, st003...) normalizados."""
        if not text:
            return []
        found = re.findall(r"\bST[-\s]?(\d{1,4})\b", text, re.IGNORECASE)
        unique: list[str] = []
        for n in found:
            sid = f"ST-{n.zfill(3)}"
            if sid not in unique:
                unique.append(sid)
        return unique

    # ------------------------------------------------------- classificação
    def classify(
        self,
        reason_text: str,
        validator_output: str = "",
        target_agent: str | None = None,
    ) -> VetoAnalysis:
        """Classifica o veto deterministicamente; LLM só em ambiguidade real."""
        reason = (reason_text or "").strip()
        output = validator_output or ""
        reason_lower = reason.lower()

        # Bloqueios estruturados no output têm prioridade: são a evidência real
        # do veto (mesmo que o reason do gate seja a linha genérica Default-Deny).
        blockers_found = self.extract_blockers(output)

        if "suíte de testes" in reason_lower or "suite de testes" in reason_lower:
            analysis = VetoAnalysis(
                veto_class=VetoClass.TEST_FAILURE,
                reason=reason,
                target_agent=target_agent or "@aniche",
            )
        elif blockers_found:
            # O validador itemizou bloqueios reais (mesmo sem keyword de reprovação).
            analysis = VetoAnalysis(
                veto_class=VetoClass.PRODUCT_GAP,
                reason=reason,
                target_agent=target_agent,
            )
        elif (
            "bloqueio registrado" in reason_lower
            or "agente reportou bloqueio" in reason_lower
            or "🛑" in reason
            or "impedimento" in reason_lower
        ):
            # AGENT_BLOCKED somente para bloqueios DECLARADOS pelo agente —
            # nunca pela palavra "bloqueios" aparecendo num excerpt de parecer.
            analysis = VetoAnalysis(
                veto_class=VetoClass.AGENT_BLOCKED,
                reason=reason,
                target_agent=target_agent,
            )
        elif "ausência de aprovação explícita" in reason_lower or (
            "nenhum resultado retornado" in reason_lower
        ):
            analysis = VetoAnalysis(
                veto_class=VetoClass.APPROVAL_MISSING,
                reason=reason,
                target_agent=target_agent,
            )
        else:
            analysis = VetoAnalysis(
                veto_class=VetoClass.APPROVAL_MISSING,
                reason=reason,
                target_agent=target_agent,
            )

        # Enriquecimento: bloqueios, stories afetadas e autor da causa
        analysis.blockers = blockers_found
        analysis.story_ids = self.extract_story_ids(output)
        if analysis.veto_class in (VetoClass.PRODUCT_GAP, VetoClass.TEST_FAILURE):
            analysis.fix_owner = self.trace_owner(analysis.blockers, analysis.veto_class)

        # Delegação probabilística apenas em ambiguidade real
        if self.llm_factory is not None and analysis.veto_class in (
            VetoClass.APPROVAL_MISSING,
            VetoClass.PRODUCT_GAP,
        ):
            llm_class = self._classify_with_llm(reason, output)
            if llm_class is not None:
                analysis.veto_class = llm_class
                analysis.source = "llm"
                analysis.fix_owner = self.trace_owner(analysis.blockers, llm_class)

        analysis.rework_prompt = self.build_rework_prompt(analysis)
        return analysis

    def trace_owner(self, blockers: list[str], veto_class: VetoClass) -> str:
        """Rastreia o autor do artefato causador do veto (upstream/downstream)."""
        if veto_class == VetoClass.TEST_FAILURE:
            return "@aniche"
        text = " ".join(blockers)
        for pattern, owner in self.UPSTREAM_TRACES:
            if pattern.search(text):
                return owner
        return "@unclebob"

    def _classify_with_llm(self, reason: str, validator_output: str) -> VetoClass | None:
        """Turing probabilístico: classifica o veto sob demanda (JSON estrito).

        Determinismo em teste: sob pytest a classificação LLM é DESLIGADA —
        o fallback determinístico é a fonte da verdade (nunca chamar rede).
        """
        if not self.permitir_llm:
            return None
        try:
            agent = self.llm_factory.create_agent(
                system_prompt="Você é o classificador de vetos do Turing Runtime. Responda apenas JSON."
            )
            prompt = (
                "Classifique o veto de validação abaixo em EXATAMENTE uma categoria:\n"
                "- APPROVAL_MISSING: o parecer não declarou aprovação explícita, mas não há objeção real.\n"
                "- PRODUCT_GAP: há bloqueios/requisitos de produto não atendidos listados.\n"
                "- TEST_FAILURE: a suíte de testes ou verificação técnica falhou.\n\n"
                f"Motivo do veto: {reason[:500]}\n\n"
                f"Parecer do validador (trecho): {validator_output[:1500]}\n\n"
                'Responda exclusivamente: {"veto_class": "<categoria>"}'
            )
            raw = agent.run_sync(prompt)
            output = str(getattr(raw, "output", getattr(raw, "data", raw)))
            match = re.search(r"\{.*\}", output, re.DOTALL)
            if not match:
                return None
            data = json.loads(match.group(0))
            cls = str(data.get("veto_class", "")).strip().upper()
            if cls in VetoClass.__members__:
                return VetoClass(cls)
        except Exception as exc:  # noqa: BLE001 — LLM é otimização, nunca obrigatória
            logger.warning(
                "Classificação LLM do veto falhou (%s); usando análise determinística.", exc
            )
        return None

    # -------------------------------------------------------- prompts
    def build_rework_prompt(self, analysis: VetoAnalysis, original_demand: str = "") -> str:
        """Prompt de re-auditoria para o VALIDADOR (rota RE_AUDIT)."""
        approval_phrase = (
            "declare EXATAMENTE 'Homologação: APROVADO'"
            if (analysis.target_agent or "") == "@edith"
            else "declare EXATAMENTE 'Governança: APROVADO'"
        )
        header = (
            f"🔁 RE-AUDITORIA SOLICITADA PELO TURING RUNTIME (ciclo autônomo de veto).\n"
            f"Seu parecer anterior foi vetado. Motivo registrado pelo gate: {analysis.reason}\n"
        )
        if original_demand:
            header += f"Demanda original em auditoria: {original_demand[:300]}\n"
        body = (
            "O veto ocorreu porque o parecer não declarou aprovação explícita (Lei da Restrição / Default-Deny).\n"
            "Reavalie o entregável e emita um parecer novo e conclusivo:\n"
            f"- Se estiver aprovado, {approval_phrase} no texto.\n"
            "- Se houver objeção real, liste cada bloqueio em linha própria iniciando com 'BLOQUEIO:'.\n"
            "Pareceres ambíguos serão vetados novamente pelo gate determinístico."
        )
        return f"{header}\n{body}"

    def build_upstream_rework_prompt(
        self,
        owner: str,
        blockers: list[str],
        story_ids: list[str],
        original_demand: str = "",
    ) -> str:
        """Prompt para o AUTOR upstream consertar o artefato causador do veto.

        O autor NÃO implementa código: conserta o artefato (PRD, story, ADR,
        modelagem...) e o burn TDD é re-executado pelo downstream.
        """
        blocker_lines = (
            "\n".join(f"- {b}" for b in blockers) or "- (ver parecer completo do validador)"
        )
        stories = ", ".join(story_ids) if story_ids else "stories afetadas da onda atual"
        artifact_map = {
            "@grace": "PRD (docs/briefings/PRD.md) e requisitos",
            "@alan": "jornada/navegação (docs/architecture/journey.md)",
            "@ieru": "arquitetura/ADRs (docs/architecture/)",
            "@codd": "modelagem de dados (docs/architecture/db.md)",
            "@claudia": "modelagem NoSQL/vetorial",
            "@barreto": "modelo de ameaças/segurança",
            "@caroli": "stories/backlog PBB (arquivos das stories)",
            "@norman": "UI/UX e design system",
            "@aniche": "suíte de testes (tests/)",
            "@unclebob": "coordenação técnica da correção",
        }
        artifact = artifact_map.get(owner, "artefato sob sua autoria")
        return (
            "🔁 RETRABALHO UPSTREAM SOLICITADO PELO TURING RUNTIME (autonomia total — nenhum humano será acionado).\n"
            f"A validação DOWNSTREAM reprovou a ONDA e rastreou a causa até um artefato da SUA autoria ({owner}):\n"
            f"Artefato esperado sob sua responsabilidade: {artifact}\n\n"
            f"Bloqueios declarados pela auditoria:\n{blocker_lines}\n\n"
            f"Stories afetadas: {stories}\n"
            + (f"Demanda original: {original_demand[:300]}\n" if original_demand else "")
            + "\nSua missão como AUTOR do artefato:\n"
            "1. Corrija/atualize o artefato de sua responsabilidade para eliminar a causa dos bloqueios.\n"
            "2. Se a causa afetar stories, atualize os ARQUIVOS das stories (critérios de aceite/BDD) para refletir a correção.\n"
            "3. NÃO implemente código de produção: o burn TDD (RED→GREEN→REFACTOR) será re-executado pelo downstream.\n"
            "4. Não corte escopo contratado nem invente escopo novo — corrija a divergência apontada.\n"
            "5. Ao concluir, declare explicitamente: 'RETRABALHO UPSTREAM CONCLUÍDO'."
        )

    # ------------------------------------------------------ escalonamento
    def build_escalation(
        self,
        analysis: VetoAnalysis,
        attempts: int,
        validator_outputs: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """DÚVIDA DE NEGÓCIO estruturada — ÚLTIMO recurso após esgotar o ciclo autônomo."""
        suggested_owner = analysis.fix_owner or (
            {
                VetoClass.APPROVAL_MISSING: analysis.target_agent or "@edith",
                VetoClass.PRODUCT_GAP: "@unclebob",
                VetoClass.TEST_FAILURE: "@aniche",
                VetoClass.AGENT_BLOCKED: analysis.target_agent or "@turing",
            }.get(analysis.veto_class, "@turing")
        )

        blockers = list(analysis.blockers)
        if not blockers:
            for output in (validator_outputs or {}).values():
                blockers.extend(self.extract_blockers(output or ""))

        question = (
            f"❓ DÚVIDA DE NEGÓCIO (intervenção humana — último recurso após {attempts} rodada(s) autônoma(s) de retrabalho).\n"
            f"Os vetos persistem e exigem decisão de negócio que excede a autonomia dos agentes.\n"
            f"Classificação: {analysis.veto_class.value} | Responsável técnico sugerido: {suggested_owner}.\n"
            + (
                "Bloqueios em aberto:\n" + "\n".join(f"- {b}" for b in blockers)
                if blockers
                else analysis.reason
            )
        )

        return {
            "type": "business_question",
            "veto_class": analysis.veto_class.value,
            "classification_source": analysis.source,
            "reason": analysis.reason,
            "attempts": attempts,
            "target_agent": analysis.target_agent,
            "suggested_owner": suggested_owner,
            "blockers": blockers,
            "question": question,
            "message": question,
        }
