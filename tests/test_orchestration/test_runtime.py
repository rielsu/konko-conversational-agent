"""Runtime: session isolation (N concurrent sessions, no state leakage)."""

from __future__ import annotations

import asyncio

import pytest

from konko_agent.config.models import AgentConfig, FieldConfig, PersonalityConfig
from konko_agent.infrastructure.llm_client import MockLLMClient
from konko_agent.infrastructure.state_store import InMemoryStateStore
from konko_agent.orchestration.runtime import AgentRuntime


@pytest.fixture
def runtime() -> AgentRuntime:
    config = AgentConfig(
        name="R",
        fields=[FieldConfig(name="email", type="email", prompt="Email?")],
        personality=PersonalityConfig(greeting="Hi", closing="Bye"),
    )
    return AgentRuntime(config, MockLLMClient(), InMemoryStateStore())


def test_session_isolation(runtime: AgentRuntime) -> None:
    """Two sessions do not share state."""
    async def run() -> None:
        mock = MockLLMClient(
            responses=[
                '{"intent": "field_response", "response_text": "Got A.", "extracted_value": "a@a.com", "confidence": 1.0, "field_name": "email"}',
                '{"intent": "field_response", "response_text": "Got B.", "extracted_value": "b@b.com", "confidence": 1.0, "field_name": "email"}',
            ]
        )
        config = AgentConfig(
            name="R",
            fields=[FieldConfig(name="email", type="email", prompt="Email?")],
            personality=PersonalityConfig(greeting="Hi", closing="Bye"),
        )
        store = InMemoryStateStore()
        rt = AgentRuntime(config, mock, store)

        await rt.handle_message("session-1", "a@a.com")
        await rt.handle_message("session-2", "b@b.com")

        state1 = await rt.get_state("session-1")
        state2 = await rt.get_state("session-2")
        assert state1 is not None and state2 is not None
        assert state1.session_id == "session-1"
        assert state2.session_id == "session-2"
        assert state1.fields["email"].current_value == "a@a.com"
        assert state2.fields["email"].current_value == "b@b.com"

    asyncio.run(run())


def test_start_session_adds_greeting_message() -> None:
    """start_session should create state with an initial assistant greeting."""

    async def run() -> None:
        config = AgentConfig(
            name="R",
            fields=[FieldConfig(name="email", type="email", prompt="Email?")],
            personality=PersonalityConfig(greeting="Hi", closing="Bye"),
        )
        rt = AgentRuntime(config, MockLLMClient(), InMemoryStateStore())

        greeting = await rt.start_session("s-greet")
        assert greeting == config.personality.greeting

        state = await rt.get_state("s-greet")
        assert state is not None
        # First message should be the assistant greeting
        assert len(state.messages) == 1
        assert state.messages[0].role == "assistant"
        assert state.messages[0].content == greeting

    asyncio.run(run())
