"""Pure validators for field types: email, phone, name, address, custom regex. No I/O."""

from __future__ import annotations

import re
from typing import Literal

# Simple patterns; can be tightened per requirements
EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_RE = re.compile(r"^[\d\s\-\+\(\)]{10,20}$")
# Name: non-empty, reasonable length, allows letters spaces hyphens apostrophes
NAME_RE = re.compile(r"^[\w\s\-']{1,120}$", re.UNICODE)
# Address: non-empty, flexible
ADDRESS_RE = re.compile(r"^.+\d.*$")  # simplistic: has some digits (street number)


def validate_email(value: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    v = value.strip()
    if not v:
        return False, "Email is required."
    if not EMAIL_RE.match(v):
        return False, "Please enter a valid email address."
    return True, ""


def validate_phone(value: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    v = value.strip()
    if not v:
        return False, "Phone number is required."
    digits = re.sub(r"\D", "", v)
    if len(digits) < 10:
        return False, "Please enter a valid phone number (at least 10 digits)."
    if not PHONE_RE.match(v):
        return False, "Please enter a valid phone number."
    return True, ""


def validate_name(value: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    v = value.strip()
    if not v:
        return False, "Name is required."
    if not NAME_RE.match(v):
        return False, "Please enter a valid name."
    return True, ""


def validate_address(value: str) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    v = value.strip()
    if not v:
        return False, "Address is required."
    if len(v) < 5:
        return False, "Please enter a complete address."
    return True, ""


def validate_custom(value: str, pattern: str | None) -> tuple[bool, str]:
    """Validate with optional regex. If no pattern, accept non-empty."""
    v = value.strip()
    if not v:
        return False, "This field is required."
    if pattern:
        try:
            if not re.match(pattern, v):
                return False, "Invalid format."
        except re.error:
            return False, "Validation error."
    return True, ""


FieldType = Literal["email", "phone", "name", "address", "custom"]


def validate_field(value: str, field_type: FieldType, validation_regex: str | None = None) -> tuple[bool, str]:
    """Dispatch to the right validator by field type."""
    if field_type == "email":
        return validate_email(value)
    if field_type == "phone":
        return validate_phone(value)
    if field_type == "name":
        return validate_name(value)
    if field_type == "address":
        return validate_address(value)
    if field_type == "custom":
        return validate_custom(value, validation_regex)
    return False, f"Unknown field type: {field_type}"
