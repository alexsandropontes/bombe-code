"""Gerenciador de Configuração do Projeto (.bombeconfig) no Bombe Code (ST-019)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProjectConfig(BaseModel):
    """Modelo declarativo de configuração do projeto (.bombeconfig)."""

    name: str = Field(default="bombe-project", description="Nome do projeto")
    type: str = Field(default="web", description="Tipo do projeto: web, api, mobile, cli, lib")
    backend_language: str = Field(default="python", description="Linguagem backend primária")
    frontend_stack: str = Field(default="react", description="Stack de interface frontend")
    root_src: str = Field(default="src/", description="Diretório raiz do código fonte")
    backend_path: str = Field(default="src/backend/", description="Subdiretório de código backend")
    frontend_path: str = Field(
        default="src/frontend/", description="Subdiretório de interface frontend"
    )
    docs_root: str = Field(default="docs/", description="Diretório raiz de documentação")
    branch: str = Field(default="dev", description="Branch de trabalho da IA")
    mode: str = Field(default="tdd-code", description="Modo de engenharia: tdd-code ou vibe-code")
    autonomy: str = Field(default="auto", description="Modo de autonomia: auto, semi-auto, manual")


class ProjectConfigManager:
    """Gerencia a leitura, gravação e autodeteção de configurações em .bombeconfig."""

    def __init__(self, project_dir: str = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.config_path = self.project_dir / ".bombeconfig"

    def load(self) -> ProjectConfig:
        """Carrega a configuração a partir de .bombeconfig ou retorna defaults."""
        if not self.config_path.is_file():
            default_name = self.project_dir.name or "bombe-project"
            return ProjectConfig(name=default_name)

        try:
            content = self.config_path.read_text(encoding="utf-8")
            raw_data = yaml.safe_load(content) or {}

            # Normalização de formatos aninhados (compatibilidade com Bombe Core)
            flat_data: dict[str, Any] = {}
            if "project" in raw_data and isinstance(raw_data["project"], dict):
                p = raw_data["project"]
                flat_data["name"] = p.get("name")
                flat_data["type"] = p.get("type")
                if "language" in p and isinstance(p["language"], dict):
                    flat_data["backend_language"] = p["language"].get("backend")
                    flat_data["frontend_stack"] = p["language"].get("frontend")
                if "structure" in p and isinstance(p["structure"], dict):
                    flat_data["root_src"] = p["structure"].get("root_src")
                    flat_data["backend_path"] = p["structure"].get("backend")
                    flat_data["frontend_path"] = p["structure"].get("frontend")
                    flat_data["docs_root"] = p["structure"].get("docs_root")
                flat_data["branch"] = p.get("branch")

            for k in [
                "mode",
                "autonomy",
                "backend_language",
                "frontend_stack",
                "name",
                "type",
                "root_src",
                "backend_path",
                "frontend_path",
                "docs_root",
                "branch",
            ]:
                if k in raw_data and raw_data[k] is not None:
                    flat_data[k] = raw_data[k]

            # Remove campos None
            clean_data = {k: v for k, v in flat_data.items() if v is not None}
            return ProjectConfig(**clean_data)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao ler .bombeconfig: %s. Usando defaults.", exc)
            return ProjectConfig(name=self.project_dir.name or "bombe-project")

    def save(self, config: ProjectConfig) -> None:
        """Grava a configuração no arquivo .bombeconfig no formato YAML legível."""
        data = {
            "project": {
                "name": config.name,
                "type": config.type,
                "language": {
                    "backend": config.backend_language,
                    "frontend": config.frontend_stack,
                },
                "structure": {
                    "root_src": config.root_src,
                    "backend": config.backend_path,
                    "frontend": config.frontend_path,
                    "docs_root": config.docs_root,
                },
                "branch": config.branch,
            },
            "mode": config.mode,
            "autonomy": config.autonomy,
        }

        yaml_str = yaml.dump(data, sort_keys=False, allow_unicode=True)
        self.config_path.write_text(yaml_str, encoding="utf-8")

    def autodetect(self) -> ProjectConfig:
        """Examina o diretório e detecta as stacks e estrutura automaticamente."""
        name = self.project_dir.name or "bombe-project"
        backend = "python"
        frontend = "none"

        # Detecção de backend
        if (self.project_dir / "pyproject.toml").exists() or (
            self.project_dir / "requirements.txt"
        ).exists():
            backend = "python"
        elif (self.project_dir / "go.mod").exists():
            backend = "go"
        elif (self.project_dir / "pom.xml").exists() or (
            self.project_dir / "build.gradle"
        ).exists():
            backend = "java"
        elif list(self.project_dir.glob("*.csproj")):
            backend = "csharp"
        elif (self.project_dir / "mix.exs").exists():
            backend = "elixir"
        elif (self.project_dir / "package.json").exists():
            backend = "node"

        # Detecção de frontend
        if (self.project_dir / "package.json").exists():
            pkg_content = (self.project_dir / "package.json").read_text(encoding="utf-8")
            if "react" in pkg_content:
                frontend = "react"
            elif "vue" in pkg_content:
                frontend = "vue"
            else:
                frontend = "node"
        elif (self.project_dir / "pubspec.yaml").exists():
            frontend = "flutter"

        root_src = "src/" if (self.project_dir / "src").is_dir() else "./"
        docs_root = "docs/"

        return ProjectConfig(
            name=name,
            backend_language=backend,
            frontend_stack=frontend,
            root_src=root_src,
            docs_root=docs_root,
        )

    def detect_stack(self) -> ProjectConfig:
        """Alias para autodetect()."""
        return self.autodetect()
