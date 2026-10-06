"""Porta de persistência do domínio de Sessão (Session Repository Interface)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Message, Part, Session


class SessionRepositoryInterface(ABC):
    """Contrato abstrato para persistência de sessões, mensagens e partes."""

    @abstractmethod
    def save_session(self, session: Session) -> None:
        """Salva ou atualiza os metadados de uma sessão."""

    @abstractmethod
    def load_session(self, session_id: str) -> Session:
        """Carrega uma sessão por ID."""

    @abstractmethod
    def list_sessions(self) -> list[Session]:
        """Lista todas as sessões ativas."""

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Remove uma sessão."""

    @abstractmethod
    def save_message(self, message: Message) -> None:
        """Persiste uma mensagem."""

    @abstractmethod
    def load_messages(self, session_id: str) -> list[Message]:
        """Recupera mensagens de uma sessão."""

    @abstractmethod
    def save_part(self, session_id: str, part: Part) -> None:
        """Persiste uma parte de mensagem."""

    @abstractmethod
    def load_parts(self, session_id: str) -> list[Part]:
        """Recupera todas as partes associadas a uma sessão."""
