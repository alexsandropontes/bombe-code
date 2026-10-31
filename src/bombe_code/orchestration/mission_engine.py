"""Engine governing mission lifecycles, physical scaffolding, and atomic single-mission invariant."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from bombe_code.domain.contracts.mission import (
    MissionState,
    MissionStatus,
    NoActiveMissionError,
    OpenMissionBlockedError,
    PendingDoDError,
)

OPEN_STATUSES = {"open", "active", "in_progress"}


class MissionLifecycleEngine:
    """Manages creation, gatekeeping, inspection, and completion of project missions."""

    def __init__(self, project_dir: Path | str = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.missions_dir = self.project_dir / "docs" / "missions"

    def _parse_mission_file(self, path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
        if match:
            fm_text, body = match.group(1), match.group(2)
            data = yaml.safe_load(fm_text) or {}
            return data, body
        return {}, text

    def _write_mission_file(self, path: Path, data: dict[str, Any], body: str) -> None:
        fm = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
        path.write_text(f"---\n{fm}\n---\n{body.lstrip()}", encoding="utf-8")

    def assert_no_open_mission(self) -> None:
        """Enforces atomic gatekeeper: raises OpenMissionBlockedError if any mission is open."""
        if not self.missions_dir.exists():
            return

        for mission_file in sorted(self.missions_dir.glob("*/mission.md")):
            data, _ = self._parse_mission_file(mission_file)
            status = str(data.get("status", "")).lower()
            if status in OPEN_STATUSES:
                mission_id = data.get("id", mission_file.parent.name)
                raise OpenMissionBlockedError(
                    f"Existe uma missão ativa ou em progresso: {mission_id} ({status}). "
                    "Finalize a missão antes de iniciar outra."
                )

    def get_next_mission_id(self) -> str:
        """Calculates next sequential zero-padded mission directory ID."""
        if not self.missions_dir.exists():
            return "01"

        highest = 0
        for entry in self.missions_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                val = int(entry.name)
                highest = max(highest, val)

        return f"{highest + 1:02d}"

    def _scaffold_structure(self, mission_dir: Path) -> None:
        subdirs = ["prd", "architecture", "epics", "stories", "rounds"]
        for sub in subdirs:
            (mission_dir / sub).mkdir(parents=True, exist_ok=True)

    def _create_mission_manifest(
        self, mission_id: str, title: str, demand: str, mission_dir: Path
    ) -> tuple[dict[str, Any], Path, str]:
        created_at = datetime.now(UTC).isoformat()
        manifest_data = {
            "id": f"MISSION-{mission_id}",
            "title": title,
            "demand": demand,
            "status": MissionStatus.OPEN.value,
            "created_at": created_at,
            "completed_at": None,
            "rounds": {},
        }
        body = f"# MISSION-{mission_id}: {title}\n\n## Demanda\n{demand}\n"
        mission_file = mission_dir / "mission.md"
        self._write_mission_file(mission_file, manifest_data, body)
        return manifest_data, mission_file, created_at

    def init_mission(self, demand: str, title: str | None = None) -> MissionState:
        """Atomically scaffolds a new mission if no open mission exists."""
        if not demand or not demand.strip():
            raise ValueError("Demand cannot be empty")

        self.assert_no_open_mission()

        mission_id = self.get_next_mission_id()
        resolved_title = title.strip() if title and title.strip() else f"Mission {mission_id}"
        mission_dir = self.missions_dir / mission_id
        self._scaffold_structure(mission_dir)

        _, mission_file, created_at = self._create_mission_manifest(
            mission_id, resolved_title, demand.strip(), mission_dir
        )

        return MissionState(
            id=mission_id,
            title=resolved_title,
            demand=demand.strip(),
            status=MissionStatus.OPEN,
            path=mission_file,
            created_at=created_at,
            completed_at=None,
            rounds={},
            current_round=None,
            total_rounds=0,
        )

    def _build_state(self, path: Path, data: dict[str, Any]) -> MissionState:
        raw_status = str(data.get("status", "open")).lower()
        status = (
            MissionStatus(raw_status)
            if raw_status in MissionStatus._value2member_map_
            else MissionStatus.OPEN
        )
        rounds = data.get("rounds") or {}
        total = len(rounds)
        curr = None
        for key in sorted(rounds.keys()):
            if rounds[key].get("status") in OPEN_STATUSES:
                match = re.search(r"\d+", key)
                if match:
                    curr = int(match.group())
                    break

        return MissionState(
            id=path.parent.name,
            title=str(data.get("title", f"Mission {path.parent.name}")),
            demand=str(data.get("demand", "")),
            status=status,
            path=path,
            created_at=str(data.get("created_at", "")),
            completed_at=data.get("completed_at"),
            rounds=rounds,
            current_round=curr,
            total_rounds=total,
        )

    def get_active_mission(self) -> MissionState | None:
        """Returns the currently active mission state if one exists."""
        if not self.missions_dir.exists():
            return None

        candidates = sorted(self.missions_dir.glob("*/mission.md"), reverse=True)
        for path in candidates:
            data, _ = self._parse_mission_file(path)
            if str(data.get("status", "")).lower() in OPEN_STATUSES:
                return self._build_state(path, data)

        return None

    def _validate_rounds_dod(self, state: MissionState) -> None:
        for r_name, r_info in state.rounds.items():
            r_status = str(r_info.get("status", "")).lower()
            if r_status not in {"validated", "completed"}:
                raise PendingDoDError(
                    f"O round '{r_name}' está com status '{r_status}'. Todos os rounds devem ser validados."
                )

        rounds_dir = state.path.parent / "rounds"
        if rounds_dir.exists():
            for goal in rounds_dir.glob("*/goal.md"):
                content = goal.read_text(encoding="utf-8")
                if re.search(r"^\s*-\s*\[\s*\]", content, re.MULTILINE):
                    raise PendingDoDError(
                        f"O arquivo {goal.parent.name}/{goal.name} possui pendências de DoD não concluídas (- [ ])."
                    )

    def complete_mission(self, force: bool = False) -> MissionState:
        """Completes active mission after asserting DoD completion, or forces closure."""
        active = self.get_active_mission()
        if active is None:
            raise NoActiveMissionError("Nenhuma missão ativa encontrada para encerramento.")

        if not force:
            self._validate_rounds_dod(active)

        data, body = self._parse_mission_file(active.path)
        data["status"] = MissionStatus.COMPLETED.value
        completed_at = datetime.now(UTC).isoformat()
        data["completed_at"] = completed_at
        self._write_mission_file(active.path, data, body)

        return self._build_state(active.path, data)
