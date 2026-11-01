"""Testes unitários para parametrização de MTP (Multi-Token Prediction) no launcher."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.local.contracts import DraftModelNotFoundError, ModelProfile
from bombe_code.local.local_manager import LocalModelManager
from bombe_code.local.profiles import (
    ModelKey,
    build_model_profile,
    get_hardware_profile,
)


class TestMTPContractsAndProfiles:
    """Validação de contratos, defaults e factories de MTP."""

    def test_draft_model_not_found_error_inheritance(self) -> None:
        from bombe_code.local.contracts import LocalModelError

        assert issubclass(DraftModelNotFoundError, LocalModelError)

    def test_model_profile_optional_mtp_fields(self) -> None:
        profile = ModelProfile(
            name="test",
            model_path=Path("/tmp/model.gguf"),
            draft_model_path=Path("/tmp/draft.gguf"),
            spec_type="draft-mtp",
            spec_draft_n_max=3,
        )
        assert profile.draft_model_path == Path("/tmp/draft.gguf")
        assert profile.spec_type == "draft-mtp"
        assert profile.spec_draft_n_max == 3

    def test_gemma_4_e4b_hardware_profile_defaults(self) -> None:
        hp = get_hardware_profile(ModelKey.GEMMA_4_E4B)
        assert hp.draft_model_path == Path("/home/lexpontes/modelos-llm/mtp-gemma-4-E4B-it-Q8_0.gguf")
        assert hp.spec_type == "draft-mtp"
        assert hp.spec_draft_n_max == 3

    def test_gemma_4_26b_a4b_hardware_profile_defaults(self) -> None:
        hp = get_hardware_profile(ModelKey.GEMMA_4_26B_A4B)
        assert hp.draft_model_path == Path("/home/lexpontes/modelos-llm/mtp-gemma-4-26B-A4B-it-Q8_0.gguf")
        assert hp.spec_type == "draft-mtp"
        assert hp.spec_draft_n_max == 3

    def test_qwen_3_8_9b_hardware_profile_defaults(self) -> None:
        hp = get_hardware_profile(ModelKey.QWEN_3_8_9B)
        assert hp.draft_model_path is None
        assert hp.spec_type is None
        assert hp.spec_draft_n_max is None

    def test_lfm3_hardware_profile_defaults(self) -> None:
        hp = get_hardware_profile(ModelKey.LFM3)
        assert hp.draft_model_path is None
        assert hp.spec_type is None
        assert hp.spec_draft_n_max is None

    def test_build_model_profile_disabling_mtp(self) -> None:
        profile = build_model_profile(ModelKey.GEMMA_4_E4B, enable_mtp=False)
        assert profile.draft_model_path is None
        assert profile.spec_type is None
        assert profile.spec_draft_n_max is None

    def test_build_model_profile_custom_draft_path(self) -> None:
        custom_draft = Path("/tmp/custom-draft.gguf")
        profile = build_model_profile(ModelKey.GEMMA_4_E4B, draft_model_path=custom_draft)
        assert profile.draft_model_path == custom_draft
        assert profile.spec_type == "draft-mtp"
        assert profile.spec_draft_n_max == 3


class TestMTPCommandLineGeneration:
    """Validação da montagem de comandos CLI do llama-server com MTP (AC-1, AC-2, AC-3)."""

    @pytest.fixture
    def manager(self) -> LocalModelManager:
        return LocalModelManager()

    def test_ac1_gemma_4_e4b_mtp_command(self, manager: LocalModelManager) -> None:
        profile = build_model_profile(ModelKey.GEMMA_4_E4B, enable_mtp=True)
        cmd = manager.build_cli_command(profile)

        assert "--model-draft" in cmd
        draft_idx = cmd.index("--model-draft")
        assert cmd[draft_idx + 1] == "/home/lexpontes/modelos-llm/mtp-gemma-4-E4B-it-Q8_0.gguf"

        assert "--spec-type" in cmd
        spec_type_idx = cmd.index("--spec-type")
        assert cmd[spec_type_idx + 1] == "draft-mtp"

        assert "--spec-draft-n-max" in cmd
        draft_n_idx = cmd.index("--spec-draft-n-max")
        assert cmd[draft_n_idx + 1] == "3"

        fa_idx = cmd.index("-fa")
        assert cmd[fa_idx + 1] == "on"

    def test_ac2_gemma_4_26b_a4b_mtp_command(self, manager: LocalModelManager) -> None:
        profile = build_model_profile(ModelKey.GEMMA_4_26B_A4B, enable_mtp=True)
        cmd = manager.build_cli_command(profile)

        assert "--model-draft" in cmd
        draft_idx = cmd.index("--model-draft")
        assert cmd[draft_idx + 1] == "/home/lexpontes/modelos-llm/mtp-gemma-4-26B-A4B-it-Q8_0.gguf"

        assert "--spec-type" in cmd
        spec_type_idx = cmd.index("--spec-type")
        assert cmd[spec_type_idx + 1] == "draft-mtp"

        assert "--spec-draft-n-max" in cmd
        draft_n_idx = cmd.index("--spec-draft-n-max")
        assert cmd[draft_n_idx + 1] == "3"

        fa_idx = cmd.index("-fa")
        assert cmd[fa_idx + 1] == "on"

        assert "--n-cpu-moe" in cmd
        moe_idx = cmd.index("--n-cpu-moe")
        assert cmd[moe_idx + 1] == "999"

    def test_ac3_qwen_3_8_9b_mtp_command(self, manager: LocalModelManager) -> None:
        profile = build_model_profile(ModelKey.QWEN_3_8_9B, enable_mtp=False)
        cmd = manager.build_cli_command(profile)

        assert "--model-draft" not in cmd
        assert "--spec-type" not in cmd

        fa_idx = cmd.index("-fa")
        assert cmd[fa_idx + 1] == "on"

    def test_disabled_mtp_emits_no_mtp_flags(self, manager: LocalModelManager) -> None:
        profile = build_model_profile(ModelKey.GEMMA_4_E4B, enable_mtp=False)
        cmd = manager.build_cli_command(profile)

        assert "--model-draft" not in cmd
        assert "--spec-type" not in cmd
        assert "--spec-draft-n-max" not in cmd


class TestMTPPhysicalValidation:
    """Validação da existência física de arquivos de draft (AC-4)."""

    def test_ac4_validate_profile_missing_draft_raises_error(self, tmp_path: Path) -> None:
        manager = LocalModelManager()
        missing_file = tmp_path / "inexistent-draft.gguf"
        profile = ModelProfile(
            name="test-model",
            model_path=tmp_path / "model.gguf",
            draft_model_path=missing_file,
            spec_type="draft-mtp",
            spec_draft_n_max=3,
        )

        with pytest.raises(DraftModelNotFoundError) as exc_info:
            manager.validate_profile(profile)

        assert str(missing_file) in str(exc_info.value)

    def test_validate_profile_existing_draft_passes(self, tmp_path: Path) -> None:
        manager = LocalModelManager()
        existing_draft = tmp_path / "real-draft.gguf"
        existing_draft.write_text("dummy gguf header")

        profile = ModelProfile(
            name="test-model",
            model_path=tmp_path / "model.gguf",
            draft_model_path=existing_draft,
            spec_type="draft-mtp",
            spec_draft_n_max=3,
        )

        manager.validate_profile(profile)

    def test_validate_profile_none_draft_passes(self, tmp_path: Path) -> None:
        manager = LocalModelManager()
        profile = ModelProfile(
            name="test-model",
            model_path=tmp_path / "model.gguf",
            draft_model_path=None,
            spec_type="draft-mtp",
            spec_draft_n_max=2,
        )

        manager.validate_profile(profile)

    def test_start_model_aborts_on_missing_draft_before_vram_gate(self, tmp_path: Path) -> None:
        from bombe_code.local.vram_gate import VRAMGate

        vram_gate_mock = MagicMock(spec=VRAMGate)
        manager = LocalModelManager(vram_gate=vram_gate_mock)
        missing_draft = tmp_path / "absent-draft.gguf"

        profile = ModelProfile(
            name="test-model",
            model_path=tmp_path / "model.gguf",
            draft_model_path=missing_draft,
            spec_type="draft-mtp",
            spec_draft_n_max=3,
        )

        with pytest.raises(DraftModelNotFoundError):
            manager.start_model(profile)

        assert vram_gate_mock.assert_clean.call_count == 0
