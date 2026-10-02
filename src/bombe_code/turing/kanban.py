"""Gerenciador e Sincronizador Dinâmico de Kanban (ST-029).

Controla o ciclo de vida dos cards no SQLite local (state.db) e sincroniza
bidirecionalmente com os arquivos físicos em docs/backlog/stories/ST-xxx.md.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any

from bombe_code.storage.project_db import ProjectDatabase

logger = logging.getLogger(__name__)


class KanbanCardStatus(str, Enum):
    BACKLOG = "BACKLOG"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DEV_DONE = "DEV_DONE"
    VALIDATE = "VALIDATE"
    DONE = "DONE"


class KanbanManager:
    """Gerencia a persistência e sincronização dos cards da ONDA."""

    def __init__(
        self,
        project_dir: str = ".",
        db: ProjectDatabase | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.db = db or ProjectDatabase(str(self.project_dir))
        self.stories_dir = self.project_dir / "docs" / "backlog" / "stories"

    def add_card(
        self,
        story_id: str,
        wave_id: str,
        title: str,
        agent: str,
        status: str = KanbanCardStatus.BACKLOG.value,
        reviews: dict[str, Any] | None = None,
        is_blocked: bool = False,
        block_reason: str = "",
        blocked_by: str = "",
    ) -> dict[str, Any]:
        """Registra um novo card de story no Kanban."""
        self.db.save_kanban_card(
            story_id=story_id,
            wave_id=wave_id,
            title=title,
            agent=agent,
            status=status,
            reviews=reviews or {},
            is_blocked=is_blocked,
            block_reason=block_reason,
            blocked_by=blocked_by,
        )
        return self.get_card(story_id) or {
            "story_id": story_id,
            "wave_id": wave_id,
            "title": title,
            "agent": agent,
            "status": status,
            "reviews": reviews or {},
            "is_blocked": is_blocked,
            "block_reason": block_reason,
            "blocked_by": blocked_by,
        }

    def update_status(
        self,
        story_id: str,
        status: str,
        reviews: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atualiza o status de um card no SQLite e sincroniza no arquivo físico."""
        success = self.db.update_kanban_card_status(
            story_id=story_id,
            status=status,
            reviews=reviews,
        )
        if success:
            self.sync_markdown_file(story_id=story_id, new_status=status)

        card = self.get_card(story_id)
        return {
            "success": success,
            "story_id": story_id,
            "status": card.get("status") if card else status,
            "reviews": card.get("reviews") if card else (reviews or {}),
            "is_blocked": card.get("is_blocked", False) if card else False,
            "block_reason": card.get("block_reason", "") if card else "",
            "blocked_by": card.get("blocked_by", "") if card else "",
        }

    def block_card(
        self,
        story_id: str,
        reason: str,
        blocked_by: str = "",
    ) -> dict[str, Any]:
        """Sinaliza bloqueio da linha no local exato do problema (sem alterar status)."""
        success = self.db.set_kanban_card_blocked(
            story_id=story_id,
            is_blocked=True,
            reason=reason,
            blocked_by=blocked_by,
        )
        if success:
            self.sync_markdown_file(
                story_id=story_id,
                blocked=True,
                blocked_reason=reason,
            )
        return self.get_card(story_id) or {}

    def unblock_card(self, story_id: str) -> dict[str, Any]:
        """Remove o bloqueio do card após resolução, permitindo o fluxo seguir."""
        success = self.db.set_kanban_card_blocked(
            story_id=story_id,
            is_blocked=False,
            reason="",
            blocked_by="",
        )
        if success:
            self.sync_markdown_file(story_id=story_id, blocked=False)
        return self.get_card(story_id) or {}

    def get_card(self, story_id: str) -> dict[str, Any] | None:
        """Recupera um card pelo ID."""
        return self.db.get_kanban_card(story_id)

    def list_cards(self, wave_id: str | None = None) -> list[dict[str, Any]]:
        """Lista cards cadastrados na ONDA."""
        return self.db.list_kanban_cards(wave_id=wave_id)

    def sync_markdown_file(
        self,
        story_id: str,
        new_status: str | None = None,
        blocked: bool | None = None,
        blocked_reason: str = "",
    ) -> bool:
        """Atualiza a linha de status e blocked no arquivo markdown correspondente."""
        if not self.stories_dir.exists():
            return False

        # Procura arquivos que iniciem com o story_id
        for path in self.stories_dir.glob(f"{story_id}*.md"):
            try:
                content = path.read_text(encoding="utf-8")
                updated = content
                if new_status is not None:
                    updated = re.sub(
                        r">\s*\*\*Status:\*\*.*",
                        f"> **Status:** {new_status}",
                        updated,
                    )
                if blocked is not None:
                    blocked_str = (
                        f"True ({blocked_reason})" if blocked and blocked_reason else str(blocked)
                    )
                    if re.search(r">\s*\*\*Blocked:\*\*.*", updated):
                        updated = re.sub(
                            r">\s*\*\*Blocked:\*\*.*",
                            f"> **Blocked:** {blocked_str}",
                            updated,
                        )
                    else:
                        # Insere após o Status
                        updated = re.sub(
                            r"(>\s*\*\*Status:\*\*.*)",
                            rf"\1\n> **Blocked:** {blocked_str}",
                            updated,
                        )
                path.write_text(updated, encoding="utf-8")
                return True
            except Exception as e:  # noqa: BLE001
                logger.warning("Falha ao sincronizar arquivo %s: %s", path, e)
        return False

    def scan_and_sync_directory(self, wave_id: str = "ONDA-006") -> list[dict[str, Any]]:
        """Lê os arquivos físicos de stories e cataloga no banco SQLite."""
        if not self.stories_dir.exists():
            return []

        synced_cards: list[dict[str, Any]] = []
        for path in sorted(self.stories_dir.glob("ST-*.md")):
            try:
                content = path.read_text(encoding="utf-8")
                # Extrai ID (ex: ST-001)
                id_match = re.search(r"ST-\d+", path.name)
                story_id = id_match.group(0) if id_match else path.stem

                # Extrai Título (primeira linha # ...)
                title_match = re.search(r"^#\s*(?:STORY\s*ST-\d+:\s*)?(.*)", content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else path.stem

                # Extrai Status
                status_match = re.search(r">\s*\*\*Status:\*\*\s*([A-Za-z_-]+)", content)
                status = (
                    status_match.group(1).strip().upper()
                    if status_match
                    else KanbanCardStatus.BACKLOG.value
                )

                # Extrai Responsável
                agent_match = re.search(r">\s*\*\*Responsáveis:\*\*\s*(@\w+)", content)
                agent = agent_match.group(1).strip() if agent_match else "@unclebob"

                # Extrai Blocked
                blocked_match = re.search(
                    r">\s*\*\*Blocked:\*\*\s*(True|False|Sim|Não)", content, re.IGNORECASE
                )
                is_blocked = False
                if blocked_match:
                    val = blocked_match.group(1).lower()
                    is_blocked = val in ("true", "sim")

                card = self.add_card(
                    story_id=story_id,
                    wave_id=wave_id,
                    title=title,
                    agent=agent,
                    status=status,
                    is_blocked=is_blocked,
                )
                synced_cards.append(card)
            except Exception as e:  # noqa: BLE001
                logger.warning("Erro ao escanear story %s: %s", path, e)

        return synced_cards
