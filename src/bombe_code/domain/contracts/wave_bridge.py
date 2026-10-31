"""Domain contracts for Wave Bridge and Deprecation Redirects."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class LegacyWaveCommand(str, Enum):
    """Comandos legados suportados pelo Wave Bridge."""

    START = "start"
    RUN = "run"
    CYCLE = "cycle"
    VALIDATE = "validate"
    STATUS = "status"
    PROMOTE = "promote"
    END = "end"


class WaveBridgeRedirect(BaseModel):
    """Contrato de redirecionamento e depreciação de comandos legados."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    legacy_command: LegacyWaveCommand
    canonical_command: str
    target_subapp: str
    deprecated: bool = True
    explanation: str
