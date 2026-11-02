"""Cognitive routing matrix: maps demand situations to primary and fallback models."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class DemandSituation(StrEnum):
    """Canonical demand situations across the Bombe Code lifecycle."""

    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"
    UPSTREAM_CRITICAL = "upstream_critical"
    UPSTREAM_LIGHT = "upstream_light"
    FINAL_REVIEW = "final_review"


class ModelNotConfiguredError(RuntimeError):
    """Raised when an LLM operation is requested without any configured model."""

    def __init__(
        self,
        message: str = (
            "Nenhum modelo de IA está configurado no Bombe Code.\n"
            "Para executar operações com IA, configure seus modelos executando:\n"
            "  bombe-code models setup  (ou use o comando /models na TUI)"
        ),
    ) -> None:
        super().__init__(message)


class ModelSlot(BaseModel):
    """Specification of an LLM provider and model target."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(..., description="Provider name (e.g. zai, openai, anthropic, vllm-local, ollama)")
    model: str = Field(..., description="Model identifier (e.g. glm-5.3-flash, qwen-3.8-9b, gemma-4-e4b)")
    base_url: str | None = Field(default=None, description="Optional custom base URL for local or custom endpoints")


class SituationRoute(BaseModel):
    """Primary and fallback routing definition for a specific situation."""

    model_config = ConfigDict(frozen=True)

    primary: ModelSlot | None = None
    fallback: ModelSlot | None = None


def _default_empty_routes() -> dict[str, SituationRoute]:
    return {situation.value: SituationRoute() for situation in DemandSituation}


class RoutingMatrixConfig(BaseModel):
    """Persisted matrix configuring model execution across all demand situations."""

    routes: dict[str, SituationRoute] = Field(default_factory=_default_empty_routes)

    def is_configured(self) -> bool:
        """Return True if at least one demand situation has a primary model defined."""
        return any(route.primary is not None for route in self.routes.values())

    def quick_setup(
        self,
        primary: ModelSlot,
        fallback: ModelSlot | None = None,
    ) -> None:
        """Replicate the primary and optional fallback model across ALL situations."""
        for situation in DemandSituation:
            self.routes[situation.value] = SituationRoute(
                primary=primary,
                fallback=fallback,
            )

    def set_route(
        self,
        situation: DemandSituation | str,
        primary: ModelSlot,
        fallback: ModelSlot | None = None,
    ) -> None:
        """Customize primary and fallback models for a specific situation."""
        sit_key = situation.value if isinstance(situation, DemandSituation) else str(situation).lower()
        if sit_key not in [s.value for s in DemandSituation]:
            valid = ", ".join(s.value for s in DemandSituation)
            raise ValueError(f"Situação inválida: '{sit_key}'. Situações válidas: {valid}")
        self.routes[sit_key] = SituationRoute(primary=primary, fallback=fallback)

    def get_route(self, situation: DemandSituation | str) -> SituationRoute:
        """Retrieve routing configuration for a given situation."""
        sit_key = situation.value if isinstance(situation, DemandSituation) else str(situation).lower()
        route = self.routes.get(sit_key)
        if route is None:
            return SituationRoute()
        return route

    def require_route(self, situation: DemandSituation | str) -> SituationRoute:
        """Retrieve routing configuration or raise ModelNotConfiguredError if missing."""
        if not self.is_configured():
            raise ModelNotConfiguredError()
        route = self.get_route(situation)
        if route.primary is None:
            # Fallback to any configured route if this specific situation was not defined
            for alt in self.routes.values():
                if alt.primary is not None:
                    return alt
            raise ModelNotConfiguredError()
        return route


def check_llm_ready() -> tuple[bool, str]:
    """Checks if at least one LLM or provider is configured and ready for execution."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True, ""
    matrix = load_matrix()
    if matrix.is_configured():
        return True, ""
    env_keys = ["ZAI_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    if any(k in os.environ for k in env_keys):
        return True, ""
    return False, (
        "Nenhum modelo de IA está configurado no Bombe Code.\n"
        "Para executar operações com IA, configure seus modelos executando:\n"
        "  bombe-code models setup  (ou use o comando /models na TUI)"
    )


def get_matrix_path() -> Path:
    """Return the filesystem location for models_matrix.json."""
    if "BOMBE_MODELS_MATRIX_PATH" in os.environ:
        return Path(os.environ["BOMBE_MODELS_MATRIX_PATH"]).resolve()

    # Check for project-specific override
    project_override = Path.cwd() / ".bombe-code" / "models_matrix.json"
    if project_override.is_file():
        return project_override

    return Path.home() / ".local" / "share" / "bombe-code" / "models_matrix.json"


def load_matrix(path: Path | None = None) -> RoutingMatrixConfig:
    """Loads routing matrix from persistent storage."""
    target_path = path or get_matrix_path()
    if not target_path.exists():
        return RoutingMatrixConfig()
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RoutingMatrixConfig.model_validate(data)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning(
            "Could not parse routing matrix at %s: %s; returning empty config",
            target_path,
            exc,
        )
        return RoutingMatrixConfig()


def save_matrix(config: RoutingMatrixConfig, path: Path | None = None) -> None:
    """Persists routing matrix to disk atomically."""
    target_path = path or get_matrix_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump(mode="json")

    dir_path = target_path.parent
    with tempfile.NamedTemporaryFile("w", dir=dir_path, delete=False, encoding="utf-8") as tmp_file:
        json.dump(payload, tmp_file, indent=2, ensure_ascii=False)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        tmp_name = tmp_file.name

    os.replace(tmp_name, target_path)
