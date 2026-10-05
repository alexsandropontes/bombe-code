"""Governança Documental Canônica: Separação entre Documentos do Projeto e Artefatos da Onda."""

from __future__ import annotations

from pathlib import Path


class WaveWorkspace:
    """Gerenciador canônico de estrutura de pastas e artefatos de documentação."""

    def __init__(self, project_dir: str | Path = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.docs_dir = self.project_dir / "docs"

    # =========================================================================
    # 1. Documentos Globais do PROJETO (Vivos, cumulativos e únicos)
    # =========================================================================
    @property
    def briefings_dir(self) -> Path:
        return self.docs_dir / "briefings"

    @property
    def prd_path(self) -> Path:
        return self.briefings_dir / "PRD.md"

    @property
    def viability_path(self) -> Path:
        return self.briefings_dir / "VIABILITY.md"

    @property
    def architecture_dir(self) -> Path:
        return self.docs_dir / "architecture"

    @property
    def system_architecture_path(self) -> Path:
        return self.architecture_dir / "SYSTEM_ARCHITECTURE.md"

    @property
    def journey_master_path(self) -> Path:
        return self.architecture_dir / "journey.md"

    @property
    def db_schema_path(self) -> Path:
        return self.architecture_dir / "db.md"

    @property
    def adr_dir(self) -> Path:
        return self.architecture_dir / "adr"

    # =========================================================================
    # 2. Documentos Específicos da ONDA (Fatias de Engenharia / Workspace da Onda)
    # =========================================================================
    @property
    def waves_root(self) -> Path:
        return self.docs_dir / "waves"

    def wave_dir(self, wave_id: str) -> Path:
        return self.waves_root / wave_id.strip().upper()

    def wave_epics_dir(self, wave_id: str) -> Path:
        return self.wave_dir(wave_id) / "epics"

    def wave_stories_dir(self, wave_id: str) -> Path:
        return self.wave_dir(wave_id) / "stories"

    def wave_qa_dir(self, wave_id: str) -> Path:
        return self.wave_dir(wave_id) / "qa"

    def wave_journey_slice_path(self, wave_id: str) -> Path:
        return self.wave_dir(wave_id) / "journey-slice.md"

    def wave_validation_report_path(self, wave_id: str) -> Path:
        return self.wave_dir(wave_id) / "validation_report.md"

    def wave_telemetry_path(self, wave_id: str) -> Path:
        return self.wave_dir(wave_id) / "telemetry.json"

    def ensure_wave_structure(self, wave_id: str) -> None:
        """Garante a existência física dos diretórios da ONDA."""
        self.wave_epics_dir(wave_id).mkdir(parents=True, exist_ok=True)
        self.wave_stories_dir(wave_id).mkdir(parents=True, exist_ok=True)
        self.wave_qa_dir(wave_id).mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 3. Resolução Resiliente e Retrocompatível
    # =========================================================================
    def find_story_file(self, story_id: str, wave_id: str | None = None) -> Path | None:
        """Localiza o arquivo de uma story com busca em cascata (Wave -> Backlog -> Fallback)."""
        sid = story_id.strip().upper()

        # 1. Procura na onda específica se informada
        if wave_id:
            sdir = self.wave_stories_dir(wave_id)
            if sdir.exists():
                for p in sdir.glob(f"{sid}*.md"):
                    if not p.name.endswith("_test_plan.md"):
                        return p

        # 2. Procura em qualquer onda existente
        if self.waves_root.exists():
            for p in self.waves_root.glob(f"*/stories/{sid}*.md"):
                if not p.name.endswith("_test_plan.md"):
                    return p

        # 3. Procura no padrão legado docs/backlog/stories/
        backlog_dir = self.docs_dir / "backlog" / "stories"
        if backlog_dir.exists():
            for p in backlog_dir.glob(f"{sid}*.md"):
                if not p.name.endswith("_test_plan.md"):
                    return p

        # 4. Procura no fallback docs/stories/
        legacy_dir = self.docs_dir / "stories"
        if legacy_dir.exists():
            for p in legacy_dir.glob(f"{sid}*.md"):
                if not p.name.endswith("_test_plan.md"):
                    return p

        return None

    def find_test_plan_file(self, story_id: str, wave_id: str | None = None) -> Path | None:
        """Localiza o arquivo de plano de teste de uma story."""
        sid = story_id.strip().upper()

        if wave_id:
            qadir = self.wave_qa_dir(wave_id)
            if qadir.exists():
                for p in qadir.glob(f"{sid}*.md"):
                    return p

        if self.waves_root.exists():
            for p in self.waves_root.glob(f"*/qa/{sid}*.md"):
                return p

        # Fallbacks legados
        for parent in (self.docs_dir / "backlog" / "stories", self.docs_dir / "stories"):
            if parent.exists():
                for p in parent.glob(f"{sid}*_test_plan.md"):
                    return p

        return None
