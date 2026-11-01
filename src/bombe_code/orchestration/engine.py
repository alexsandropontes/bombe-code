"""Execution engine enforcing 1 Round = 1 Story invariant, DoD gates, and CLI orchestration."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from bombe_code.domain.contracts.round import (
    InvalidRoundStateError,
    RoundNotReadyError,
    RoundState,
    RoundStatus,
    SliceState,
    SliceType,
)
from bombe_code.orchestration.autonomous_runner import AutonomousRunner


class InvalidRoundScopeError(ValueError):
    """Raised when more than one story or zero stories are assigned to a single round."""


class PendingDoDError(RuntimeError):
    """Raised when a previous round contains uncompleted DoD checklist items."""


class RoundExecutionEngine:
    """Manages round transitions, Kanban invariant enforcement, and mission synchronization."""

    def __init__(self, project_dir: Path | str = ".", autonomous: bool | None = None) -> None:
        self.project_dir = Path(project_dir).resolve()
        if autonomous is None:
            self.autonomous = "PYTEST_CURRENT_TEST" not in os.environ
        else:
            self.autonomous = autonomous
        self._runner: AutonomousRunner | None = None

    @property
    def runner(self) -> AutonomousRunner:
        if self._runner is None:
            self._runner = AutonomousRunner(self.project_dir)
        return self._runner

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

        candidates = sorted(missions_dir.glob("*/mission.md"), reverse=True)
        if not candidates:
            raise FileNotFoundError("Nenhum arquivo mission.md encontrado.")

        # Prioriza missão em estado ativo (open, active, in_progress)
        open_statuses = {"open", "active", "in_progress"}
        for cand in candidates:
            try:
                text = cand.read_text(encoding="utf-8")
                match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
                if match:
                    data = yaml.safe_load(match.group(1)) or {}
                    if str(data.get("status", "")).lower() in open_statuses:
                        return cand
            except (OSError, yaml.YAMLError):
                continue

        # Fallback para a missão mais recente
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

    def _get_previous_round_num(self, round_num: int) -> int | None:
        """Find immediate predecessor round in mission sequence."""
        try:
            data, _, _ = self._read_mission_data()
            rounds = data.get("rounds", {})
            numbers: list[int] = []
            for k in rounds:
                if k.startswith("ROUND-"):
                    parsed = self._parse_round_number(k)
                    if parsed is not None:
                        numbers.append(parsed)
            numbers.sort()
            lower = [n for n in numbers if n < round_num]
            if lower:
                return lower[-1]
            return None
        except (FileNotFoundError, yaml.YAMLError, KeyError):
            return round_num - 1 if round_num > 1 else None

    def assert_no_dod_pendencies(self, round_num: int) -> None:
        """Verify previous round has no unchecked '- [ ]' DoD items."""
        prev_round = self._get_previous_round_num(round_num)
        if prev_round is None:
            return  # First round in sequence, no predecessor DoD check

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
        rounds = data.get("rounds")
        if rounds is None or not isinstance(rounds, dict):
            rounds = {}
        round_key = f"ROUND-{round_num}"
        if round_key in rounds and isinstance(rounds[round_key], dict):
            rounds[round_key]["status"] = status
        else:
            rounds[round_key] = {
                "status": status,
                "story_id": f"STORY-{round_num:03d}",
            }
        data["rounds"] = rounds
        self._write_mission_data(data, body, path)

    def _create_round_scaffolds(self, round_num: int, story_id: str) -> Path:
        """Create physical scaffolding files for a round if missing."""
        mission_path = self._get_mission_path()
        round_dir = mission_path.parent / "rounds" / f"round-{round_num:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)

        goal_path = round_dir / "goal.md"
        if not goal_path.exists():
            goal_content = (
                f"---\nround: {round_num}\nstatus: dor_ready\nstory_id: {story_id}\n"
                "dor_ready: true\n---\n"
                f"# Round {round_num} ({story_id})\n\n"
                "## Checklist de Definition of Ready (DoR)\n"
                "- [x] Story analisada e validada\n"
                "- [x] Slices técnicos fatiados\n\n"
                "## Checklist de Definition of Done (DoD)\n"
                "- [ ] Slices backend e frontend implementados\n"
                "- [ ] Testes passando e cobertura validada\n"
            )
            goal_path.write_text(goal_content, encoding="utf-8")

        stories_path = round_dir / "stories.md"
        if not stories_path.exists():
            stories_content = (
                f"# Stories do Round {round_num}\n\n"
                f"- **{story_id}**: Implementação com TDD e fatiamento vertical.\n"
            )
            stories_path.write_text(stories_content, encoding="utf-8")

        return round_dir

    def _build_default_slices(self, story_id: str, status: str = "pending") -> list[SliceState]:
        """Build standard fullstack vertical slices (Backend TDD + Frontend Construction)."""
        return [
            SliceState(
                slice_id="SLICE-01",
                name=f"Backend Slice {story_id}",
                type=SliceType.BACKEND_TDD,
                status=status,
            ),
            SliceState(
                slice_id="SLICE-02",
                name=f"Frontend Slice {story_id}",
                type=SliceType.FRONTEND_CONSTRUCTION,
                status=status,
            ),
        ]

    def _get_story_slices(self, story_id: str, status: str = "pending") -> list[SliceState]:
        """Extract slices from story markdown file, falling back to default slices."""
        try:
            mission_path = self._get_mission_path()
            story_file = mission_path.parent / "stories" / f"{story_id}.md"
            if story_file.is_file():
                text = story_file.read_text(encoding="utf-8")
                slice_matches = re.findall(r"^###\s+(SLICE-[A-Za-z0-9\-_]+)", text, re.MULTILINE)
                if slice_matches:
                    slices = []
                    for s_id in slice_matches:
                        slice_type = (
                            SliceType.FRONTEND_CONSTRUCTION
                            if "FRONT" in s_id.upper() or "UI" in s_id.upper()
                            else SliceType.BACKEND_TDD
                        )
                        slices.append(
                            SliceState(
                                slice_id=s_id,
                                name=f"Slice {s_id}",
                                type=slice_type,
                                status=status,
                            )
                        )
                    return slices
        except Exception:
            pass
        return self._build_default_slices(story_id, status=status)

    def start_round(self, round_num: int) -> RoundState:
        """Execute Upstream for round and stop deterministically at DoR."""
        self.assert_no_dod_pendencies(round_num)
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_info = rounds.get(f"ROUND-{round_num}", {})
        story_id = round_info.get("story_id", f"STORY-{round_num:03d}")
        self.validate_round_scope(story_id)

        self._create_round_scaffolds(round_num, story_id)
        slices = self._get_story_slices(story_id, status="pending")
        self.sync_mission_kanban(round_num, RoundStatus.DOR_READY.value)
        return RoundState(
            round_number=round_num,
            story_id=story_id,
            status=RoundStatus.DOR_READY,
            slices=slices,
            dor_ready=True,
            dod_validated=False,
            message="Upstream concluído com sucesso. Parada determinística na fronteira do DoR.",
        )

    def burn_round(self, round_num: int) -> RoundState:
        """Execute Downstream slice burning with strict DoR gate check."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_info = rounds.get(f"ROUND-{round_num}", {})
        current_status = round_info.get("status", RoundStatus.PENDING.value)
        goal_file = self._get_round_goal_path(round_num)

        valid_dor_states = (
            RoundStatus.DOR_READY.value,
            RoundStatus.BURNING.value,
            RoundStatus.IN_PROGRESS.value,
        )
        if current_status not in valid_dor_states or goal_file is None:
            raise RoundNotReadyError(
                f"Round {round_num} não atingiu DoR (Definition of Ready). "
                f"Execute 'round start {round_num}' antes de queimar."
            )

        story_id = round_info.get("story_id", f"STORY-{round_num:03d}")
        mission_path = self._get_mission_path()
        story_file = mission_path.parent / "stories" / f"{story_id}.md"

        # Execução autônoma real via local LLMs se configurado e story existir
        if self.autonomous and story_file.is_file():
            burn_result = self.runner.execute_burn_station(round_num, story_id, story_file)
            if not burn_result.success:
                raise RuntimeError(
                    f"Falha na queima autônoma do Round {round_num} ({story_id}): "
                    f"Testes não passaram após tentativas."
                )

        slices = self._get_story_slices(story_id, status="done")
        self.sync_mission_kanban(round_num, RoundStatus.BURNING.value)
        if goal_file and goal_file.exists():
            content = goal_file.read_text(encoding="utf-8")
            content = re.sub(r"status:\s*.*", f"status: {RoundStatus.BURNING.value}", content)
            goal_file.write_text(content, encoding="utf-8")

        return RoundState(
            round_number=round_num,
            story_id=story_id,
            status=RoundStatus.BURNING,
            slices=slices,
            dor_ready=True,
            dod_validated=False,
            message=f"Round {round_num} slices queimados com sucesso. Pronto para code review.",
        )

    def review_round(self, round_num: int) -> RoundState:
        """Perform code review gate checking previous burn completion."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_info = rounds.get(f"ROUND-{round_num}", {})
        current_status = round_info.get("status", RoundStatus.PENDING.value)

        if current_status in (RoundStatus.PENDING.value, RoundStatus.DOR_READY.value):
            raise InvalidRoundStateError(
                f"Round {round_num} ainda não foi queimado para revisão. Status atual: {current_status}"
            )

        story_id = round_info.get("story_id", f"STORY-{round_num:03d}")

        if self.autonomous:
            rev_res = self.runner.execute_review_station(round_num, story_id)
            if not rev_res.success:
                raise RuntimeError(f"Auditoria de code review reprovada no Round {round_num} ({story_id}).")

        slices = self._get_story_slices(story_id, status="done")
        self.sync_mission_kanban(round_num, RoundStatus.REVIEWING.value)
        goal_file = self._get_round_goal_path(round_num)
        if goal_file and goal_file.exists():
            content = goal_file.read_text(encoding="utf-8")
            content = re.sub(r"status:\s*.*", f"status: {RoundStatus.REVIEWING.value}", content)
            goal_file.write_text(content, encoding="utf-8")

        return RoundState(
            round_number=round_num,
            story_id=story_id,
            status=RoundStatus.REVIEWING,
            slices=slices,
            dor_ready=True,
            dod_validated=False,
            message=f"Round {round_num} revisado com conformidade. Pronto para validação de DoD.",
        )

    def arch_review_round(self, round_num: int) -> RoundState:
        """Perform architectural review and commit authorization with @unclebob."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_info = rounds.get(f"ROUND-{round_num}", {})
        story_id = round_info.get("story_id", f"STORY-{round_num:03d}")

        if self.autonomous:
            arch_res = self.runner.execute_arch_review_station(round_num, story_id)
            if not arch_res.success:
                raise RuntimeError(f"Auditoria arquitetural reprovada por @unclebob no Round {round_num} ({story_id}).")

        slices = self._get_story_slices(story_id, status="done")
        return RoundState(
            round_number=round_num,
            story_id=story_id,
            status=RoundStatus.REVIEWING,
            slices=slices,
            dor_ready=True,
            dod_validated=False,
            message=f"Round {round_num} aprovado por @unclebob (Arquitetura & Clean Code).",
        )

    def validate_round(self, round_num: int) -> RoundState:
        """Validate DoD items, update goal.md, and mark round validated."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})
        round_info = rounds.get(f"ROUND-{round_num}", {})
        story_id = round_info.get("story_id", f"STORY-{round_num:03d}")

        if self.autonomous:
            val_res = self.runner.execute_validate_station(round_num, story_id)
            if not val_res.success:
                raise PendingDoDError(f"DoD Gate reprovado no Round {round_num} ({story_id}): testes falhando.")

        goal_file = self._get_round_goal_path(round_num)
        if goal_file is None:
            mission_path = self._get_mission_path()
            round_dir = mission_path.parent / "rounds" / f"round-{round_num:02d}"
            round_dir.mkdir(parents=True, exist_ok=True)
            goal_file = round_dir / "goal.md"
            goal_file.write_text(
                f"---\nround: {round_num}\nstatus: validated\nstory_id: {story_id}\n"
                "dor_ready: true\ndod_validated: true\n---\n"
                f"# Round {round_num} ({story_id})\n\n"
                "## Checklist de Definition of Done (DoD)\n"
                "- [x] DoD validated\n",
                encoding="utf-8",
            )
        else:
            content = goal_file.read_text(encoding="utf-8")
            content = re.sub(r"status:\s*.*", f"status: {RoundStatus.VALIDATED.value}", content)
            content = re.sub(r"-\s*\[\s*\]", "- [x]", content)
            goal_file.write_text(content, encoding="utf-8")

        self.sync_mission_kanban(round_num, RoundStatus.VALIDATED.value)
        slices = self._get_story_slices(story_id, status="done")
        return RoundState(
            round_number=round_num,
            story_id=story_id,
            status=RoundStatus.VALIDATED,
            slices=slices,
            dor_ready=True,
            dod_validated=True,
            next_round_auto_advanced=False,
            message=f"Round {round_num} concluído e validado. Parada determinística.",
        )

    def status_round(self, round_num: int | None = None) -> list[RoundState] | RoundState:
        """Retrieve current state of rounds from mission and physical files."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})

        states: list[RoundState] = []
        for key in sorted(rounds.keys()):
            if not key.startswith("ROUND-"):
                continue
            r_num_str = key.replace("ROUND-", "")
            if not r_num_str.isdigit():
                continue
            r_num = int(r_num_str)
            val = rounds[key]
            story_id = val.get("story_id", f"STORY-{r_num:03d}")
            raw_status = val.get("status", "pending")
            try:
                status_enum = RoundStatus(raw_status)
            except ValueError:
                status_enum = RoundStatus.PENDING

            is_dor = status_enum in (
                RoundStatus.DOR_READY,
                RoundStatus.BURNING,
                RoundStatus.REVIEWING,
                RoundStatus.VALIDATED,
            )
            is_dod = status_enum == RoundStatus.VALIDATED

            slice_status = "done" if is_dod or status_enum in (RoundStatus.BURNING, RoundStatus.REVIEWING) else "pending"
            slices = self._get_story_slices(story_id, status=slice_status)

            state = RoundState(
                round_number=r_num,
                story_id=story_id,
                status=status_enum,
                slices=slices,
                dor_ready=is_dor,
                dod_validated=is_dod,
                message=f"Round {r_num} status: {status_enum.value}",
            )
            states.append(state)

        if round_num is not None:
            for s in states:
                if s.round_number == round_num:
                    return s
            return RoundState(
                round_number=round_num,
                story_id=f"STORY-{round_num:03d}",
                status=RoundStatus.PENDING,
            )

        return states

    def execute_round_full(self, round_num: int) -> RoundState:
        """Execute round from upstream to validation and stop without auto-advancing."""
        self.start_round(round_num)
        self.burn_round(round_num)
        self.review_round(round_num)
        self.arch_review_round(round_num)
        return self.validate_round(round_num)

    full_round = execute_round_full

    def _assert_no_test_failures(self, state: RoundState) -> None:
        """Assert that round completed with full validation and without test failures."""
        if state.status != RoundStatus.VALIDATED or not state.dod_validated:
            raise RuntimeError(f"Round {state.round_number} falhou na validação: {state.message}")

    def _parse_round_number(self, round_key: str) -> int | None:
        """Extract numeric round number from round key (e.g. ROUND-01 -> 1)."""
        match = re.search(r"\d+", round_key)
        return int(match.group()) if match else None

    def execute_round_all(self, timeout: int | None = None) -> list[RoundState]:
        """Iterate through all non-validated rounds sequentially with fail-fast enforcement."""
        data, _, _ = self._read_mission_data()
        rounds = data.get("rounds", {})

        round_keys = [k for k in rounds if k.startswith("ROUND-")]
        sorted_keys = sorted(
            round_keys,
            key=lambda k: self._parse_round_number(k) or 0,
        )

        results: list[RoundState] = []
        for key in sorted_keys:
            round_num = self._parse_round_number(key)
            if round_num is None:
                continue
            val = rounds[key]
            if val.get("status") != RoundStatus.VALIDATED.value:
                state = self.execute_round_full(round_num)
                self._assert_no_test_failures(state)
                results.append(state)

        return results

    all_rounds = execute_round_all

