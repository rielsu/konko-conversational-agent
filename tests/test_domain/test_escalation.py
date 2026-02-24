"""Escalation: payload contains fields, history, reason."""

from __future__ import annotations

from datetime import datetime

import pytest

from konko_agent.config.models import AgentConfig, EscalationPolicy, FieldConfig, PersonalityConfig
from konko_agent.domain.escalation import evaluate_escalation
from konko_agent.domain.state import ConversationState, FieldState, FieldAttempt


def _config(
    trigger_phrases: list[str] | None = None,
    enabled: bool = True,
    reason: str | None = None,
) -> AgentConfig:
    return AgentConfig(
        name="E",
        fields=[
            FieldConfig(name="email", type="email", prompt="Email?", required=True),
            FieldConfig(name="name", type="name", prompt="Name?", required=True),
        ],
        personality=PersonalityConfig(greeting="Hi", closing="Bye"),
        escalation=EscalationPolicy(
            enabled=enabled,
            reason=reason,
            after_all_fields=True,
            trigger_phrases=trigger_phrases or [],
        ),
    )


def _state_with_collected() -> ConversationState:
    def make_collected(name: str, value: str) -> FieldState:
        return FieldState(
            field_name=name,
            attempts=[
                FieldAttempt(value=value, timestamp=datetime.utcnow(), confidence=1.0, validation_status="valid", source="user_provided"),
            ],
        )
    return ConversationState(
        session_id="s",
        phase="collecting",
        messages=[],
        fields={
            "email": make_collected("email", "a@b.com"),
            "name": make_collected("name", "Alice"),
        },
        current_field=None,
        escalation=None,
    )


def test_escalation_after_all_fields_collected() -> None:
    config = _config()
    state = _state_with_collected()
    result = evaluate_escalation(state, config, "ok")
    assert result is not None
    assert result.reason == "all_fields_collected"
    assert result.fields.get("email") == "a@b.com"
    assert result.fields.get("name") == "Alice"


def test_no_escalation_when_not_all_collected() -> None:
    config = _config()
    state = _state_with_collected()
    state.fields["name"].attempts.clear()
    result = evaluate_escalation(state, config, "ok")
    assert result is None


def test_escalation_trigger_phrase() -> None:
    config = _config(trigger_phrases=["speak to human", "agent"])
    state = _state_with_collected()
    state.fields["name"].attempts.clear()
    result = evaluate_escalation(state, config, "I want to speak to human please")
    assert result is not None
    assert result.reason == "user_request"


def test_escalation_disabled_even_when_all_fields_collected() -> None:
    config = _config(enabled=False)
    state = _state_with_collected()
    result = evaluate_escalation(state, config, "ok")
    assert result is None


def test_escalation_uses_configured_reason() -> None:
    custom_reason = "All required fields collected"
    config = _config(reason=custom_reason)
    state = _state_with_collected()
    result = evaluate_escalation(state, config, "ok")
    assert result is not None
    assert result.reason == custom_reason
