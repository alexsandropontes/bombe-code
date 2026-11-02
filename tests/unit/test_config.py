from pathlib import Path

import pytest

from bombe_code.config.project_config import (
    InvalidModeError,
    ProjectConfig,
    ProjectConfigManager,
)


def test_project_config_defaults():
    """Valida defaults soberanos: slice-flow e enterprise-grade."""
    cfg = ProjectConfig()
    assert cfg.mode == "slice-flow"
    assert cfg.delivery_target == "enterprise-grade"
    assert cfg.mode_origin is None
    assert cfg.mode_migrated_at is None


def test_project_config_invalid_mode_raises():
    """Garante que modos inválidos ou legados levantem InvalidModeError diretamente."""
    with pytest.raises(InvalidModeError, match="descontinuado"):
        ProjectConfig(mode="tdd-code")
    with pytest.raises(InvalidModeError, match="descontinuado"):
        ProjectConfig(mode="spec-code")
    with pytest.raises(InvalidModeError, match="inválido"):
        ProjectConfig(mode="invalid-random-mode")


def test_project_config_valid_vibe_code():
    """Garante suporte ao modo vibe-flow e normalização de vibe-code."""
    cfg = ProjectConfig(mode="vibe-code")
    assert cfg.mode == "vibe-flow"
    cfg_flow = ProjectConfig(mode="vibe-flow")
    assert cfg_flow.mode == "vibe-flow"


def test_config_manager_load_and_migrate_legacy(tmp_path: Path):
    """Testa leitura e migração transparente de arquivo legado tdd-code."""
    legacy_file = tmp_path / ".bombeconfig"
    legacy_file.write_text("mode: tdd-code\nproject:\n  name: legacy-app\n", encoding="utf-8")

    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    cfg = mgr.load()

    assert cfg.mode == "slice-flow"
    assert cfg.mode_origin == "tdd-code"
    assert cfg.mode_migrated_at is not None
    assert cfg.name == "legacy-app"


def test_config_manager_save_persists_migration_fields(tmp_path: Path):
    """Garante que campos de migração sejam persistidos no YAML gerado."""
    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    cfg = ProjectConfig(
        name="migrated-app",
        mode="slice-flow",
        mode_origin="tdd-code",
        mode_migrated_at="2026-10-31T15:00:00Z",
    )
    mgr.save(cfg)

    reloaded = mgr.load()
    assert reloaded.mode == "slice-flow"
    assert reloaded.mode_origin == "tdd-code"
    assert reloaded.mode_migrated_at == "2026-10-31T15:00:00Z"
    assert reloaded.delivery_target == "enterprise-grade"
