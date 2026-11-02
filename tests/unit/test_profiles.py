from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from bombe_code.local.contracts import LocalModelError, ModelProfile
from bombe_code.local.local_manager import LocalModelManager
from bombe_code.local.profiles import (
    HARDWARE_PROFILES,
    HardwareProfile,
    ModelKey,
    UnknownModelProfileError,
    build_model_profile,
    get_hardware_profile,
    normalize_model_key,
)


class TestSlice1ModelKeyNormalization:
    """Slice 1: Normalização de chaves ModelKey e tratamento de erros."""

    def test_model_keys_values(self) -> None:
        assert ModelKey.GEMMA_4_E4B.value == "gemma-4-e4b"
        assert ModelKey.GEMMA_4_26B_A4B.value == "gemma-4-26b-a4b"
        assert ModelKey.QWEN_3_8_9B.value == "qwen-3.8-9b"
        assert ModelKey.LFM3.value == "lfm3"

    @pytest.mark.parametrize(
        ("input_key", "expected_key"),
        [
            ("gemma-4-e4b", ModelKey.GEMMA_4_E4B),
            ("gemma_4_e4b", ModelKey.GEMMA_4_E4B),
            ("gemma-e4b", ModelKey.GEMMA_4_E4B),
            ("e4b", ModelKey.GEMMA_4_E4B),
            ("GEMMA_4_E4B", ModelKey.GEMMA_4_E4B),
            ("gemma-4-26b-a4b", ModelKey.GEMMA_4_26B_A4B),
            ("gemma-4-26b", ModelKey.GEMMA_4_26B_A4B),
            ("gemma_26b", ModelKey.GEMMA_4_26B_A4B),
            ("gemma-26b", ModelKey.GEMMA_4_26B_A4B),
            ("26b", ModelKey.GEMMA_4_26B_A4B),
            ("qwen-3.8-9b", ModelKey.QWEN_3_8_9B),
            ("qwen_3.8_9b", ModelKey.QWEN_3_8_9B),
            ("qwen-3-8-9b", ModelKey.QWEN_3_8_9B),
            ("qwen_9b", ModelKey.QWEN_3_8_9B),
            ("qwen9b", ModelKey.QWEN_3_8_9B),
            ("qwen", ModelKey.QWEN_3_8_9B),
            ("lfm3", ModelKey.LFM3),
            ("lfm-3", ModelKey.LFM3),
            ("lfm_3", ModelKey.LFM3),
            (ModelKey.LFM3, ModelKey.LFM3),
            (ModelKey.GEMMA_4_26B_A4B, ModelKey.GEMMA_4_26B_A4B),
        ],
    )
    def test_normalize_model_key_valid_variants(
        self, input_key: str | ModelKey, expected_key: ModelKey
    ) -> None:
        assert normalize_model_key(input_key) == expected_key

    def test_normalize_model_key_unknown_raises_error(self) -> None:
        with pytest.raises(UnknownModelProfileError) as exc_info:
            normalize_model_key("unsupported-model-xyz")

        assert issubclass(UnknownModelProfileError, LocalModelError)
        assert "unsupported-model-xyz" in str(exc_info.value)


