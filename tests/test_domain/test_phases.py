"""Phase transitions: greeting -> collecting -> escalated/completed."""

from __future__ import annotations

from datetime import datetime

import pytest

from konko_agent.domain.phases import ConversationPhase, next_phase
from konko_agent.domain.state import (
    ConversationState,
    EscalationState,
    FieldAttempt,
    FieldState,
)


def _state(
    phase: str,
    fields: dict[str, FieldState],
    escalation: EscalationState | None = None,
) -> ConversationState:
    return ConversationState(
        session_id="s",
        phase=phase,
        messages=[],
        fields=fields,
        current_field=None,
        escalation=escalation,
    )


def test_greeting_goes_to_collecting() -> None:
    state = _state(ConversationPhase.GREETING.value, {})
    next_p = next_phase(ConversationPhase.GREETING, state, ["email", "name"])
    assert next_p == ConversationPhase.COLLECTING


def test_collecting_with_escalation_goes_to_escalated() -> None:
    state = _state(
        ConversationPhase.COLLECTING.value,
        {},
        escalation=EscalationState(reason="user_request", fields={}),
    )
    next_p = next_phase(ConversationPhase.COLLECTING, state, ["email"])
    assert next_p == ConversationPhase.ESCALATED


def test_collecting_all_required_collected_goes_to_completed() -> None:
    state = _state(
        ConversationPhase.COLLECTING.value,
        {
            "email": FieldState(field_name="email", attempts=[]),
            "name": FieldState(field_name="name", attempts=[]),
        },
        escalation=None,
    )
    state.fields["email"].attempts.append(
        FieldAttempt(value="a@b.com", timestamp=datetime.utcnow(), confidence=1.0, validation_status="valid", source="user_provided")
    )
    state.fields["name"].attempts.append(
        FieldAttempt(value="Alice", timestamp=datetime.utcnow(), confidence=1.0, validation_status="valid", source="user_provided")
    )
    next_p = next_phase(ConversationPhase.COLLECTING, state, ["email", "name"])
    assert next_p == ConversationPhase.COMPLETED


def test_collecting_not_all_collected_stays_collecting() -> None:
    state = _state(
        ConversationPhase.COLLECTING.value,
        {
            "email": FieldState(field_name="email", attempts=[]),
            "name": FieldState(field_name="name", attempts=[]),
        },
    )
    state.fields["email"].attempts.append(
        FieldAttempt(value="a@b.com", timestamp=datetime.utcnow(), confidence=1.0, validation_status="valid", source="user_provided")
    )
    next_p = next_phase(ConversationPhase.COLLECTING, state, ["email", "name"])
    assert next_p == ConversationPhase.COLLECTING


def test_escalated_stays_escalated() -> None:
    state = _state(ConversationPhase.ESCALATED.value, {}, escalation=EscalationState(reason="done", fields={}))
    next_p = next_phase(ConversationPhase.ESCALATED, state, [])
    assert next_p == ConversationPhase.ESCALATED
