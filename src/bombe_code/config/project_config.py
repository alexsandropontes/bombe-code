"""Gerenciador de Configuração do Projeto (.bombeconfig) no Bombe Code (ST-019 / MISSION-01)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class InvalidModeError(ValueError):
    """Exceção levantada quando um modo não suportado ou extinto é configurado."""


MODE_ALIASES: dict[str, str] = {
    # Vibe flow
    "vibe-flow": "vibe-flow",
    "vibe_flow": "vibe-flow",
    "vibe-code": "vibe-flow",
    "vibe_code": "vibe-flow",
    "vibe": "vibe-flow",
    # Slice flow
    "slice-flow": "slice-flow",
    "slice_flow": "slice-flow",
    "slice-code": "slice-flow",
    "slice_code": "slice-flow",
    "slice": "slice-flow",
}

CANONICAL_MODES: set[str] = {"slice-flow", "vibe-flow"}


class ProjectConfig(BaseModel):
    """Modelo declarativo de configuração do projeto (.bombeconfig)."""

    name: str = Field(default="bombe-project", description="Nome do projeto")
    type: str = Field(default="web", description="Tipo do projeto: web, api, mobile, cli, lib")
    backend_language: str = Field(default="python", description="Linguagem backend primária")
    frontend_stack: str = Field(default="react", description="Stack de interface frontend")
    root_src: str = Field(default="src/", description="Diretório raiz do código fonte")
    backend_path: str = Field(default="src/backend/", description="Subdiretório de código backend")
    frontend_path: str = Field(
        default="src/frontend/",
        description="Subdiretório de interface frontend",
    )
    docs_root: str = Field(default="docs/", description="Diretório raiz de documentação")
    branch: str = Field(default="dev", description="Branch de trabalho da IA")
    mode: str = Field(
        default="slice-flow",
        description="Modo de engenharia: slice-flow ou vibe-flow",
    )
    mode_origin: str | None = Field(
        default=None,
        description="Modo de origem pré-migração (ex: tdd-code)",
    )
    mode_migrated_at: str | None = Field(
        default=None,
        description="Timestamp ISO 8601 da migração",
    )
    autonomy: str = Field(default="auto", description="Modo de autonomia: auto, semi-auto, manual")
    verbosity: str = Field(
        default="verbose",
        description="Verbosidade do runtime: verbose (padrão) ou quiet",
    )
    delivery_target: str = Field(
        default="enterprise-grade",
        description="Nível de entrega e maturidade: poc, mvp, enterprise-grade",
    )

    def __init__(self, **data: Any) -> None:
        if "mode" in data and data["mode"] is not None:
            data["mode"] = self.validate_mode(data["mode"])
        super().__init__(**data)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        raw = str(v).strip().lower()
        if raw in {"tdd-code", "spec-code"}:
            raise InvalidModeError(
                f"Modo '{v}' foi descontinuado no Bombe Core v4. Modos permitidos: {sorted(CANONICAL_MODES)}"
            )
        if raw in MODE_ALIASES:
            return MODE_ALIASES[raw]
        raise InvalidModeError(
            f"Modo '{v}' é inválido. Modos permitidos: {sorted(CANONICAL_MODES)}"
        )


class ProjectConfigManager:
    """Gerencia a leitura, gravação e autodeteção de configurações em .bombeconfig."""

    def __init__(self, project_dir: str = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.config_path = self.project_dir / ".bombeconfig"

    def _migrate_legacy_data(self, raw_data: dict[str, Any]) -> None:
        """Migra chaves legadas e atualiza o modo extinto tdd-code de forma transparente."""
        current_mode = raw_data.get("mode")
        if current_mode in {"tdd-code", "spec-code"}:
            if not raw_data.get("mode_origin"):
                raw_data["mode_origin"] = current_mode
            raw_data["mode"] = "slice-code"
            if not raw_data.get("mode_migrated_at"):
                raw_data["mode_migrated_at"] = datetime.now(UTC).isoformat()

    def load(self) -> ProjectConfig:
        """Carrega a configuração a partir de .bombeconfig ou retorna defaults."""
        if not self.config_path.is_file():
            default_name = self.project_dir.name or "bombe-project"
            return ProjectConfig(name=default_name)

        try:
            content = self.config_path.read_text(encoding="utf-8")
            raw_data = yaml.safe_load(content) or {}

            # Migração de dados legados em runtime
            self._migrate_legacy_data(raw_data)

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
                "mode_origin",
                "mode_migrated_at",
                "autonomy",
                "verbosity",
                "delivery_target",
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

            clean_data = {k: v for k, v in flat_data.items() if v is not None}
            if "verbosity" in clean_data:
                clean_data["verbosity"] = (
                    "quiet"
                    if str(clean_data["verbosity"]).strip().lower()
                    in ("quiet", "silencioso", "silence")
                    else "verbose"
                )

            return ProjectConfig(**clean_data)

        except InvalidModeError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao ler .bombeconfig: %s. Usando defaults.", exc)
            return ProjectConfig(name=self.project_dir.name or "bombe-project")

    def save(self, config: ProjectConfig) -> None:
        """Grava a configuração no arquivo .bombeconfig no formato YAML legível."""
        data: dict[str, Any] = {
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
        }

        if config.mode_origin is not None:
            data["mode_origin"] = config.mode_origin
        if config.mode_migrated_at is not None:
            data["mode_migrated_at"] = config.mode_migrated_at

        data["verbosity"] = config.verbosity
        data["delivery_target"] = config.delivery_target
        if config.autonomy:
            data["autonomy"] = config.autonomy

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