class TestSlice2HardwareProfilesCatalog:
    """Slice 2: Verificação do catálogo HARDWARE_PROFILES e atributos."""

    def test_catalog_contains_all_models(self) -> None:
        assert len(HARDWARE_PROFILES) == 4
        for key in ModelKey:
            assert key in HARDWARE_PROFILES

    def test_gemma_4_e4b_hardware_profile(self) -> None:
        profile = get_hardware_profile(ModelKey.GEMMA_4_E4B)
        assert profile.model_key == ModelKey.GEMMA_4_E4B
        assert profile.context_size == 131072
        assert profile.flash_attention is True
        assert profile.kv_cache_type == "q8_0"
        assert profile.n_cpu_moe is None

    def test_gemma_4_26b_a4b_hardware_profile(self) -> None:
        profile = get_hardware_profile("gemma_26b")
        assert profile.model_key == ModelKey.GEMMA_4_26B_A4B
        assert profile.context_size == 65536
        assert profile.flash_attention is True
        assert profile.kv_cache_type == "q8_0"
        assert profile.n_cpu_moe == 999

    def test_qwen_3_8_9b_hardware_profile(self) -> None:
        profile = get_hardware_profile("qwen-3.8-9b")
        assert profile.model_key == ModelKey.QWEN_3_8_9B
        assert profile.context_size == 65536
        assert profile.flash_attention is True
        assert profile.kv_cache_type == "q8_0"
        assert profile.n_cpu_moe is None

    def test_lfm3_hardware_profile(self) -> None:
        profile = get_hardware_profile("lfm3")
        assert profile.model_key == ModelKey.LFM3
        assert profile.context_size == 131072
        assert profile.flash_attention is True
        assert profile.kv_cache_type == "q8_0"
        assert profile.n_cpu_moe is None

    def test_hardware_profile_immutability(self) -> None:
        profile = get_hardware_profile(ModelKey.LFM3)
        assert isinstance(profile, HardwareProfile)
        with pytest.raises(FrozenInstanceError):
            profile.context_size = 32768  # type: ignore[misc]


class TestSlice3FactoryAndCommandLineIntegration:
    """Slice 3: Factory build_model_profile e integração de flags de CLI com LocalModelManager."""

    def setup_method(self) -> None:
        self.manager = LocalModelManager(binary_path=Path("/bin/llama-server"))

    def test_build_model_profile_custom_path_and_port(self) -> None:
        custom_path = Path("/tmp/custom_gemma.gguf")
        profile: ModelProfile = build_model_profile(
            "gemma-4-e4b",
            model_path=custom_path,
            port=19000,
            host="0.0.0.0",
        )
        assert profile.name == "gemma-4-e4b"
        assert profile.model_path == custom_path
        assert profile.port == 19000
        assert profile.host == "0.0.0.0"
        assert profile.context_size == 131072
        assert profile.flash_attention is True

    def test_ac1_context_window_128k_for_gemma_e4b_and_lfm3(self) -> None:
        cmd_gemma_e4b = self.manager.build_cli_command(build_model_profile("gemma-4-e4b"))
        cmd_lfm3 = self.manager.build_cli_command(build_model_profile("lfm3"))

        assert "-c" in cmd_gemma_e4b
        assert cmd_gemma_e4b[cmd_gemma_e4b.index("-c") + 1] == "131072"

        assert "-c" in cmd_lfm3
        assert cmd_lfm3[cmd_lfm3.index("-c") + 1] == "131072"

    def test_ac2_context_window_64k_for_gemma_26b_and_qwen(self) -> None:
        cmd_gemma_26b = self.manager.build_cli_command(build_model_profile("gemma_26b"))
        cmd_qwen = self.manager.build_cli_command(build_model_profile("qwen-3.8-9b"))

        assert "-c" in cmd_gemma_26b
        assert cmd_gemma_26b[cmd_gemma_26b.index("-c") + 1] == "65536"

        assert "-c" in cmd_qwen
        assert cmd_qwen[cmd_qwen.index("-c") + 1] == "65536"

    def test_ac3_kv_cache_q8_0_for_all_profiles(self) -> None:
        for key in ModelKey:
            profile = build_model_profile(key)
            cmd = self.manager.build_cli_command(profile)

            assert "-ctk" in cmd
            assert cmd[cmd.index("-ctk") + 1] == "q8_0"
            assert "-ctv" in cmd
            assert cmd[cmd.index("-ctv") + 1] == "q8_0"

    def test_ac4_gemma_26b_moe_cpu_offload_and_flash_attention(self) -> None:
        profile = build_model_profile("gemma-4-26b-a4b")
        cmd = self.manager.build_cli_command(profile)

        assert "--n-cpu-moe" in cmd
        assert cmd[cmd.index("--n-cpu-moe") + 1] == "999"

        assert "-fa" in cmd
        assert cmd[cmd.index("-fa") + 1] == "on"

    def test_ac5_gemma_e4b_flash_attention_on(self) -> None:
        profile = build_model_profile("gemma-4-e4b")
        cmd = self.manager.build_cli_command(profile)

        assert "-fa" in cmd
        assert cmd[cmd.index("-fa") + 1] == "on"
