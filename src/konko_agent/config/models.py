"""Pydantic models for agent configuration. Central contract for IDE and validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# --- Field configuration ---

FieldType = Literal["email", "phone", "name", "address", "custom"]


class FieldConfig(BaseModel):
    """Configuration for a single collectible field."""

    name: str = Field(..., description="Unique field identifier (e.g. email, phone)")
    type: FieldType = Field(..., description="Validation type")
    prompt: str = Field(..., description="What to ask the user for this field")
    required: bool = True
    # For type="custom", validation uses this regex
    validation_regex: str | None = Field(default=None, description="Optional regex for custom type")


# --- Personality ---


class PersonalityConfig(BaseModel):
    """Tone and style of the agent."""

    tone: str = Field(default="friendly", description="e.g. friendly, casual, formal")
    greeting: str = Field(..., description="Initial greeting message")
    closing: str = Field(default="Thank you! We'll be in touch.", description="Message before escalation")
    style: str | None = Field(
        default=None,
        description='Optional style description, e.g. "conversational", "supportive".',
    )
    formality: str | None = Field(
        default=None,
        description='Optional formality level, e.g. "casual", "semi-formal", "formal".',
    )
    use_emojis: bool = Field(
        default=False,
        description="Whether the agent should naturally use emojis.",
    )
    emoji_list: list[str] = Field(
        default_factory=list,
        description="Optional list of emojis the agent may use.",
    )


# --- Escalation ---


class EscalationPolicy(BaseModel):
    """When to escalate: after all fields collected and/or custom triggers."""

    enabled: bool = Field(
        default=True,
        description="Master toggle to enable or disable escalation logic.",
    )
    reason: str | None = Field(
        default=None,
        description="Human-readable description for the default all-fields escalation.",
    )
    after_all_fields: bool = Field(
        default=True,
        description="Escalate once all required fields are collected",
    )
    # Optional: trigger keywords or conditions (e.g. "speak to human")
    trigger_phrases: list[str] = Field(default_factory=list)


# --- Top-level agent config ---


class AgentConfig(BaseModel):
    """Full agent configuration loaded from YAML."""

    name: str = Field(default="Konko Agent", description="Agent display name")
    fields: list[FieldConfig] = Field(..., min_length=1, description="Fields to collect in order")
    personality: PersonalityConfig = Field(..., description="Tone and messages")
    escalation: EscalationPolicy = Field(default_factory=EscalationPolicy)
    # LLM endpoint (optional in config; can be overridden by env)
    llm_base_url: str | None = Field(default=None)
    llm_model: str = Field(default="gpt-4o-mini")
