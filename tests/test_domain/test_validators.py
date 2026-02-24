"""Validators: email, phone, name, address, custom."""

from __future__ import annotations

import pytest

from konko_agent.domain.validators import (
    validate_email,
    validate_phone,
    validate_name,
    validate_address,
    validate_custom,
    validate_field,
)


def test_validate_email_accepts_valid() -> None:
    ok, msg = validate_email("alice@example.com")
    assert ok is True
    assert msg == ""


def test_validate_email_rejects_invalid() -> None:
    ok, msg = validate_email("notanemail")
    assert ok is False
    assert "email" in msg.lower()


def test_validate_phone_accepts_valid() -> None:
    ok, _ = validate_phone("+1 555-123-4567")
    assert ok is True


def test_validate_phone_rejects_too_short() -> None:
    ok, msg = validate_phone("123")
    assert ok is False
    assert "digit" in msg.lower() or "valid" in msg.lower()


def test_validate_name_accepts_valid() -> None:
    ok, _ = validate_name("Alice Smith")
    assert ok is True


def test_validate_name_rejects_empty() -> None:
    ok, msg = validate_name("   ")
    assert ok is False


def test_validate_address_accepts_long_enough() -> None:
    ok, _ = validate_address("123 Main St")
    assert ok is True


def test_validate_custom_with_regex() -> None:
    ok, _ = validate_custom("ABC123", r"^[A-Z]+\d+$")
    assert ok is True
    ok2, _ = validate_custom("invalid", r"^[A-Z]+\d+$")
    assert ok2 is False


def test_validate_field_dispatches() -> None:
    ok, _ = validate_field("alice@example.com", "email")
    assert ok is True
    ok2, _ = validate_field("alice@example.com", "phone")
    assert ok2 is False
