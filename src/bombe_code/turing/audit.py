"""Contra-Auditoria Forense (C.A.R. Hoare) — "Pedido vs. Entregue" com o CÓDIGO
como fonte da verdade.

A metodologia é INTENCIONALMENTE diferente do validate original:
- Postura adversarial: assume que o homologador anterior pode ter sido preguiçoso.
- Cross-examinação: cada alegação do relatório anterior vira exigência de evidência.
- Checagens determinísticas de custo ZERO de tokens (grep de fraude, mapa CA×teste,
  execução REAL da suíte de testes do projeto auditado).
- Prova por amostragem profunda nas stories de maior risco.

O gasto de LLM é limitado a UMA chamada adversarial do @hoare.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Padrões de código "fingido" em produção (fraude de implementação)
FRAUDE_PRODUCAO: tuple[tuple[str, str], ...] = (
    (r"NotImplementedError", "NotImplementedError em código de produção"),
    (r"^\s*(#|//|/\*)\s*TODO(?!:.*teste)", "TODO não resolvido em código de produção"),
    (r"^\s*(#|//)\s*FIXME", "FIXME aberto em código de produção"),
    (r"\bunittest\.mock\b|\bMagicMock\b|\bpatch\(", "mock de teste vazando em código de produção"),
    (r"return\s+(True|None)\s*#\s*mock", "retorno simulado marcado como mock"),
)

# Diretórios/pastas que NÃO são código de produção
EXCLUSOES_AUDIT = (
    ".git",
    "docs",
    ".bombe",
    ".bombe-code",
    ".venv",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
)


@dataclass
class EvidenciaDeterministica:
    """Resultados das checagens de custo zero — insumo do @hoare."""

    arquivos_producao: list[str] = field(default_factory=list)
    testes_encontrados: list[str] = field(default_factory=list)
    fraudes_potenciais: list[str] = field(default_factory=list)
    mapa_cas: dict[str, dict[str, Any]] = field(default_factory=dict)  # story -> {cas, bdd}
    suite_resultado: str = "NÃO EXECUTADA"
    suite_detalhes: str = ""
    aleacoes_relatorio_anterior: list[str] = field(default_factory=list)


def _arquivos_codigo(project_dir: Path) -> list[Path]:
    if not project_dir.exists():
        return []
    candidatos = [
        p
        for p in project_dir.rglob("*")
        if p.is_file()
        and not any(part in EXCLUSOES_AUDIT for part in p.parts)
        and p.suffix
        in (
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".vue",
            ".go",
            ".java",
            ".cs",
            ".sql",
            ".rb",
            ".php",
        )
    ]
    return sorted(candidatos)


def coletar_evidencias(
    project_dir: str | Path, wave_id: str, report_anterior: str
) -> EvidenciaDeterministica:
    """Coleta TODAS as provas determinísticas antes de gastar 1 token."""
    base = Path(project_dir)
    ev = EvidenciaDeterministica()

    # 1. Inventário de produção × testes
    for p in _arquivos_codigo(base):
        rel = p.relative_to(base).as_posix()
        if "/tests/" in f"/{rel}" or rel.startswith("tests/"):
            ev.testes_encontrados.append(rel)
        else:
            ev.arquivos_producao.append(rel)

    # 2. Fraude potencial em produção
    for rel in ev.arquivos_producao:
        caminho = base / rel
        try:
            conteudo = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, motivo in FRAUDE_PRODUCAO:
            if re.search(pattern, conteudo, re.MULTILINE):
                linha = next(
                    (
                        str(i + 1)
                        for i, l in enumerate(conteudo.splitlines())
                        if re.search(pattern, l, re.MULTILINE)
                    ),
                    "?",
                )
                ev.fraudes_potenciais.append(f"{motivo} → {rel}:{linha}")

    # 3. Mapa de CAs declarados por story (contrato do escopo)
    stories_dir = base / "docs" / "stories"
    for story_file in sorted(stories_dir.glob("*.md")) if stories_dir.is_dir() else []:
        try:
            conteudo = story_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cas = sorted(set(re.findall(r"\bCA-\d+\b", conteudo)))
        bdd = "Dado" in conteudo or "Quando" in conteudo
        ev.mapa_cas[story_file.stem] = {"cas": cas, "bdd": bdd}  # type: ignore[assignment]

    return ev


def executar_suite_testes(project_dir: str | Path, timeout: int = 900) -> tuple[str, str]:
    """Executa a suíte REAL do projeto auditado (custo: tempo de CPU, zero tokens).

    Suporta projetos Python (uv run pytest) e Node (npm test). Retorna
    (resultado_resumido, detalhes_para_o_auditor).
    """
    base = Path(project_dir)

    if (base / "pyproject.toml").exists() or (base / "pytest.ini").exists():
        try:
            proc = subprocess.run(
                ["uv", "run", "pytest", "-q", "--tb=line"],
                cwd=str(base),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            cauda = "\n".join((proc.stdout or "").strip().splitlines()[-12:])
            resumo = "PASSOU" if proc.returncode == 0 else f"FALHOU (exit {proc.returncode})"
            return resumo, cauda or (proc.stderr or "")[-800:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "INCONCLUSIVA", f"suíte não executável: {exc}"

    if (base / "package.json").exists():
        try:
            proc = subprocess.run(
                ["npm", "test", "--", "--run"],
                cwd=str(base),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            cauda = "\n".join((proc.stdout or "").strip().splitlines()[-12:])
            resumo = "PASSOU" if proc.returncode == 0 else f"FALHOU (exit {proc.returncode})"
            return resumo, cauda or (proc.stderr or "")[-800:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "INCONCLUSIVA", f"suíte não executável: {exc}"

    return "AUSENTE", "nenhum runner de testes encontrado no projeto"


def extrair_aleacoes_relatorio(report_anterior: str) -> list[str]:
    """Extrai alegações verificáveis do relatório de validação anterior
    (frases com 'passando', 'coberto', 'sem mock', 'conforme', 'real')."""
    alegacoes: list[str] = []
    gatilhos = re.compile(
        r"(testes?\s+(passando|executad\w+|aprovad\w+)|CA-\d+[^.\n]{0,60}(coberto|implementad\w+)|sem\s+mocks?\w*|cobre[^.\n]{0,60}|conforme[^.\n]{0,40})",
        re.IGNORECASE,
    )
    for linha in (report_anterior or "").splitlines():
        limpa = linha.strip().lstrip("-*| ")
        if gatilhos.search(limpa) and len(limpa) > 12:
            alegacoes.append(limpa[:200])
    return alegacoes[:40]


def extrair_furos(laudo: str) -> list[str]:
    """Extrai furos do laudo do @hoare (linhas 'FURO: ...')."""
    furos: list[str] = []
    for linha in (laudo or "").splitlines():
        limpa = linha.strip().lstrip("*- ")
        if limpa.upper().startswith("FURO"):
            furos.append(limpa.split(":", 1)[1].strip() if ":" in limpa else limpa)
    return furos


def veredito_auditoria(laudo: str, furos: list[str]) -> tuple[bool, str]:
    """Veredito estrutural do laudo: LIMPA exige zero furos + declaração canônica;
    qualquer FURO veta. Prosa não decide."""
    if furos:
        return False, f"{len(furos)} furo(s) encontrado(s) pela contra-auditoria"
    if re.search(r"auditoria:\s*limpa", laudo, re.IGNORECASE):
        return True, "Contra-auditoria limpa — pedido × entregue verificado no código"
    if re.search(r"limpa", laudo, re.IGNORECASE):
        return True, "Contra-auditoria limpa"
    return False, "laudo sem veredito canônico ('AUDITORIA: LIMPA') e sem furos estruturados"
