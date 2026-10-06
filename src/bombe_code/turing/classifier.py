"""Classificador determinístico e contextual de intenções do Turing (Cérebro Local Rápido / 0 Tokens).

Suporta frases rotineiras, comandos curtos e textos extensos (briefings, demandas de produto em markdown),
com vocabulário amplo, token scoring ponderado e extração semântica de slots.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass(frozen=True)
class TuringIntentResult:
    intention: str
    confidence: float
    slots: dict[str, str] = field(default_factory=dict)
    needs_llm: bool = False
    raw_text: str = ""


class TuringIntentClassifier:
    """Classificador local de intenções em Python puro com vocabulário enterprise.

    Opera em 3 níveis determinísticos:
    1. Reconhecimento de Briefings / Demandas Extensas em Markdown.
    2. Correspondência exata por frases (`phrases`) com score máximo.
    3. Pontuação ponderada por tokens fortes (`strong` = 10 pts) e fracos (`weak` = 2 pts).
    """

    CATALOG: ClassVar[dict[str, dict[str, Any]]] = {
        "wave_status": {
            "phrases": [
                "status da onda",
                "como esta a onda",
                "como ta a onda",
                "progresso da onda",
                "onda atual",
                "wave status",
                "status do projeto",
                "como esta o projeto",
                "como ta o projeto",
                "o que esta rodando",
                "o que ta rodando",
                "missoes ativas",
                "status da missao",
                "resumo da onda",
            ],
            "strong": ["onda", "status", "progresso", "rodando", "missao", "missoes"],
            "weak": ["como", "esta", "ta", "atual", "projeto", "ativas"],
        },
        "start_discuss": {
            "phrases": [
                "iniciar fase discuss",
                "iniciar discuss",
                "comecar discuss",
                "fase de discussao",
                "discuss do projeto",
                "novo projeto",
                "criar projeto",
                "iniciar projeto",
                "cria um projeto",
                "criar um novo projeto",
                "novo sistema",
                "cria projeto",
                "briefing do projeto",
                "briefing do mvp",
                "proposta de produto",
                "quero criar um app",
                "quero criar um sistema",
                "quero construir um",
                "quero desenvolver um",
                "nova funcionalidade",
                "criar funcionalidade",
                "implementar funcionalidade",
                "discussao de escopo",
                "definir prd",
                "gerar prd",
            ],
            "strong": [
                "discuss",
                "briefing",
                "prd",
                "projeto",
                "produto",
                "aplicativo",
                "sistema",
                "app",
                "mvp",
                "funcionalidade",
                "escopo",
                "ideacao",
            ],
            "weak": [
                "iniciar",
                "comecar",
                "novo",
                "nova",
                "criar",
                "construir",
                "desenvolver",
                "visao",
                "requisitos",
                "fase",
                "quero",
                "preciso",
            ],
        },
        "start_plan": {
            "phrases": [
                "planejar a arquitetura",
                "vamos planejar",
                "iniciar fase plan",
                "iniciar plan",
                "fase de planejamento",
                "planejar backlog",
                "desenhar arquitetura",
                "modelar banco",
                "mapear jornadas",
                "especificar telas",
                "gerar stories",
                "quebrar em stories",
                "quebrar em tarefas",
                "planejar sprint",
                "plano da onda",
            ],
            "strong": [
                "plan",
                "planejamento",
                "planejar",
                "arquitetura",
                "backlog",
                "jornadas",
                "stories",
                "tarefas",
            ],
            "weak": ["vamos", "fase", "iniciar", "banco", "telas", "modelo", "desenhar", "quebrar"],
        },
        "start_cycle": {
            "phrases": [
                "executar ciclo",
                "iniciar ciclo",
                "ciclo da story",
                "rodar ciclo",
                "proximo ciclo",
                "proxima story",
                "ciclo tdd",
                "roda o tdd",
                "executa tdd",
                "escrever teste",
                "roda os testes",
                "rodar testes",
                "executar story",
                "fazer a story",
                "implementar story",
                "desenvolver story",
            ],
            "strong": [
                "ciclo",
                "story",
                "tdd",
                "testes",
                "teste",
                "implementar",
                "executar",
                "executa",
            ],
            "weak": ["rodar", "iniciar", "proximo", "proxima", "fazer", "desenvolver", "codigo"],
        },
        "review_cycle": {
            "phrases": [
                "code review",
                "solicitar code review",
                "review do tech lead",
                "revisar story",
                "revisar codigo",
                "revisao tecnica",
                "auditar codigo",
                "auditar conformidade",
                "inspecionar entrega",
                "faz o review",
                "fazer o review",
            ],
            "strong": ["review", "revisar", "revisao", "auditar", "inspecionar", "conformidade"],
            "weak": ["codigo", "tech", "lead", "story", "entrega", "solicitar", "faz"],
        },
        "validate_wave": {
            "phrases": [
                "validar entrega",
                "auditar contrato",
                "fase validate",
                "iniciar validate",
                "homologar onda",
                "validar onda",
                "roda a validacao",
                "rodar a validacao",
                "valida o projeto",
                "validar o projeto",
                "valida tudo",
                "testes e2e",
                "testes de integracao",
                "selo da onda",
            ],
            "strong": ["validate", "validar", "validacao", "homologar", "contrato", "selo", "e2e"],
            "weak": ["entrega", "onda", "fase", "projeto", "tudo", "integracao", "testes"],
        },
        "workflow_resume": {
            "phrases": [
                "continue de onde parou",
                "continuar de onde parou",
                "continua de onde parou",
                "continua da onde parou",
                "retomar de onde parou",
                "retome de onde parou",
                "segue de onde parou",
                "retomar o fluxo",
                "continuar o workflow",
                "continua o trabalho",
                "retomar o trabalho",
                "retoma o fluxo",
                "segue dai",
                "retomar execucao",
                "deu erro e parou",
                "parou no meio",
            ],
            "strong": ["retomar", "retoma", "retome", "resume"],
            "weak": [
                "continua",
                "continue",
                "continuar",
                "parou",
                "fluxo",
                "trabalho",
                "workflow",
                "segue",
            ],
        },
        "approve_execution": {
            "phrases": [
                "pode executar",
                "pode executar sim",
                "pronto pode executar",
                "pode comecar",
                "pode comecar a execucao",
                "aprovado execute",
                "aprovado, execute",
                "liberado execute",
                "executa o plano",
                "execute o plano",
                "comeca a execucao",
                "esta aprovado",
                "esta liberado",
                "plano aprovado",
            ],
            "strong": ["executar", "executa", "execucao", "aprovado", "liberado"],
            "weak": ["pode", "pronto", "comeca", "comecar", "plano", "sim", "esta"],
        },
        "toggle_mode": {
            "phrases": [
                "mudar para modo",
                "alterar modo",
                "troca o modo",
                "muda pro modo",
                "modo auto",
                "modo manual",
                "modo semi-auto",
                "modo tdd",
                "modo vibe",
                "coloca no automatico",
                "modo automatico",
                "trabalhe sozinho",
            ],
            "strong": ["modo", "autonomia", "automatico", "manual", "vibe", "tdd", "sozinho"],
            "weak": ["mudar", "alterar", "troca", "muda", "coloca"],
        },
    }

    # Marcadores de seções estruturais de Briefing de Produto
    BRIEFING_MARKERS: ClassVar[list[str]] = [
        "visao do produto",
        "visao geral",
        "conceito central",
        "regra de ouro",
        "regras de negocio",
        "escopo do mvp",
        "escopo da entrega",
        "objetivos de validacao",
        "funcionalidades (in)",
        "funcionalidades",
        "requisitos",
        "personas",
        "criterios rice",
        "publico-alvo",
        "briefing",
        "modelo conceitual",
    ]

    def _normalize(self, text: str) -> str:
        """Remove diacríticos, formatação de pontuação e normaliza espaços."""
        if not text:
            return ""
        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        # Remove caracteres de markdown comuns para análise semântica limpa
        text = re.sub(r"[#*_>`~|\[\]\(\)\{\}\-]", " ", text)
        return " ".join(text.split())

    def _strip_markdown_headers(self, text: str) -> str:
        """Remove cabeçalhos markdown e extrai título principal se houver."""
        lines = text.strip().splitlines()
        for line in lines:
            cleaned = line.strip()
            if cleaned.startswith("#"):
                header_text = re.sub(r"^#+\s*", "", cleaned).strip()
                # Remove prefixos comuns como 'BRIEFING —', 'PRD —', 'PROPOSTA:'
                clean_title = re.sub(
                    r"^(?:briefing|prd|proposta|projeto)\s*[\-—:]\s*",
                    "",
                    header_text,
                    flags=re.IGNORECASE,
                ).strip()
                if clean_title:
                    return clean_title
        return ""

    def _is_extensive_briefing(self, raw_text: str, norm_text: str) -> tuple[bool, str]:
        """Detecta deterministicamente se o texto é um Briefing Extenso ou Demanda de Produto."""
        raw = raw_text.strip()
        if len(raw) < 80:
            return False, ""

        # 1. Checa presença de marcadores estruturais de produto
        matched_markers = [m for m in self.BRIEFING_MARKERS if m in norm_text]
        if len(matched_markers) >= 2 or (len(matched_markers) >= 1 and len(raw) > 200):
            extracted_title = self._strip_markdown_headers(raw)
            if not extracted_title:
                # Tenta primeira linha não-vazia ou resumo
                first_line = raw.splitlines()[0].strip()
                extracted_title = first_line[:120]
            return True, extracted_title

        # 2. Padrões explícitos como 'Quero criar um app...', '# Briefing'
        if re.search(
            r"^(#+\s*)?(?:briefing|prd|especificacao|visao do produto)\b", raw, re.IGNORECASE
        ):
            title = self._strip_markdown_headers(raw) or raw[:120]
            return True, title

        # 3. Frases ricas com 'Quero criar / Desenvolver' acima de 120 caracteres
        if len(raw) >= 120 and re.search(
            r"\b(quero|preciso|desejo|gostaria de)\s+(?:criar|desenvolver|construir|fazer)\s+(?:um|uma)\s+(?:app|aplicativo|sistema|plataforma|software|saas|pwa)\b",
            norm_text,
        ):
            title = self._strip_markdown_headers(raw) or raw[:120]
            return True, title

        return False, ""

    def _extract_slots(self, intention: str, raw_text: str) -> dict[str, str]:
        """Extrai slots semânticos a partir do texto bruto."""
        slots: dict[str, str] = {}
        raw = raw_text.strip()

        # Extrai Story ID (ex: ST-001, ST-123)
        story_match = re.search(r"\b(ST-\d+)\b", raw, re.IGNORECASE)
        if story_match:
            slots["story_id"] = story_match.group(1).upper()

        # Extrai modo (auto, semi-auto, manual, tdd, vibe)
        mode_match = re.search(r"\b(auto|semi-auto|manual|tdd|vibe)\b", raw, re.IGNORECASE)
        if mode_match:
            slots["mode"] = mode_match.group(1).lower()

        # Extrai persona/agente (ex: @meira, @grace, @linus)
        agent_match = re.search(r"(@[a-zA-Z0-9_]+)", raw)
        if agent_match:
            slots["persona"] = agent_match.group(1).lower()

        if intention == "start_discuss":
            # Tenta título ou primeiras palavras representativas
            title = self._strip_markdown_headers(raw)
            if title:
                slots["topic"] = title
            else:
                m = re.search(
                    r"(?:criar|desenvolver|construir|projeto|app|aplicativo|sistema|plataforma)\s+(?:chamado\s+|de\s+)?([a-zA-Z0-9À-ÿ_\-\s]{3,80})",
                    raw,
                    re.IGNORECASE,
                )
                if m:
                    slots["topic"] = m.group(1).strip()
                else:
                    slots["topic"] = raw[:120].strip()

        return slots

    def classify(
        self,
        text: str,
        stage: str | None = None,
        is_greenfield: bool = False,
    ) -> TuringIntentResult:
        """Classifica a intenção do texto em modo determinístico/contextual.

        Parâmetros:
        - `text`: texto bruto enviado pelo usuário.
        - `stage`: etapa atual da ONDA (ex: DISCUSS, PLAN, EXECUTE, VALIDATE).
        - `is_greenfield`: indica se o projeto é novo sem artefatos prévios.
        """
        if not text or not str(text).strip():
            return TuringIntentResult(
                intention="unknown",
                confidence=0.0,
                slots={},
                needs_llm=True,
                raw_text=text or "",
            )

        raw = text.strip()
        norm = self._normalize(raw)
        norm_tokens = set(norm.split())

        # 1. DETECÇÃO ESTRUTURAL DE BRIEFING EXTENSO (Prioridade 1 para textos longos)
        is_briefing, topic_extracted = self._is_extensive_briefing(raw, norm)
        if is_briefing:
            slots = self._extract_slots("start_discuss", raw)
            if topic_extracted:
                slots["topic"] = topic_extracted
            return TuringIntentResult(
                intention="start_discuss",
                confidence=0.98,
                slots=slots,
                needs_llm=False,
                raw_text=raw,
            )

        # 2. CONTEXTO DE ETAPA: Se estamos em DISCUSS ou DISCOVERY em projeto greenfield
        # e o usuário enviou uma descrição substantiva (> 40 caracteres)
        norm_stage = (stage or "").strip().upper()
        if (norm_stage in ("DISCUSS", "DISCOVERY") or is_greenfield) and len(raw) >= 40:
            product_words = {
                "app",
                "aplicativo",
                "sistema",
                "plataforma",
                "mvp",
                "produto",
                "projeto",
                "funcionalidade",
            }
            if norm_tokens.intersection(product_words):
                slots = self._extract_slots("start_discuss", raw)
                return TuringIntentResult(
                    intention="start_discuss",
                    confidence=0.92,
                    slots=slots,
                    needs_llm=False,
                    raw_text=raw,
                )

        # 3. PONTUAÇÃO PONDERADA VIA CATÁLOGO (Phrases, Strong, Weak)
        best_intent = "unknown"
        highest_score = 0.0

        for intent, spec in self.CATALOG.items():
            phrases = spec.get("phrases", [])
            strong = spec.get("strong", [])
            weak = spec.get("weak", [])

            # A. Match exato por frase normalizada (score 100)
            matched_phrase = False
            for phrase in phrases:
                norm_phrase = self._normalize(phrase)
                if norm_phrase and norm_phrase in norm:
                    coverage = len(norm_phrase) / max(len(norm), 1)
                    # Frases curtas em textos muito longos têm cobertura proporcional
                    score = min(0.98, 0.85 + coverage * 0.13)
                    if score > highest_score:
                        highest_score = score
                        best_intent = intent
                        matched_phrase = True
                    break

            if matched_phrase:
                continue

            # B. Match por tokens fortes e fracos
            pts = 0
            for st in strong:
                norm_st = self._normalize(st)
                if norm_st in norm_tokens:
                    pts += 10
            for wk in weak:
                norm_wk = self._normalize(wk)
                if norm_wk in norm_tokens:
                    pts += 2

            # Threshold mínimo: pelo menos 10 pontos (1 strong token ou 5 weak tokens)
            if pts >= 10:
                calc_score = min(0.92, 0.60 + (pts / 50.0) * 0.32)
                if calc_score > highest_score:
                    highest_score = calc_score
                    best_intent = intent

        # 4. DECISÃO FINAL
        if highest_score >= 0.70 and best_intent != "unknown":
            slots = self._extract_slots(best_intent, raw)
            return TuringIntentResult(
                intention=best_intent,
                confidence=highest_score,
                slots=slots,
                needs_llm=False,
                raw_text=raw,
            )

        # Se não casou com confiança suficiente, sinaliza needs_llm para Tier 3
        return TuringIntentResult(
            intention="unknown",
            confidence=highest_score,
            slots={},
            needs_llm=True,
            raw_text=raw,
        )
