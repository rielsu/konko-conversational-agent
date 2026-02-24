"""Conversation FSM: enum and pure transition function."""

from __future__ import annotations

from enum import Enum

from konko_agent.domain.state import ConversationState


class ConversationPhase(str, Enum):
    """Conversation lifecycle phases."""

    GREETING = "greeting"
    COLLECTING = "collecting"
    ESCALATED = "escalated"
    COMPLETED = "completed"


def next_phase(
    phase: ConversationPhase,
    state: ConversationState,
    required_field_names: list[str],
) -> ConversationPhase:
    """
    Pure transition: given current phase, state, and list of required field names,
    return the next phase. Testable in isolation without I/O.
    """
    if phase == ConversationPhase.GREETING:
        return ConversationPhase.COLLECTING

    if phase == ConversationPhase.COLLECTING:
        if state.escalation is not None:
            return ConversationPhase.ESCALATED
        if _all_required_fields_collected(state, required_field_names):
            return ConversationPhase.COMPLETED
        return ConversationPhase.COLLECTING

    if phase == ConversationPhase.ESCALATED:
        return ConversationPhase.ESCALATED

    if phase == ConversationPhase.COMPLETED:
        return ConversationPhase.COMPLETED

    return phase


def _all_required_fields_collected(state: ConversationState, required_field_names: list[str]) -> bool:
    """True if every required field has at least one valid attempt."""
    if not required_field_names:
        return True
    return all(
        state.fields.get(name) and state.fields[name].is_collected
        for name in required_field_names
    )
