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
    ) -> dict[str, Any]:
        """Registra um novo card de story no Kanban."""
        self.db.save_kanban_card(
            story_id=story_id,
            wave_id=wave_id,
            title=title,
            agent=agent,
            status=status,
            reviews=reviews or {},
        )
        return self.get_card(story_id) or {
            "story_id": story_id,
            "wave_id": wave_id,
            "title": title,
            "agent": agent,
            "status": status,
            "reviews": reviews or {},
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
        }

    def get_card(self, story_id: str) -> dict[str, Any] | None:
        """Recupera um card pelo ID."""
        return self.db.get_kanban_card(story_id)

    def list_cards(self, wave_id: str | None = None) -> list[dict[str, Any]]:
        """Lista cards cadastrados na ONDA."""
        return self.db.list_kanban_cards(wave_id=wave_id)

    def sync_markdown_file(self, story_id: str, new_status: str) -> bool:
        """Atualiza a linha de status no arquivo markdown correspondente."""
        if not self.stories_dir.exists():
            return False

        # Procura arquivos que iniciem com o story_id
        for path in self.stories_dir.glob(f"{story_id}*.md"):
            try:
                content = path.read_text(encoding="utf-8")
                # Substitui > **Status:** ... por > **Status:** <new_status>
                updated = re.sub(
                    r">\s*\*\*Status:\*\*.*",
                    f"> **Status:** {new_status}",
                    content,
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

                card = self.add_card(
                    story_id=story_id,
                    wave_id=wave_id,
                    title=title,
                    agent=agent,
                    status=status,
                )
                synced_cards.append(card)
            except Exception as e:  # noqa: BLE001
                logger.warning("Erro ao escanear story %s: %s", path, e)

        return synced_cards
