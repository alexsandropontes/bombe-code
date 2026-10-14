"""GOVERNANÇA DE AMBIENTE (SRP — uma responsabilidade: decidir e operar
impedimentos de ferramenta/dependência).

Regras do projeto incarnadas aqui:
- Instalar dependência do projeto é CAPACIDADE DA PLATAFORMA — nunca escalação
  humana (o usuário pode ser um PM que não instala nada). O gate é
  DETERMINÍSTICO: decide pela FORMA do comando (local, pacote único, sem -g,
  sem sudo, sem encadeamento), nunca por juízo de LLM.
- Bloqueio por falta de ferramenta/dependência → o Turing abre task
  PRIORITÁRIA (ordem 0 = PRIMEIRA da fila) roteada pelo PAPEL:
    * ferramenta de infra/ambiente (PostgreSQL, Docker, pandoc…) → @guto
    * biblioteca de aplicação (pacote npm/pip do código) → @unclebob
- A origem ganha dep: na DOR — só re-queima quando a instalação está DEV DONE.
"""

from __future__ import annotations

import re
from typing import Any

from bombe_code.agents.runner import AgentExecutionResult
from bombe_code.turing.progress import BUS

# Assinaturas DETERMINÍSTICAS de bloqueio por falta de ferramenta/dependência
# (nunca cota/provedor — isso é pausa de cota, não instalação).
SINAIS_DE_FALTA_DE_FERRAMENTA = (
    "missing dependency",
    "cannot find dependency",
    "no matching distribution",
    "modulenotfounderror",
    "no module named",
    "cannot find module",
    "unable to locate package",
    "command not found",
    "is not recognized",
    "não está instalado",
    "nao esta instalado",
    "dependência ausente",
    "dependencia ausente",
    "require um executor dom",
    "requires jsdom",
    "requires a dom",
    "document is not defined",
)

# Ferramentas de INFRA/ambiente → DevOps (@guto); o resto (biblioteca de
# aplicação) → Tech Lead (@unclebob).
PALAVRAS_INFRA = (
    "postgres",
    "postgresql",
    "psql",
    "mysql",
    "mariadb",
    "mongo",
    "redis",
    "rabbitmq",
    "kafka",
    "docker",
    "podman",
    "nginx",
    "sqlite3-cli",
    "pandoc",
    "node ",
    "python ",
    "runtime",
)

_PADRAO_PACOTE = re.compile(
    r"^(@[a-zA-Z0-9][a-zA-Z0-9._-]*/)?[a-zA-Z0-9][a-zA-Z0-9._/-]*"
    r"(@[a-zA-Z0-9][a-zA-Z0-9.<>=~^-]*|==[a-zA-Z0-9][a-zA-Z0-9.<>=~^-]*)?$"
)


_EXECUCAO_DE_INSTALACAO = (
    "npm install", "npm add", "pnpm install", "pnpm add",
    "yarn install", "yarn add", "uv add", "pip install",
)


def verificar_instalacao(registro: list[str] | None) -> bool:
    """DOD REAL da card de INSTALAÇÃO — VALIDAÇÃO, não instalação: o REGISTRO
    PLATFORM-SIDE precisa conter comando auditado EXECUTADO pela ferramenta
    com exit 0 (o teste de import/require da biblioteca). Zero suposição:
    registro vazio = nada rodou de verdade = FALHA — não importa o que o
    agente tenha ESCRITO. Cobre: instalou agora · já estava instalado
    (só o teste roda) · reinstalou após instalar errado."""
    return any((cmd or "").strip() for cmd in (registro or []))


def auditar_instalacao(comando: str) -> str | None:
    """Gate DETERMINÍSTICO de instalação (função pura — testável isolada).

    Retorna a ferramenta se o comando é instalação AUDITADA (forma permitida);
    None se não é instalação; string de erro (prefixo 'Erro:') se é instalação
    em forma PROIBIDA."""
    c = comando.strip()
    if not re.match(r"^(npm|pnpm|yarn)\s+(install|add)\b|^uv\s+(add|pip\s+install)\b", c):
        return None
    if any(s in c for s in ("|", ";", "&&", "`", "$(", ">", "<")):
        return "Erro: instalação auditada aceita UM comando simples, sem encadeamento."
    tokens = c.split()
    if any(t in ("-g", "--global", "sudo") for t in tokens):
        return "Erro: instalação GLOBAL proibida no gate — só dependência do projeto."
    # `npm install`/`uv add` SEM pacote = instalar do lockfile existente — legítimo.
    pacotes = [
        t
        for t in tokens[2:]
        if not t.startswith("-") and t not in ("pip", "install", "add") and t != "uv"
    ]
    for pacote in pacotes:
        if not _PADRAO_PACOTE.match(pacote):
            return f"Erro: nome de pacote fora do padrão auditado: {pacote[:40]}"
    return "npm" if c.startswith(("npm", "pnpm", "yarn")) else "uv"


def evidencia_de(r: Any) -> str:
    """Extrai a evidência textual de um resultado de agente (fonte única do
    texto usado para classificar bloqueios)."""
    return " ".join(
        str(x)
        for x in (
            getattr(r, "block_reason", None),
            getattr(r, "error", None),
            getattr(r, "output", None),
        )
        if x
    )


def runner_ausente(handle: str) -> AgentExecutionResult:
    """Resultado canônico de runner indisponível (DRY: um só literal)."""
    return AgentExecutionResult(
        agent_handle=handle,
        success=False,
        is_blocked=True,
        block_reason="runner indisponível",
    )


def e_bloqueio_de_instalacao(texto: str | None) -> bool:
    """Detecção DETERMINÍSTICA de bloqueio por falta de ferramenta."""
    if not texto:
        return False
    t = texto.lower()
    if "429" in t or "cota" in t or "rate limit" in t:
        return False
    return any(s in t for s in SINAIS_DE_FALTA_DE_FERRAMENTA)


def roteamento_da_instalacao(evidencia: str) -> str:
    """PAPEL dono da instalação: infra → @guto; biblioteca de app → @unclebob."""
    return "@guto" if any(p in evidencia.lower() for p in PALAVRAS_INFRA) else "@unclebob"


def anunciar_instalacao_prioritaria(
    story_id: str, task_origem: str, task_id: str, roteado_para: str
) -> None:
    BUS.publish(
        "announcement",
        agent="@turing",
        text=(
            f"🧰 IMPEDIMENTO DE AMBIENTE — {story_id} {task_origem} bloqueada por "
            f"falta de ferramenta/dependência. Task prioritária {task_id} aberta "
            f"para {roteado_para} (PRIMEIRA da fila — ordem 0). {task_origem} volta "
            "a queimar quando a instalação estiver DEV DONE. Sem escalação humana."
        ),
    )
