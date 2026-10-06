"""Módulo de atualização (upgrade) do Bombe Code via Git e uv."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .. import __version__

logger = logging.getLogger(__name__)

DEFAULT_GIT_URL = "https://github.com/alexsandropontes/bombe-code.git"


def get_uv_executable() -> str | None:
    """Localiza o binário uv no sistema ou em diretórios comuns de usuário."""
    # 1. PATH do sistema
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path

    # 2. Localizações padrão no Linux/macOS
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
    ]
    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)

    return None


def detect_remote_default_branch(git_url: str) -> str:
    """Detecta a branch padrão do repositório remoto via git ls-remote --symref."""
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--symref", git_url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                match = re.search(r"ref:\s*refs/heads/(\S+)", line)
                if match:
                    return match.group(1).strip()
    except (subprocess.SubprocessError, OSError) as exc:
        logger.debug("Falha ao detectar branch padrão remota: %s", exc)

    return "main"


def get_remote_ref_sha(git_url: str, ref: str) -> str | None:
    """Obtém o SHA do commit remoto para uma branch ou tag específica."""
    try:
        proc = subprocess.run(
            ["git", "ls-remote", git_url, ref],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            lines = proc.stdout.strip().splitlines()
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[0]
    except (subprocess.SubprocessError, OSError) as exc:
        logger.debug("Falha ao consultar commit remoto via git ls-remote: %s", exc)

    return None


def get_local_git_info(project_dir: str = ".") -> dict[str, str] | None:
    """Se executado dentro de um clone local do git, obtém informações da branch e commit."""
    try:
        proc_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        proc_commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc_branch.returncode == 0 and proc_commit.returncode == 0:
            return {
                "branch": proc_branch.stdout.strip(),
                "commit": proc_commit.stdout.strip(),
            }
    except (subprocess.SubprocessError, OSError):
        pass
    return None


def ha_sessao_ativa() -> list[dict[str, str]]:
    """Detecta sessões VIVAS do Bombe Code (TUI/CLI em execução).

    REGRA OPERACIONAL: deploy (`upgrade`/`uv tool install`) NUNCA roda por
    cima de uma sessão ativa — derruba trabalho em voo e deixa o usuário na
    versão velha sem saber. Quem faz deploy primeiro GARANTE que parou.
    """
    import os as _os
    import subprocess as _subprocess

    try:
        out = _subprocess.run(
            ["pgrep", "-af", "bombe"], capture_output=True, text=True, check=False
        )
    except OSError:
        return []
    sessoes: list[dict[str, str]] = []
    meu_pid = _os.getpid()
    for linha in (out.stdout or "").splitlines():
        pid, _, cmd = linha.strip().partition(" ")
        if not pid.isdigit() or int(pid) == meu_pid:
            continue
        # Sessão real: binário do tool em execução (não greps/scripts acidentais)
        if "bin/bombe-code" in cmd or "bin/python -m bombe_code" in cmd:
            sessoes.append({"pid": pid, "cmd": cmd.strip()[:120]})
    return sessoes


def run_upgrade(
    git_url: str | None = None,
    branch: str | None = None,
    tag: str | None = None,
    local: bool = False,
    force: bool = True,
    check_only: bool = False,
    project_dir: str = ".",
) -> dict[str, Any]:
    """Executa o processo de atualização (upgrade) do Bombe Code baseado em Git.

    Retorna um dicionário com o resultado da operação.
    """
    uv_bin = get_uv_executable()
    if not uv_bin:
        return {
            "success": False,
            "error": "uv não encontrado no PATH nem em ~/.local/bin/uv. Instale uv via: curl -LsSf https://astral.sh/uv/install.sh | sh",
            "current_version": __version__,
        }

    # Determina a URL do Git
    final_git_url = git_url or os.environ.get("BOMBE_GIT_URL", DEFAULT_GIT_URL)

    # Modo Local
    if local:
        target_ref = "local (diretório atual)"
        remote_sha = None
        cmd = [uv_bin, "tool", "install"]
        if force:
            cmd.append("--force")
        cmd.append(project_dir)

        if check_only:
            return {
                "success": True,
                "check_only": True,
                "current_version": __version__,
                "target_ref": target_ref,
                "remote_sha": remote_sha,
                "message": f"Modo local: alvo é o diretório '{project_dir}'.",
            }
    else:
        # Modo Remoto Git
        if tag:
            target_ref = tag
            ref_spec = f"refs/tags/{tag}"
            pkg_target = f"git+{final_git_url}@{tag}"
        elif branch:
            target_ref = branch
            ref_spec = f"refs/heads/{branch}"
            pkg_target = f"git+{final_git_url}@{branch}"
        else:
            # Detecta a branch padrão remota
            detected_branch = detect_remote_default_branch(final_git_url)
            target_ref = detected_branch
            ref_spec = f"refs/heads/{detected_branch}"
            pkg_target = f"git+{final_git_url}@{detected_branch}"

        remote_sha = get_remote_ref_sha(final_git_url, ref_spec)

        if check_only:
            return {
                "success": True,
                "check_only": True,
                "current_version": __version__,
                "git_url": final_git_url,
                "target_ref": target_ref,
                "remote_sha": remote_sha,
                "message": (
                    f"Versão instalada: {__version__}\n"
                    f"Alvo no Git: {final_git_url} ({target_ref})\n"
                    f"Commit remoto: {remote_sha or 'desconhecido'}"
                ),
            }

        cmd = [uv_bin, "tool", "install"]
        if force:
            cmd.append("--force")
        cmd.append(pkg_target)

    # Executa o comando uv tool install
    logger.info("Executando upgrade do Bombe Code via uv: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout ao executar uv tool install (limite de 180s excedido).",
            "current_version": __version__,
        }
    except OSError as exc:
        return {
            "success": False,
            "error": f"Erro de execução do uv: {exc}",
            "current_version": __version__,
        }

    if proc.returncode != 0:
        return {
            "success": False,
            "error": f"Falha na instalação pelo uv (código {proc.returncode}):\n{proc.stderr or proc.stdout}",
            "current_version": __version__,
            "raw_output": proc.stderr or proc.stdout,
        }

    # Tenta obter a nova versão instalada
    new_version = __version__
    bombe_bin = shutil.which("bombe-code")
    if bombe_bin:
        try:
            ver_proc = subprocess.run(
                [bombe_bin, "version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if ver_proc.returncode == 0:
                match = re.search(r"bombe-code\s+([0-9a-zA-Z.-]+)", ver_proc.stdout)
                if match:
                    new_version = match.group(1)
        except (subprocess.SubprocessError, OSError):
            pass

    return {
        "success": True,
        "current_version": __version__,
        "new_version": new_version,
        "target_ref": target_ref,
        "remote_sha": remote_sha,
        "git_url": final_git_url if not local else None,
        "message": f"Bombe Code atualizado com sucesso para '{new_version}' a partir de '{target_ref}'!",
        "raw_output": proc.stdout,
    }
