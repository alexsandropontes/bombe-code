#!/usr/bin/env python3
"""Script de versionamento semântico automático (SemVer) baseado em Conventional Commits."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"
INIT_PATH = ROOT_DIR / "src" / "bombe_code" / "__init__.py"


def run_git(args: list[str]) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True)
    return res.stdout.strip()


def get_current_version_from_pyproject() -> str:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not m:
        raise ValueError("Campo version não encontrado no pyproject.toml")
    return m.group(1)


def get_latest_git_tag() -> str | None:
    tag = run_git(["describe", "--tags", "--abbrev=0"])
    return tag if tag else None


def parse_semver(version: str) -> tuple[int, int, int]:
    clean = version.lstrip("v")
    parts = clean.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def calculate_bump(commits: list[str]) -> str:
    """Calcula se o bump é major, minor ou patch a partir das mensagens de commit."""
    bump_type = "patch"
    for c in commits:
        if "BREAKING CHANGE:" in c or re.search(r"^[a-z]+(\([^\)]+\))?!:", c):
            return "major"
        if re.search(r"^feat(\([^\)]+\))?:", c):
            bump_type = "minor"
    return bump_type


def bump_version(current: str, bump_type: str) -> str:
    major, minor, patch = parse_semver(current)
    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def update_files(new_version: str) -> None:
    # Atualiza pyproject.toml
    pyproj = PYPROJECT_PATH.read_text(encoding="utf-8")
    pyproj = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', pyproj, count=1)
    PYPROJECT_PATH.write_text(pyproj, encoding="utf-8")

    # Atualiza __init__.py
    if INIT_PATH.exists():
        init_content = INIT_PATH.read_text(encoding="utf-8")
        init_content = re.sub(
            r'__version__\s*=\s*"[^"]+"', f'__version__ = "{new_version}"', init_content, count=1
        )
        INIT_PATH.write_text(init_content, encoding="utf-8")


def main() -> int:
    latest_tag = get_latest_git_tag()
    current_ver = get_current_version_from_pyproject()

    git_range = f"{latest_tag}..HEAD" if latest_tag else "HEAD"
    log_output = run_git(["log", git_range, "--oneline"])
    commits = [line.strip() for line in log_output.splitlines() if line.strip()]

    # Filtra commits de release anteriores
    commits = [c for c in commits if "chore(release):" not in c]

    if not commits:
        print("ℹ️  Nenhum commit novo desde a última tag de release.")
        return 0

    base_version = latest_tag.lstrip("v") if latest_tag else current_ver
    bump_type = calculate_bump(commits)
    new_version = bump_version(base_version, bump_type)

    print(f"🚀 Bump de versão: {base_version} ➔ {new_version} ({bump_type.upper()})")
    update_files(new_version)

    # Cria commit e tag
    subprocess.run(["git", "add", str(PYPROJECT_PATH), str(INIT_PATH)], cwd=ROOT_DIR, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "--author=Alexsandro Pontes <alexsandropontes@gmail.com>",
            "-m",
            f"chore(release): v{new_version} [no-test]",
        ],
        cwd=ROOT_DIR,
        check=True,
    )
    subprocess.run(
        ["git", "tag", "-a", f"v{new_version}", "-m", f"Release v{new_version}"],
        cwd=ROOT_DIR,
        check=True,
    )

    print(f"✅ Versão v{new_version} commitada e tagueada com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
