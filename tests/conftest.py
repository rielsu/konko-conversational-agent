"""Pytest fixtures: MockLLMClient, example configs, state factories."""

from __future__ import annotations

from pathlib import Path

import pytest

from konko_agent.config.models import (
    AgentConfig,
    EscalationPolicy,
    FieldConfig,
    PersonalityConfig,
)
from konko_agent.domain.phases import ConversationPhase
from konko_agent.domain.state import (
    ConversationState,
    FieldState,
    Message,
)
from konko_agent.infrastructure.llm_client import MockLLMClient
from konko_agent.infrastructure.state_store import InMemoryStateStore


@pytest.fixture
def minimal_config() -> AgentConfig:
    """Minimal valid config for tests."""
    return AgentConfig(
        name="TestAgent",
        fields=[
            FieldConfig(name="email", type="email", prompt="Your email?"),
            FieldConfig(name="name", type="name", prompt="Your name?"),
        ],
        personality=PersonalityConfig(
            tone="friendly",
            greeting="Hi! I need a couple of details.",
            closing="Thanks!",
        ),
        escalation=EscalationPolicy(after_all_fields=True),
    )


@pytest.fixture
def mock_llm() -> MockLLMClient:
    """Mock LLM that returns default off_topic until scripted responses are set."""
    return MockLLMClient()


@pytest.fixture
def state_store() -> InMemoryStateStore:
    return InMemoryStateStore()


@pytest.fixture
def sample_state() -> ConversationState:
    """Conversation state in COLLECTING phase with one message."""
    return ConversationState(
        session_id="test-session",
        phase=ConversationPhase.COLLECTING.value,
        messages=[
            Message(role="user", content="alice@example.com"),
            Message(role="assistant", content="Got it. What's your name?"),
        ],
        fields={
            "email": FieldState(field_name="email", attempts=[]),
            "name": FieldState(field_name="name", attempts=[]),
        },
        current_field="name",
        escalation=None,
    )


@pytest.fixture
def configs_dir() -> Path:
    """Path to configs directory (may not exist in tests)."""
    return Path(__file__).resolve().parent.parent / "configs"
