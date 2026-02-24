"""State store: Protocol + in-memory implementation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from konko_agent.domain.state import ConversationState


@runtime_checkable
class StateStore(Protocol):
    """Protocol for persisting and loading conversation state per session."""

    async def get(self, session_id: str) -> ConversationState | None:
        """Load state for session. Return None if not found."""
        ...

    async def set(self, session_id: str, state: ConversationState) -> None:
        """Persist state for session."""
        ...


class InMemoryStateStore:
    """In-memory dict store. Suitable for single process; no persistence."""

    def __init__(self) -> None:
        self._store: dict[str, ConversationState] = {}

    async def get(self, session_id: str) -> ConversationState | None:
        return self._store.get(session_id)

    async def set(self, session_id: str, state: ConversationState) -> None:
        self._store[session_id] = state
