"""Classificador determinístico de intenções do Turing (Cérebro Local Rápido / 0 Tokens)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class TuringIntentResult:
    intention: str
    confidence: float
    slots: dict[str, str] = field(default_factory=dict)
    needs_llm: bool = False
    raw_text: str = ""


class TuringIntentClassifier:
    """Classificador local de intenções em Python puro.

    Identifica comandos rotineiros de ciclo da ONDA sem fazer requisições a LLM.
    """

    PATTERNS: ClassVar[dict[str, list[str]]] = {
        "wave_status": [
            r"status da onda",
            r"como est[aá] a onda",
            r"como t[aá] a onda",
            r"progresso da onda",
            r"onda atual",
            r"wave status",
        ],
        "start_discuss": [
            r"iniciar fase discuss",
            r"iniciar discuss",
            r"come[cç]ar discuss",
            r"fase de discuss[aã]o",
            r"discuss do projeto",
        ],
        "start_plan": [
            r"planejar a arquitetura",
            r"vamos planejar",
            r"iniciar fase plan",
            r"iniciar plan",
            r"fase de planejamento",
            r"planejar backlog",
        ],
        "start_cycle": [
            r"executar ciclo",
            r"iniciar ciclo",
            r"ciclo da story",
            r"rodar ciclo",
            r"pr[oó]ximo ciclo",
            r"pr[oó]xima story",
        ],
        "review_cycle": [
            r"code review",
            r"solicitar code review",
            r"review do tech lead",
            r"revisar story",
            r"revisar c[oó]digo",
            r"revis[aã]o t[eé]cnica",
        ],
        "validate_wave": [
            r"validar entrega",
            r"auditar contrato",
            r"fase validate",
            r"iniciar validate",
            r"homologar onda",
            r"validar onda",
        ],
        "toggle_mode": [
            r"mudar para modo",
            r"alterar modo",
            r"modo auto",
            r"modo semi[- ]auto",
            r"modo manual",
            r"modo tdd",
            r"modo vibe",
        ],
    }

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    def _extract_slots(self, text: str, intention: str) -> dict[str, str]:
        slots: dict[str, str] = {}
        # Extrai Story ID (ex: ST-001, ST-123)
        story_match = re.search(r"\b(ST-\d+)\b", text, re.IGNORECASE)
        if story_match:
            slots["story_id"] = story_match.group(1).upper()

        # Extrai modo (auto, semi-auto, manual, tdd, vibe)
        mode_match = re.search(r"\b(auto|semi-auto|manual|tdd|vibe)\b", text, re.IGNORECASE)
        if mode_match:
            slots["mode"] = mode_match.group(1).lower()

        return slots

    def classify(self, text: str) -> TuringIntentResult:
        normalized = self._normalize(text)

        for intention, pattern_list in self.PATTERNS.items():
            for pat in pattern_list:
                norm_pat = self._normalize(pat)
                if re.search(r"\b" + norm_pat + r"\b", normalized):
                    slots = self._extract_slots(text, intention)
                    return TuringIntentResult(
                        intention=intention,
                        confidence=0.95,
                        slots=slots,
                        needs_llm=False,
                        raw_text=text,
                    )

        # Se não casou com padrões rotineiros, delega à LLM
        return TuringIntentResult(
            intention="unknown",
            confidence=0.1,
            slots={},
            needs_llm=True,
            raw_text=text,
        )
