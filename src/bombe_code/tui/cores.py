"""Registro de Cores de Identidade dos Agentes (TUI).

Cada agente tem uma COR única que o identifica na tela — o nome dele aparece
sempre nela. Funções diferentes do maestro Turing ganham cores próprias
(determinístico, probabilístico, maestro), para o usuário avançado saber
quem está agindo sem jargão de arquitetura exposto.

Jargão interno ("Turing determinístico/probabilístico") NÃO aparece em texto
ao usuário — a identificação é pela cor + símbolo.
"""

from __future__ import annotations

# ─── Funções do Maestro Turing (cada papel, uma cor) ────────────────────────
CORES_TURING = {
    "maestro": "#cba6f7",  # orquestração, encadeamento, pausas (Mauve)
    "deterministico": "#94e2d5",  # gates, análise de veto, autocura (Teal)
    "probabilistico": "#f5c2e7",  # classificador LLM sob demanda (Pink)
}

# ─── Cor única por agente (24 especialistas) ────────────────────────────────
CORES_AGENTES = {
    # Upstream
    "@meira": "#89dceb",  # Sky
    "@grace": "#f9e2af",  # Yellow
    "@alan": "#a6e3a1",  # Green
    "@norman": "#fab387",  # Peach
    "@ieru": "#89b4fa",  # Blue
    "@codd": "#74c7ec",  # Sapphire
    "@claudia": "#94e2d5",  # Teal
    "@barreto": "#f38ba8",  # Red
    "@caroli": "#b4befe",  # Lavender
    "@nelson": "#ee99b0",  # Rosewater-ish
    # Downstream — construção
    "@valim": "#a6d189",  # Soft green (BEAM)
    "@barbara": "#8caaee",  # Nordic blue
    "@scott": "#81c8be",  # Nordic teal (.NET)
    "@ryan": "#e5c890",  # Node yellow
    "@james": "#ca9ee6",  # Java purple
    "@ada": "#f2d5cf",  # Frontend rose
    "@diego": "#e78284",  # Offsec red
    "@aniche": "#e0af68",  # QA amber
    "@unclebob": "#c6a0f6",  # Guardian violet
    "@demi": "#99d1db",  # SRE cyan
    # Downstream — validação
    "@edith": "#ef9f76",  # Homologação orange
    "@nina": "#f4b8e4",  # Governança pink
    # Contra-auditoria forense
    "@hoare": "#d3869b",  # Auditor mauve-pink (prova e cross-exame)
    # Maestro (persona LLM de suporte à orquestração)
    "@turing": CORES_TURING["maestro"],
}

# Símbolos por função do Turing (identificação extra sem texto)
SIMBOLOS_TURING = {
    "maestro": "◆",
    "deterministico": "▣",
    "probabilistico": "◈",
}


def cor_agente(handle: str) -> str:
    """Cor de identidade do agente (desconhecidos recebem o texto padrão)."""
    return CORES_AGENTES.get((handle or "").strip().lower(), CORES_TURING["maestro"])


def markup_agente(handle: str) -> str:
    """Retorna o handle envolvido na cor de identidade dele (markup Textual)."""
    return f"[{cor_agente(handle)}]{handle}[/]"


def markup_turing(funcao: str) -> str:
    """Tag colorida de uma função do maestro (ex.: '▣ TURING' em teal)."""
    cor = CORES_TURING.get(funcao, CORES_TURING["maestro"])
    simbolo = SIMBOLOS_TURING.get(funcao, "◆")
    return f"[{cor}]{simbolo} TURING[/]"


def colorizar_handles(texto: str) -> str:
    """Substitui @handles conhecidos no texto pelas versões coloridas.

    Identidade por cor na tela: o usuário avançado reconhece quem age pela
    cor; o usuário normal apenas lê a mensagem.
    """
    resultado = texto or ""
    for handle, cor in CORES_AGENTES.items():
        if handle in resultado:
            resultado = resultado.replace(handle, f"[{cor}]{handle}[/]")
    return resultado
