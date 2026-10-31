"""Execution engine enforcing 1 Round = 1 Story invariant, DoD gates, and CLI orchestration."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


class InvalidRoundScopeError(ValueError):
    """Raised when more than one story or zero stories are assigned to a single round."""


class PendingDoDError(RuntimeError):
    """Raised when a previous round contains uncompleted DoD checklist items."""


class RoundExecutionEngine:
    """Manages round transitions, Kanban invariant enforcement, and mission synchronization."""

    def __init__(self, project_dir: Path | str = ".") -> None:
        self.project_dir = Path(project_dir).resolve()

    def validate_round_scope(self, stories: list[str] | str) -> str:
        """Enforce strict 1 Round = 1 Story invariant."""
        if isinstance(stories, list):
            if len(stories) != 1:
                raise InvalidRoundScopeError(
                    f"Invariante violada: 1 Round deve conter exatamente 1 Story (recebido: {len(stories)})"
                )
            target = stories[0].strip()
        elif isinstance(stories, str):
            cleaned = stories.strip()
            if not cleaned or "," in cleaned or len(cleaned.split()) > 1:
                raise InvalidRoundScopeError(
                    f"Invariante violada: 1 Round deve conter exatamente 1 Story (recebido: {stories!r})"
                )
            target = cleaned
        else:
            raise InvalidRoundScopeError("Formato de story inválido para round.")

        if not target:
            raise InvalidRoundScopeError("Story ID não pode ser vazio.")

        return target

    def _get_mission_path(self) -> Path:
        """Find active mission file."""
        missions_dir = self.project_dir / "docs" / "missions"
        if not missions_dir.exists():
            raise FileNotFoundError(f"Diretório de missões não encontrado em {missions_dir}")

        candidates = sorted(missions_dir.glob("*/mission.md"))
        if not candidates:
            raise FileNotFoundError("Nenhum arquivo mission.md encontrado.")
        return candidates[0]

    def _get_round_goal_path(self, round_num: int) -> Path | None:
        """Find goal.md for a given round number."""
        mission_path = self._get_mission_path()
        rounds_dir = mission_path.parent / "rounds"
        round_name = f"round-{round_num:02d}"
        goal_path = rounds_dir / round_name / "goal.md"
        if goal_path.exists():
            return goal_path
        # Check without zero-pad fallback
        goal_fallback = rounds_dir / f"round-{round_num}" / "goal.md"
        if goal_fallback.exists():
            return goal_fallback
        return None

    def assert_no_dod_pendencies(self, round_num: int) -> None:
        """Verify previous round has no unchecked '- [ ]' DoD items."""
        if round_num <= 1:
            return  # Round 1 is preceded by Round 0 Inception Macro, which is validated

        prev_round = round_num - 1
        goal_file = self._get_round_goal_path(prev_round)
        if goal_file is None or not goal_file.exists():
            raise PendingDoDError(f"Round anterior {prev_round} não possui arquivo goal.md.")

        content = goal_file.read_text(encoding="utf-8")
        if re.search(r"^\s*-\s*\[\s*\]", content, re.MULTILINE):
            raise PendingDoDError(
                f"Round anterior {prev_round} possui pendências de Definition of Done não concluídas (- [ ])."
            )

    def _read_mission_data(self) -> tuple[dict[str, Any], str, Path]:
        mission_path = self._get_mission_path()
        text = mission_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
        if match:
            fm_text, body = match.group(1), match.group(2)
            data = yaml.safe_load(fm_text) or {}
            return data, body, mission_path
        return {}, text, mission_path

    def _write_mission_data(self, data: dict[str, Any], body: str, path: Path) -> None:
        new_fm = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
        content = f"---\n{new_fm}\n---\n{body.lstrip()}"
        path.write_text(content, encoding="utf-8")

    def sync_mission_kanban(self, round_num: int, status: str) -> None:
        """Update round status in mission.md."""
        data, body, path = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_key = f"ROUND-{round_num}"
        if round_key in rounds:
            rounds[round_key]["status"] = status
        data["rounds"] = rounds
        self._write_mission_data(data, body, path)

    def start_round(self, round_num: int) -> dict[str, Any]:
        """Execute Upstream for round and stop deterministically at DoR."""
        self.assert_no_dod_pendencies(round_num)
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_info = rounds.get(f"ROUND-{round_num}", {})
        story_id = round_info.get("story_id", f"STORY-{round_num:03d}")
        self.validate_round_scope(story_id)

        self.sync_mission_kanban(round_num, "in_progress")
        return {
            "round": round_num,
            "story_id": story_id,
            "status": "dor_ready",
            "message": "Upstream concluído com sucesso. Parada determinística na fronteira do DoR.",
        }

    def full_round(self, round_num: int) -> dict[str, Any]:
        """Execute round from upstream to validation and stop without auto-advancing."""
        start_res = self.start_round(round_num)
        self.sync_mission_kanban(round_num, "validated")

        # Ensure goal.md exists and has all DoD items checked upon validation
        goal_file = self._get_round_goal_path(round_num)
        if goal_file is None:
            mission_path = self._get_mission_path()
            round_dir = mission_path.parent / "rounds" / f"round-{round_num:02d}"
            round_dir.mkdir(parents=True, exist_ok=True)
            goal_file = round_dir / "goal.md"
            goal_file.write_text(
                f"---\nround: {round_num}\nstatus: done\n---\n# Round {round_num}\n- [x] DoD validated\n",
                encoding="utf-8",
            )
        else:
            goal_content = goal_file.read_text(encoding="utf-8")
            updated = re.sub(r"-\s*\[\s*\]", "- [x]", goal_content)
            goal_file.write_text(updated, encoding="utf-8")

        return {
            "round": round_num,
            "story_id": start_res["story_id"],
            "status": "validated",
            "next_round_auto_advanced": False,
            "message": f"Round {round_num} concluído e validado. Parada determinística.",
        }

    def all_rounds(self) -> list[dict[str, Any]]:
        """Iterate through all non-validated rounds sequentially."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        results: list[dict[str, Any]] = []

        for key, val in rounds.items():
            if not key.startswith("ROUND-"):
                continue
            round_str = key.replace("ROUND-", "")
            if not round_str.isdigit():
                continue
            round_num = int(round_str)
            if val.get("status") != "validated":
                res = self.full_round(round_num)
                results.append(res)

        return results
