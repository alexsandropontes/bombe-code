"""Guarda determinístico de permissões por etapa da ONDA (DISCUSS, PLAN, EXECUTE, VALIDATE).

Garante que ferramentas e ações da LLM respeitem os limites arquiteturais de cada etapa
do ciclo de vida da ONDA:
- DISCUSS: Elicitação, entendimento de escopo, briefing. Bloqueada escrita em src/ e testes.
- PLAN: Arquitetura, decomposição de stories, jornadas. Bloqueada escrita de código de produção.
- EXECUTE: Implementação fullstack e testes TDD. Totalmente liberado.
- VALIDATE: Auditoria de qualidade, testes E2E e relatórios. Bloqueada adição de novos módulos arbitrários.
"""

from __future__ import annotations

import re
from pathlib import Path

# Caracteres proibidos em caminhos de arquivos e artefatos de tags XML de LLM
INVALID_PATH_CHARS_REGEX = re.compile(r'[<>:"|?*\x00-\x1f\r\n]')


def validate_safe_relative_path(path: str, project_dir: str | None = None) -> tuple[bool, str]:
    """Valida se o caminho é seguro e livre de artefatos de LLM (tags XML, caracteres proibidos).

    Retorna (True, "") se válido, ou (False, mensagem_de_erro) se inválido.
    """
    if not path or not isinstance(path, str) or not path.strip():
        return False, "Caminho do arquivo não pode ser vazio."

    cleaned = path.strip()
    if INVALID_PATH_CHARS_REGEX.search(cleaned):
        return (
            False,
            f"Caminho inválido: '{path}' contém caracteres proibidos ou tags XML malformadas (ex: '<', '>', '?', ':').",
        )

    if cleaned.startswith(("/", "\\")):
        return False, f"Caminho deve ser relativo ao projeto: '{path}'"

    # Previne directory traversal explícito com '..'
    parts = Path(cleaned).parts
    if ".." in parts:
        return False, f"Caminho não pode conter '..': '{path}'"

    return True, ""


STAGE_DISCUSS = "DISCUSS"
STAGE_DISCOVERY = "DISCOVERY"
STAGE_PLAN = "PLAN"
STAGE_INCEPTION = "INCEPTION"
STAGE_REFINEMENT = "REFINEMENT"
STAGE_EXECUTE = "EXECUTE"
STAGE_VALIDATE = "VALIDATE"
STAGE_COMPLETED = "COMPLETED"
STAGE_VIBE = "VIBE"

VALID_STAGES = {
    STAGE_DISCUSS,
    STAGE_DISCOVERY,
    STAGE_PLAN,
    STAGE_INCEPTION,
    STAGE_REFINEMENT,
    STAGE_EXECUTE,
    STAGE_VALIDATE,
    STAGE_COMPLETED,
    STAGE_VIBE,
}


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".vue",
    ".svelte",
}

CODE_DIRS = {"src", "lib", "app", "components", "pages", "pkg", "internal", "api"}
TEST_DIRS = {"test", "tests", "spec", "specs"}


def is_code_path(rel_path: str) -> bool:
    """Verifica se o caminho corresponde a arquivos de código fonte ou testes."""
    path = Path(rel_path)
    parts = set(path.parts)

    # Se está dentro de docs/, não é considerado código de produção
    if "docs" in parts:
        return False

    # Diretórios típicos de código fonte
    if any(p in parts for p in CODE_DIRS):
        return True

    # Diretórios de testes
    if any(p in parts for p in TEST_DIRS):
        return True

    # Extensão de código fora de docs
    return path.suffix.lower() in CODE_EXTENSIONS


def is_production_code_path(rel_path: str) -> bool:
    """Verifica se o caminho é código de produção (excluindo testes e docs)."""
    path = Path(rel_path)
    parts = set(path.parts)
    if "docs" in parts or any(p in parts for p in TEST_DIRS):
        return False
    if any(p in parts for p in CODE_DIRS):
        return True
    return path.suffix.lower() in CODE_EXTENSIONS


