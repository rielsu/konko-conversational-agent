"""LLM turn analysis: intent and extracted value."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Intent(str, Enum):
    """User intent for this turn."""

    FIELD_RESPONSE = "field_response"
    CORRECTION = "correction"
    ESCALATION_REQUEST = "escalation_request"
    OFF_TOPIC = "off_topic"


class TurnAnalysis(BaseModel):
    """Structured output from LLM for one turn."""

    intent: Intent
    response_text: str = Field(..., description="Text to show the user")
    extracted_value: str | None = Field(default=None, description="For field_response/correction")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    field_name: str | None = Field(default=None, description="Which field this value is for")
