"""Perfis de hardware, restrições de contexto e particionamento de memória para inferência local."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .contracts import LocalModelError, ModelProfile


class ModelKey(str, Enum):
    """Chaves canônicas de identificação de modelos locais."""

    GEMMA_4_E4B = "gemma-4-e4b"
    GEMMA_4_26B_A4B = "gemma-4-26b-a4b"
    QWEN_3_8_9B = "qwen-3.8-9b"
    LFM3 = "lfm3"


class UnknownModelProfileError(LocalModelError):
    """Lançada quando a chave do modelo não corresponde a nenhum perfil homologado."""


@dataclass(frozen=True)
class HardwareProfile:
    """Perfil estático de hardware e restrições de execução para um modelo."""

    model_key: ModelKey
    display_name: str
    default_model_path: Path
    context_size: int
    flash_attention: bool
    kv_cache_type: str = "q8_0"
    n_cpu_moe: int | None = None
    n_gpu_layers: int = 999
    draft_model_path: Path | None = None
    spec_type: str | None = None
    spec_draft_n_max: int | None = None
    extra_args: tuple[str, ...] = field(default_factory=tuple)

    def to_model_profile(
        self,
        model_path: Path | str | None = None,
        port: int = 18094,
        host: str = "127.0.0.1",
        extra_args: tuple[str, ...] = (),
        enable_mtp: bool = True,
        draft_model_path: Path | str | None = None,
    ) -> ModelProfile:
        """Converte as configurações de hardware em um ModelProfile para execução."""
        resolved_path = Path(model_path) if model_path is not None else self.default_model_path
        assembled_args: list[str] = list(self.extra_args)

        if self.n_cpu_moe is not None:
            assembled_args.extend(["--n-cpu-moe", str(self.n_cpu_moe)])

        if extra_args:
            assembled_args.extend(list(extra_args))

        resolved_draft_path: Path | None = None
        resolved_spec_type: str | None = None
        resolved_spec_draft_n_max: int | None = None

        if enable_mtp:
            if draft_model_path is not None:
                resolved_draft_path = Path(draft_model_path)
            else:
                resolved_draft_path = self.draft_model_path
            resolved_spec_type = self.spec_type
            resolved_spec_draft_n_max = self.spec_draft_n_max

        return ModelProfile(
            name=self.model_key.value,
            model_path=resolved_path,
            context_size=self.context_size,
            port=port,
            host=host,
            n_gpu_layers=self.n_gpu_layers,
            flash_attention=self.flash_attention,
            kv_cache_type=self.kv_cache_type,
            draft_model_path=resolved_draft_path,
            spec_type=resolved_spec_type,
            spec_draft_n_max=resolved_spec_draft_n_max,
            extra_args=tuple(assembled_args),
        )


HARDWARE_PROFILES: dict[ModelKey, HardwareProfile] = {
    ModelKey.GEMMA_4_E4B: HardwareProfile(
        model_key=ModelKey.GEMMA_4_E4B,
        display_name="Gemma 4 E4B",
        default_model_path=Path("/home/lexpontes/modelos-llm/gemma-4-E4B-it-UD-Q4_K_XL.gguf"),
        context_size=131072,
        flash_attention=True,
        kv_cache_type="q8_0",
        n_cpu_moe=None,
        n_gpu_layers=30,
        draft_model_path=Path("/home/lexpontes/modelos-llm/mtp-gemma-4-E4B-it-Q8_0.gguf"),
        spec_type="draft-mtp",
        spec_draft_n_max=3,
        extra_args=("-b", "1024", "-ub", "256", "--parallel", "1"),
    ),
    ModelKey.GEMMA_4_26B_A4B: HardwareProfile(
        model_key=ModelKey.GEMMA_4_26B_A4B,
        display_name="Gemma 4 26B-A4B MoE",
        default_model_path=Path("/home/lexpontes/modelos-llm/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf"),
        context_size=65536,
        flash_attention=True,
        kv_cache_type="q8_0",
        n_cpu_moe=999,
        draft_model_path=Path("/home/lexpontes/modelos-llm/mtp-gemma-4-26B-A4B-it-Q8_0.gguf"),
        spec_type="draft-mtp",
        spec_draft_n_max=3,
    ),
    ModelKey.QWEN_3_8_9B: HardwareProfile(
        model_key=ModelKey.QWEN_3_8_9B,
        display_name="Qwen 3.8-9B",
        default_model_path=Path("/home/lexpontes/modelos-llm/Qwen3.8-9B-Q4_K_M.gguf"),
        context_size=65536,
        flash_attention=True,
        kv_cache_type="q8_0",
        n_cpu_moe=None,
        n_gpu_layers=18,
        draft_model_path=None,
        spec_type="draft-mtp",
        spec_draft_n_max=2,
        extra_args=("-b", "1024", "-ub", "256", "--parallel", "1"),
    ),
    ModelKey.LFM3: HardwareProfile(
        model_key=ModelKey.LFM3,
        display_name="LFM3 1.7B",
        default_model_path=Path("/home/lexpontes/modelos-llm/LFM3-1.7B-Q5_K_M.gguf"),
        context_size=131072,
        flash_attention=True,
        kv_cache_type="q8_0",
        n_cpu_moe=None,
        draft_model_path=None,
        spec_type=None,
        spec_draft_n_max=None,
    ),
}

_MODEL_KEY_ALIASES: dict[str, ModelKey] = {
    # Gemma 4 E4B aliases
    "gemma-4-e4b": ModelKey.GEMMA_4_E4B,
    "gemma_4_e4b": ModelKey.GEMMA_4_E4B,
    "gemma-e4b": ModelKey.GEMMA_4_E4B,
    "gemma_e4b": ModelKey.GEMMA_4_E4B,
    "e4b": ModelKey.GEMMA_4_E4B,
    "gemma4-e4b": ModelKey.GEMMA_4_E4B,
    "gemma4_e4b": ModelKey.GEMMA_4_E4B,
    "gemma_4b": ModelKey.GEMMA_4_E4B,
    "gemma-4b": ModelKey.GEMMA_4_E4B,
    # Gemma 4 26B-A4B aliases
    "gemma-4-26b-a4b": ModelKey.GEMMA_4_26B_A4B,
    "gemma_4_26b_a4b": ModelKey.GEMMA_4_26B_A4B,
    "gemma-4-26b": ModelKey.GEMMA_4_26B_A4B,
    "gemma_4_26b": ModelKey.GEMMA_4_26B_A4B,
    "gemma-26b": ModelKey.GEMMA_4_26B_A4B,
    "gemma_26b": ModelKey.GEMMA_4_26B_A4B,
    "26b": ModelKey.GEMMA_4_26B_A4B,
    "gemma-26b-a4b": ModelKey.GEMMA_4_26B_A4B,
    # Qwen 3.8-9B aliases
    "qwen-3.8-9b": ModelKey.QWEN_3_8_9B,
    "qwen_3.8_9b": ModelKey.QWEN_3_8_9B,
    "qwen-3-8-9b": ModelKey.QWEN_3_8_9B,
    "qwen-3.8": ModelKey.QWEN_3_8_9B,
    "qwen_3.8": ModelKey.QWEN_3_8_9B,
    "qwen-9b": ModelKey.QWEN_3_8_9B,
    "qwen_9b": ModelKey.QWEN_3_8_9B,
    "qwen9b": ModelKey.QWEN_3_8_9B,
    "qwen": ModelKey.QWEN_3_8_9B,
    # LFM3 aliases
    "lfm3": ModelKey.LFM3,
    "lfm-3": ModelKey.LFM3,
    "lfm_3": ModelKey.LFM3,
    "lfm": ModelKey.LFM3,
}


def normalize_model_key(key: str | ModelKey) -> ModelKey:
    """Normaliza identificadores flexíveis e aliases para a chave canônica ModelKey."""
    if isinstance(key, ModelKey):
        return key

    raw = str(key).strip().lower()
    if raw in _MODEL_KEY_ALIASES:
        return _MODEL_KEY_ALIASES[raw]

    sanitized = raw.replace("_", "-")
    if sanitized in _MODEL_KEY_ALIASES:
        return _MODEL_KEY_ALIASES[sanitized]

    valid_keys = [k.value for k in ModelKey]
    raise UnknownModelProfileError(
        f"Chave de modelo desconhecida: '{key}'. Chaves suportadas: {valid_keys}"
    )


def get_hardware_profile(key: str | ModelKey) -> HardwareProfile:
    """Recupera o HardwareProfile correspondente à chave fornecida."""
    canonical_key = normalize_model_key(key)
    return HARDWARE_PROFILES[canonical_key]


def build_model_profile(
    key: str | ModelKey,
    model_path: Path | str | None = None,
    port: int = 18094,
    host: str = "127.0.0.1",
    extra_args: tuple[str, ...] = (),
    enable_mtp: bool = True,
    draft_model_path: Path | str | None = None,
) -> ModelProfile:
    """Constrói um ModelProfile operacional a partir da chave de modelo e overrides."""
    hardware_profile = get_hardware_profile(key)
    return hardware_profile.to_model_profile(
        model_path=model_path,
        port=port,
        host=host,
        extra_args=extra_args,
        enable_mtp=enable_mtp,
        draft_model_path=draft_model_path,
    )
