"""Subpacote para gerenciamento de modelos e servidores de inferência locais."""

from .contracts import (
    LocalModelError,
    ModelConcurrencyError,
    ModelProfile,
    ModelStartupTimeoutError,
    ModelStatus,
    NvidiaSmiNotFoundError,
    VRAMThresholdExceededError,
)
from .local_manager import LocalModelManager
from .vram_gate import VRAMGate

__all__ = [
    "LocalModelError",
    "LocalModelManager",
    "ModelConcurrencyError",
    "ModelProfile",
    "ModelStartupTimeoutError",
    "ModelStatus",
    "NvidiaSmiNotFoundError",
    "VRAMGate",
    "VRAMThresholdExceededError",
]
