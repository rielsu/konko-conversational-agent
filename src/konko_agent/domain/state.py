"""Conversation and field state models. Append-only FieldAttempt per field."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FieldAttempt(BaseModel):
    """Single attempt to provide or correct a field value."""

    value: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(ge=0.0, le=1.0, description="LLM confidence 0.0-1.0")
    validation_status: str = Field(
        ...,
        description="valid | invalid | pending",
    )
    source: str = Field(
        default="user_provided",
        description="user_provided | corrected",
    )


class FieldState(BaseModel):
    """State for one collectible field: append-only attempts, derived current value."""

    field_name: str
    attempts: list[FieldAttempt] = Field(default_factory=list)

    @property
    def current_value(self) -> str | None:
        """Last valid attempt's value, or None."""
        for a in reversed(self.attempts):
            if a.validation_status == "valid":
                return a.value
        return None

    @property
    def is_collected(self) -> bool:
        """True if there is at least one valid attempt."""
        return self.current_value is not None


class Message(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="user | assistant")
    content: str


class EscalationState(BaseModel):
    """Result of escalation: payload for handoff."""

    reason: str = Field(..., description="e.g. all_fields_collected | user_request")
    fields: dict[str, str] = Field(default_factory=dict, description="field_name -> final value")
    history_summary: str | None = Field(default=None, description="Optional summary of attempts/corrections")


class ConversationState(BaseModel):
    """Full conversation state for one session."""

    session_id: str
    phase: str = Field(..., description="ConversationPhase value (string to avoid circular import at init)")
    messages: list[Message] = Field(default_factory=list)
    fields: dict[str, FieldState] = Field(default_factory=dict)
    current_field: str | None = None
    escalation: EscalationState | None = None
