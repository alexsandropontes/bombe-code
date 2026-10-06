"""Implementação SQLite do repositório da ONDA (Wave Repository Adapter)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bombe_code.domain.wave.models import (
    AutonomyMode,
    EngineeringMode,
    StoryCard,
    Wave,
    WaveId,
    WaveState,
)
from bombe_code.domain.wave.repository import WaveRepositoryInterface
from bombe_code.storage.project_db import ProjectDatabase


class SqliteWaveRepository(WaveRepositoryInterface):
    """Adaptador de infraestrutura que persiste o domínio da ONDA no SQLite (.bombe-code/state.db)."""

    def __init__(self, project_dir: str | Path = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.db = ProjectDatabase(str(self.project_dir))

    def save_wave(self, wave: Wave) -> None:
        self.db.save_wave_state(
            wave_id=wave.wave_id.value,
            state=wave.state.value,
            autonomy_mode=wave.autonomy_mode.value,
            engineering_mode=wave.engineering_mode.value,
        )

    def load_wave(self, wave_id: WaveId | str | None = None) -> Wave | None:
        raw = self.db.load_wave_state()
        if not raw:
            return None

        target_id = str(wave_id) if wave_id else raw.get("wave_id", "ONDA-001")
        return Wave(
            wave_id=WaveId(target_id),
            state=WaveState.from_str(raw.get("state", "DISCUSS")),
            autonomy_mode=AutonomyMode.from_str(raw.get("autonomy_mode", "AUTO")),
            engineering_mode=EngineeringMode.from_str(raw.get("engineering_mode", "tdd-code")),
            project_dir=str(self.project_dir),
        )

    def save_card(self, wave_id: WaveId | str, card: StoryCard) -> None:
        wid = str(wave_id)
        self.db.save_kanban_card(
            story_id=card.story_id,
            wave_id=wid,
            title=card.title,
            agent=card.assigned_to,
            status=card.status,
            blocked_by=card.blocked_by,
        )

    def list_cards(self, wave_id: WaveId | str) -> list[StoryCard]:
        wid = str(wave_id)
        raw_cards = self.db.list_kanban_cards(wave_id=wid)
        cards: list[StoryCard] = []
        for rc in raw_cards:
            cards.append(
                StoryCard(
                    story_id=rc.get("story_id", ""),
                    title=rc.get("title", ""),
                    status=rc.get("status", "BACKLOG"),
                    assigned_to=rc.get("agent", "@barbara"),
                    blocked_by=rc.get("blocked_by"),
                    metadata=rc,
                )
            )
        return cards

    def save_gate_evaluation(
        self, wave_id: WaveId | str, gate_name: str, evaluation: dict[str, Any]
    ) -> None:
        wid = str(wave_id)
        self.db.save_gate_evaluation(
            wave_id=wid,
            stage=evaluation.get("stage", "DISCUSS"),
            gate_name=gate_name,
            passed=bool(evaluation.get("passed", True)),
            reason=str(evaluation.get("reason", "")),
            details=evaluation,
        )
