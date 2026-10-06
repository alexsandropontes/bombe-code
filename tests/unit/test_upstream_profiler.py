"""Testes unitários para UpstreamProfiler (Lean Inception & PBB)."""

from pathlib import Path

from bombe_code.turing.prompt_assembler import DeliveryTarget
from bombe_code.turing.upstream_profiler import (
    InceptionLevel,
    ProjectOrigin,
    UpstreamProfiler,
)


def test_greenfield_mvp_generates_full_canonical_inception(tmp_path: Path):
    profile = UpstreamProfiler.profile(tmp_path, target=DeliveryTarget.MVP)
    assert profile.origin == ProjectOrigin.GREENFIELD
    assert profile.inception_level == InceptionLevel.FULL_CANONICAL
    assert profile.mocks_allowed is False
    assert profile.is_mvp is True
    assert "docs/briefings/PRD.md" in profile.required_artifacts


def test_greenfield_poc_generates_mini_inception_with_mocks_allowed(tmp_path: Path):
    profile = UpstreamProfiler.profile(tmp_path, target=DeliveryTarget.POC)
    assert profile.origin == ProjectOrigin.GREENFIELD
    assert profile.inception_level == InceptionLevel.MINI
    assert profile.mocks_allowed is True
    assert profile.is_experimental is True


def test_greenfield_enterprise_generates_deep_enterprise_inception(tmp_path: Path):
    profile = UpstreamProfiler.profile(tmp_path, target=DeliveryTarget.ENTERPRISE)
    assert profile.origin == ProjectOrigin.GREENFIELD
    assert profile.inception_level == InceptionLevel.DEEP_ENTERPRISE
    assert profile.mocks_allowed is False
    assert profile.is_enterprise is True
    assert "docs/governance/compliance.md" in profile.required_artifacts


def test_brownfield_project_detected_from_existing_prd(tmp_path: Path):
    prd_dir = tmp_path / "docs" / "briefings"
    prd_dir.mkdir(parents=True)
    prd_file = prd_dir / "PRD.md"
    prd_file.write_text("# PRD existente\n" + "Conteúdo substancial de produto existente..." * 10)

    profile = UpstreamProfiler.profile(tmp_path, target=DeliveryTarget.MVP)
    assert profile.origin == ProjectOrigin.BROWNFIELD
    assert profile.inception_level == InceptionLevel.EVOLUTION_DAKI
    assert profile.mocks_allowed is False
    assert "PBB Delta" in profile.pbb_granularity


def test_brownfield_project_detected_from_src_code_files(tmp_path: Path):
    src_dir = tmp_path / "src" / "modules"
    src_dir.mkdir(parents=True)
    (src_dir / "app.ts").write_text("export const a = 1;")
    (src_dir / "service.ts").write_text("export const s = 2;")
    (src_dir / "repo.ts").write_text("export const r = 3;")

    profile = UpstreamProfiler.profile(tmp_path, target="enterprise")
    assert profile.origin == ProjectOrigin.BROWNFIELD
    assert profile.inception_level == InceptionLevel.EVOLUTION_DAKI
