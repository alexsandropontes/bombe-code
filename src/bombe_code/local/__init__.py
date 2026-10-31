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
from .profiles import (
    HARDWARE_PROFILES,
    HardwareProfile,
    ModelKey,
    UnknownModelProfileError,
    build_model_profile,
    get_hardware_profile,
    normalize_model_key,
)
from .vram_gate import VRAMGate

__all__ = [
    "HARDWARE_PROFILES",
    "HardwareProfile",
    "LocalModelError",
    "LocalModelManager",
    "ModelConcurrencyError",
    "ModelKey",
    "ModelProfile",
    "ModelStartupTimeoutError",
    "ModelStatus",
    "NvidiaSmiNotFoundError",
    "UnknownModelProfileError",
    "VRAMGate",
    "VRAMThresholdExceededError",
    "build_model_profile",
    "get_hardware_profile",
    "normalize_model_key",
]