def validate_stage_permission(
    stage: str,
    action: str,
    target_path: str,
    project_dir: str = "",
) -> tuple[bool, str | None]:
    """Valida se uma ação sobre um arquivo é permitida na etapa atual da ONDA.

    Retorna: (permitido: bool, motivo_se_bloqueado: str | None)
    """
    normalized_stage = stage.strip().upper() if stage else STAGE_DISCUSS
    if normalized_stage not in VALID_STAGES:
        normalized_stage = STAGE_DISCUSS

    # Modo VIBE: liberdade total para criar, editar, planejar e codificar sem restrições
    if normalized_stage == STAGE_VIBE:
        return True, None

    # Leitura é sempre permitida em qualquer etapa para dar contexto ao modelo
    if action in {"read", "glob", "grep", "search"}:
        return True, None

    # Normalização de path relativo ao workspace do projeto
    try:
        p_target = Path(target_path)
        if project_dir and p_target.is_absolute():
            rel = str(p_target.relative_to(Path(project_dir).resolve()))
        else:
            rel = str(p_target)
    except (ValueError, OSError):
        rel = target_path

    rel = rel.replace("\\", "/").lstrip("./")

    # Validação de caminho seguro contra tags XML e caracteres proibidos
    is_safe, err_msg = validate_safe_relative_path(rel)
    if not is_safe:
        return False, f"⛔ [CAMINHO INVÁLIDO] {err_msg}"

    # 1. ETAPA DISCUSS / DISCOVERY
    if normalized_stage in {STAGE_DISCUSS, STAGE_DISCOVERY}:
        if is_code_path(rel):
            stage_name = normalized_stage
            return (
                False,
                (
                    f"⛔ [BLOQUEIO DE ETAPA: {stage_name}] A alteração do arquivo de código '{rel}' é proibida na etapa {stage_name}. "
                    "Esta etapa é reservada para levantamento de requisitos, discussão de escopo e documentação de briefings em docs/. "
                    "Pressione a tecla TAB na TUI para avançar para as próximas etapas quando o escopo estiver alinhado."
                ),
            )

        # Blindagem canônica: proíbe LLMs de inventar nomes arbitrários para PRD e Viabilidade
        rel_lower = rel.lower()
        if "briefings" in rel_lower or "prd" in rel_lower:
            # Se é um arquivo markdown de PRD ou Viabilidade com nome arbitrário (ex: PRD-foo.md)
            filename = Path(rel).name.lower()
            if filename.startswith("prd") and filename not in ("prd.md", "prd.json"):
                return (
                    False,
                    (
                        f"⛔ [ARTEFATO NÃO-CANÔNICO: {rel}] É estritamente proibido inventar nomes arbitrários de PRD. "
                        "Pelas regras do framework Bombe Code, o PRD estruturado DEVE ser persistido obrigatoriamente "
                        "em 'docs/briefings/PRD.md' e produzido sob a autoridade da agente @grace."
                    ),
                )
            if filename.startswith("viability") and filename not in (
                "viability.md",
                "viability.json",
            ):
                return (
                    False,
                    (
                        f"⛔ [ARTEFATO NÃO-CANÔNICO: {rel}] É estritamente proibido inventar nomes arbitrários de Viabilidade. "
                        "O parecer técnico DEVE ser persistido em 'docs/briefings/VIABILITY.md' sob autoridade do @meira."
                    ),
                )
        return True, None

    # 2. ETAPA PLAN / INCEPTION / REFINEMENT
    if normalized_stage in {STAGE_PLAN, STAGE_INCEPTION, STAGE_REFINEMENT}:
        if is_production_code_path(rel):
            stage_name = normalized_stage
            return (
                False,
                (
                    f"⛔ [BLOQUEIO DE ETAPA: {stage_name}] A criação ou edição de código de produção em '{rel}' é proibida na etapa {stage_name}. "
                    "Esta etapa destina-se à arquitetura, jornadas, decomposição e refinamento de stories em docs/. "
                    "Pressione a tecla TAB na TUI para avançar para a etapa EXECUTE para implementar o código."
                ),
            )
        return True, None

    # 3. ETAPA EXECUTE
    if normalized_stage == STAGE_EXECUTE:
        # Totalmente liberado para codificar e implementar suíte de testes
        return True, None

    # 4. ETAPA VALIDATE
    if normalized_stage in {STAGE_VALIDATE, STAGE_COMPLETED}:
        parts = set(Path(rel).parts)
        # Relatórios em docs/reports/, documentação e testes são permitidos
        if "reports" in parts or any(p in parts for p in TEST_DIRS) or rel.endswith(".md"):
            return True, None

        if is_production_code_path(rel):
            return (
                False,
                (
                    f"⛔ [BLOQUEIO DE ETAPA: VALIDATE] A adição ou alteração estrutural de código em '{rel}' é restrita na etapa VALIDATE. "
                    "Esta etapa é dedicada exclusivamente à auditoria de conformidade, execução de suíte de testes e relatórios em docs/reports/. "
                    "Pressione a tecla TAB na TUI para retornar a EXECUTE caso necessite implementar novos módulos."
                ),
            )
        return True, None

    return True, None
