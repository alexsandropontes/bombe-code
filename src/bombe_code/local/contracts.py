from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ModelStatus(str, Enum):
    """Estados do ciclo de vida de um servidor de modelo local."""

    STOPPED = "STOPPED"
    STARTING = "STARTING"
    READY = "READY"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


class LocalModelError(Exception):
    """Exceção base para operações de modelos locais."""


class VRAMThresholdExceededError(LocalModelError):
    """Lançada quando a VRAM residual excede o limite tolerado para nova alocação."""


class ModelStartupTimeoutError(LocalModelError):
    """Lançada quando o servidor local não atinge prontidão dentro da janela de tempo."""


class ModelConcurrencyError(LocalModelError):
    """Lançada ao tentar instanciar um modelo enquanto outro já está ativo ou inicializando."""


class NvidiaSmiNotFoundError(LocalModelError):
    """Lançada quando o utilitário nvidia-smi não é encontrado e o modo estrito está ativo."""


class DraftModelNotFoundError(LocalModelError):
    """Lançada quando o artefato do modelo draft especificado não existe fisicamente."""


@dataclass(frozen=True)
class ModelProfile:
    """Perfil declarativo de execução de modelo no llama-server."""

    name: str
    model_path: Path
    context_size: int = 131072
    port: int = 18094
    host: str = "127.0.0.1"
    n_gpu_layers: int = 999
    flash_attention: bool = True
    kv_cache_type: str = "q8_0"
    draft_model_path: Path | None = None
    spec_type: str | None = None
    spec_draft_n_max: int | None = None
    extra_args: tuple[str, ...] = field(default_factory=tuple)
    env_vars: tuple[tuple[str, str], ...] = field(default_factory=tuple)
