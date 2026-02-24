"""Domain state: FieldState current_value, is_collected."""

from __future__ import annotations

from datetime import datetime

import pytest

from konko_agent.domain.state import FieldAttempt, FieldState


def test_field_state_empty_not_collected() -> None:
    fs = FieldState(field_name="email", attempts=[])
    assert fs.current_value is None
    assert fs.is_collected is False


def test_field_state_valid_attempt_collected() -> None:
    fs = FieldState(
        field_name="email",
        attempts=[
            FieldAttempt(
                value="a@b.com",
                timestamp=datetime.utcnow(),
                confidence=0.9,
                validation_status="valid",
                source="user_provided",
            ),
        ],
    )
    assert fs.current_value == "a@b.com"
    assert fs.is_collected is True


def test_field_state_last_valid_is_current_value() -> None:
    fs = FieldState(
        field_name="email",
        attempts=[
            FieldAttempt(value="old@x.com", timestamp=datetime.utcnow(), confidence=0.9, validation_status="valid", source="user_provided"),
            FieldAttempt(value="bad", timestamp=datetime.utcnow(), confidence=0.5, validation_status="invalid", source="user_provided"),
            FieldAttempt(value="new@y.com", timestamp=datetime.utcnow(), confidence=0.95, validation_status="valid", source="corrected"),
        ],
    )
    assert fs.current_value == "new@y.com"
    assert fs.is_collected is True
