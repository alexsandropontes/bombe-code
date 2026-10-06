"""TuringWaiter — O Garçom Onisciente do Turing (3-Tier Intent Dispatcher).

Atende o desenvolvedor no salão, higieniza a mensagem e despacha comandos
e métodos canônicos da ONDA através de uma cascata de 3 Tiers:
- Tier 1: Literal Slash Command (`/wave ...`) -> 0 tokens, 0 ms.
- Tier 2: NLU Local Determinístico (`TuringIntentClassifier`) -> 0 tokens, microsegundos.
- Tier 3: Fallback Roteador de Intenções Enxuto (sem ferramentas de escrita, apenas classificação).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from .classifier import TuringIntentClassifier, TuringIntentResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TuringAction:
    tier: int  # 1: Literal Slash, 2: Local NLU, 3: LLM Intent Fallback
    intention: str
    confidence: float
    command: str | None = None
    action_type: str | None = None
    action_args: dict[str, Any] = field(default_factory=dict)
    slots: dict[str, str] = field(default_factory=dict)
    needs_llm: bool = False
    raw_input: str = ""


class TuringWaiter:
    """Garçom da ONDA responsável por interpretar e despachar toda entrada em modo TDD."""

    INTENT_TO_COMMAND: ClassVar[dict[str, str]] = {
        "wave_status": "/wave status",
        "start_plan": "/wave plan",
        "validate_wave": "/wave validate",
        "review_cycle": "/review",
        "approve_execution": "/wave execute",
        "workflow_resume": "/wave resume",
    }

    def __init__(self, classifier: TuringIntentClassifier | None = None) -> None:
        self.classifier = classifier or TuringIntentClassifier()

    def _map_to_action(
        self,
        intent_result: TuringIntentResult,
        raw_input: str,
        stage: str | None = None,
    ) -> tuple[str | None, str | None, dict[str, Any]]:
        """Mapeia um resultado de intenção para (command, action_type, action_args)."""
        intent = intent_result.intention
        slots = intent_result.slots

        if intent == "start_discuss":
            # Tópico ou briefing integral
            topic = slots.get("topic") or raw_input.strip()
            short_topic = topic[:80].replace("\n", " ").strip()
            return f"/wave discuss {short_topic}", "run_discuss", {"topic": raw_input.strip()}

        if intent == "start_plan":
            return "/wave plan", "run_plan", {}

        if intent == "start_cycle":
            story_id = slots.get("story_id")
            if story_id:
                return f"/wave execute {story_id}", "run_cycle", {"story_id": story_id}
            return "/wave execute", "run_cycle", {}

        if intent == "workflow_resume":
            return "/wave resume", "run_cycle", {}

        if intent == "approve_execution":
            return "/wave execute", "run_execute", {}

        if intent == "validate_wave":
            return "/wave validate", "run_validate", {}

        if intent == "review_cycle":
            return "/review", "review_cycle", {}

        if intent == "wave_status":
            return "/wave status", "wave_status", {}

        if intent == "toggle_mode":
            mode = slots.get("mode", "auto")
            return f"/autonomy {mode}", "set_autonomy", {"mode": mode}

        cmd = self.INTENT_TO_COMMAND.get(intent)
        return cmd, intent, {}

    async def attend(
        self,
        user_input: str,
        stage: str | None = None,
        is_greenfield: bool = False,
        adapter: Any | None = None,
    ) -> TuringAction:
        """Processa a entrada do desenvolvedor através da esteira de 3 Tiers."""
        raw = (user_input or "").strip()
        if not raw:
            return TuringAction(
                tier=1,
                intention="empty",
                confidence=1.0,
                command=None,
                raw_input="",
            )

        # TIER 1: Comando Literal com Barra (0 tokens, 0 ms)
        if raw.startswith("/"):
            return TuringAction(
                tier=1,
                intention="literal_slash",
                confidence=1.0,
                command=raw,
                action_type="slash_command",
                action_args={"command_line": raw},
                raw_input=raw,
            )

        # TIER 2: NLU Local Determinístico e Contextual (0 tokens, microsegundos)
        local_result = self.classifier.classify(
            raw,
            stage=stage,
            is_greenfield=is_greenfield,
        )

        if not local_result.needs_llm and local_result.confidence >= 0.70:
            cmd, action_type, action_args = self._map_to_action(local_result, raw, stage=stage)
            return TuringAction(
                tier=2,
                intention=local_result.intention,
                confidence=local_result.confidence,
                command=cmd,
                action_type=action_type,
                action_args=action_args,
                slots=local_result.slots,
                needs_llm=False,
                raw_input=raw,
            )

        # TIER 3: Fallback Roteador de Intenções Enxuto (Classificação Pura, SEM ferramentas de escrita)
        if adapter is not None:
            try:
                tier3_action = await self._resolve_tier3_llm(raw, stage, adapter)
                if tier3_action is not None:
                    return tier3_action
            except Exception as exc:  # noqa: BLE001
                logger.warning("Falha no classificador Tier 3 LLM: %s", exc)

        # Se não foi possível classificar deterministicamente, retorna como conversa informativa
        return TuringAction(
            tier=3,
            intention=local_result.intention,
            confidence=local_result.confidence,
            command=None,
            action_type=None,
            action_args={},
            slots=local_result.slots,
            needs_llm=True,
            raw_input=raw,
        )

    async def _resolve_tier3_llm(
        self,
        raw_text: str,
        stage: str | None,
        adapter: Any,
    ) -> TuringAction | None:
        """Executa uma classificação semântica enxuta via LLM sem ferramentas de escrita."""
        prompt = (
            "Você é o classificador de intenções do framework Bombe Code.\n"
            f"Etapa atual da ONDA: {stage or 'DISCUSS'}.\n"
            "Classifique a intenção do desenvolvedor estritamente entre uma das seguintes opções:\n"
            "- start_discuss (nova demanda, briefing, proposta de produto, requisitos de software)\n"
            "- start_plan (planejamento de arquitetura, modelagem de dados, decomposição de stories)\n"
            "- start_cycle (implementação de código, execução de story TDD, escrever testes)\n"
            "- review_cycle (code review, auditoria técnica de conformidade)\n"
            "- validate_wave (validação final da onda, testes e2e, homologação)\n"
            "- wave_status (pergunta sobre status, progresso ou métricas da onda)\n"
            "- toggle_mode (troca de modo de autonomia auto/semi-auto/manual ou tdd/vibe)\n"
            "- unknown (dúvida conceitual ou pergunta fora das ações da onda)\n\n"
            f'Texto do usuário:\n"""{raw_text[:1500]}"""\n\n'
            "Responda EXCLUSIVAMENTE em formato JSON puro, sem blocos markdown adicionais:\n"
            '{"intention": "<opcao>", "confidence": 0.0_a_1.0, "topic": "<resumo_se_houver>"}'
        )

        response_text = ""
        if hasattr(adapter, "complete"):
            res = await adapter.complete([{"role": "user", "content": prompt}])
            response_text = res if isinstance(res, str) else getattr(res, "text", str(res))
        elif hasattr(adapter, "chat"):
            res = adapter.chat(prompt)
            response_text = res if isinstance(res, str) else str(res)

        if not response_text:
            return None

        # Extrai JSON
        m = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not m:
            return None

        data = json.loads(m.group(0))
        intent = data.get("intention", "unknown")
        confidence = float(data.get("confidence", 0.5))
        topic = data.get("topic", "")

        if intent in self.INTENT_TO_COMMAND or intent in (
            "start_discuss",
            "start_cycle",
            "toggle_mode",
        ):
            mock_res = TuringIntentResult(
                intention=intent,
                confidence=confidence,
                slots={"topic": topic} if topic else {},
                needs_llm=False,
                raw_text=raw_text,
            )
            cmd, action_type, action_args = self._map_to_action(mock_res, raw_text, stage=stage)
            return TuringAction(
                tier=3,
                intention=intent,
                confidence=confidence,
                command=cmd,
                action_type=action_type,
                action_args=action_args,
                slots=mock_res.slots,
                needs_llm=False,
                raw_input=raw_text,
            )

        return None
