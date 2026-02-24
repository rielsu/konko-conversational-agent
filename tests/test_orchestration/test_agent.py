"""Orchestration: field collection order, correction handling."""

from __future__ import annotations

import asyncio

import pytest

from konko_agent.config.models import AgentConfig, FieldConfig, PersonalityConfig
from konko_agent.infrastructure.llm_client import MockLLMClient
from konko_agent.infrastructure.state_store import InMemoryStateStore
from konko_agent.orchestration.agent import ConversationAgent


@pytest.fixture
def four_field_config() -> AgentConfig:
    return AgentConfig(
        name="Test",
        fields=[
            FieldConfig(name="email", type="email", prompt="Email?"),
            FieldConfig(name="name", type="name", prompt="Name?"),
            FieldConfig(name="phone", type="phone", prompt="Phone?"),
            FieldConfig(name="address", type="address", prompt="Address?"),
        ],
        personality=PersonalityConfig(greeting="Hi", closing="Bye"),
    )


def test_field_collection_order_and_current_field_advances(four_field_config: AgentConfig) -> None:
    """First response provides email -> current_field advances to name."""
    async def run() -> None:
        responses = [
            '{"intent": "field_response", "response_text": "Got your email.", "extracted_value": "alice@example.com", "confidence": 0.95, "field_name": "email"}',
        ]
        mock_llm = MockLLMClient(responses=responses)
        store = InMemoryStateStore()
        agent = ConversationAgent(four_field_config, mock_llm, store)

        out = await agent.handle_message("s1", "alice@example.com")
        assert "Got your email" in out or "email" in out.lower()

        state = await agent.get_state("s1")
        assert state is not None
        assert state.fields["email"].is_collected
        assert state.fields["email"].current_value == "alice@example.com"
        assert state.current_field == "name"

    asyncio.run(run())


def test_correction_adds_field_attempt_with_source_corrected(four_field_config: AgentConfig) -> None:
    """Correction intent adds FieldAttempt with source=corrected."""
    async def run() -> None:
        responses = [
            '{"intent": "field_response", "response_text": "Got it.", "extracted_value": "wrong@old.com", "confidence": 0.8, "field_name": "email"}',
            '{"intent": "correction", "response_text": "Updated.", "extracted_value": "right@new.com", "confidence": 0.95, "field_name": "email"}',
        ]
        mock_llm = MockLLMClient(responses=responses)
        store = InMemoryStateStore()
        agent = ConversationAgent(four_field_config, mock_llm, store)

        await agent.handle_message("s2", "wrong@old.com")
        await agent.handle_message("s2", "Actually it's right@new.com")

        state = await agent.get_state("s2")
        assert state is not None
        assert len(state.fields["email"].attempts) == 2
        assert state.fields["email"].attempts[0].source == "user_provided"
        assert state.fields["email"].attempts[1].source == "corrected"
        assert state.fields["email"].current_value == "right@new.com"

    asyncio.run(run())
