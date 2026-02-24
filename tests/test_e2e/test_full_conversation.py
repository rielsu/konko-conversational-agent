"""End-to-end conversation test: greeting, sequential collection, correction, escalation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from konko_agent.config.loader import load_config
from konko_agent.infrastructure.llm_client import MockLLMClient
from konko_agent.infrastructure.state_store import InMemoryStateStore
from konko_agent.orchestration.runtime import AgentRuntime
from konko_agent.domain.phases import ConversationPhase


def test_full_conversation_e2e() -> None:
    """Exercise a full conversation including correction and escalation."""

    async def run() -> None:
        root = Path(__file__).resolve().parent.parent.parent
        config_path = root / "configs" / "default_agent.yaml"
        config = load_config(config_path)

        # Script LLM responses for each turn.
        responses = [
            # Turn 1: email
            '{"intent": "field_response", "response_text": "Got your email.", '
            '"extracted_value": "alice@example.com", "confidence": 0.95, "field_name": "email"}',
            # Turn 2: name
            '{"intent": "field_response", "response_text": "Thanks, Alice.", '
            '"extracted_value": "Alice", "confidence": 0.95, "field_name": "name"}',
            # Turn 3: phone
            '{"intent": "field_response", "response_text": "Phone saved.", '
            '"extracted_value": "+1 555 123 4567", "confidence": 0.95, "field_name": "phone"}',
            # Turn 4: correction to email
            '{"intent": "correction", "response_text": "Updated your email.", '
            '"extracted_value": "alice+new@example.com", "confidence": 0.99, "field_name": "email"}',
            # Turn 5: address
            '{"intent": "field_response", "response_text": "Address stored.", '
            '"extracted_value": "123 Main St", "confidence": 0.95, "field_name": "address"}',
        ]

        mock_llm = MockLLMClient(responses=responses)
        store = InMemoryStateStore()
        runtime = AgentRuntime(config, mock_llm, store)

        session_id = "e2e-session"

        # Start session and verify greeting
        greeting = await runtime.start_session(session_id)
        assert greeting == config.personality.greeting

        # Simulate user turns
        await runtime.handle_message(session_id, "alice@example.com")
        await runtime.handle_message(session_id, "Alice")
        await runtime.handle_message(session_id, "+1 555 123 4567")
        await runtime.handle_message(session_id, "Actually it's alice+new@example.com")
        await runtime.handle_message(session_id, "123 Main St")

        state = await runtime.get_state(session_id)
        assert state is not None

        # First message should be greeting from start_session
        assert state.messages[0].role == "assistant"
        assert state.messages[0].content == greeting

        # Email field should reflect corrected value, with multiple attempts.
        email_state = state.fields["email"]
        assert len(email_state.attempts) >= 2
        assert email_state.current_value == "alice+new@example.com"

        # All required fields should be collected.
        for field_cfg in config.fields:
            if field_cfg.required:
                assert state.fields[field_cfg.name].is_collected

        # Escalation should have fired after all required fields were collected.
        assert state.escalation is not None
        assert state.escalation.fields["email"] == "alice+new@example.com"
        assert state.escalation.fields["name"] == "Alice"
        assert state.escalation.fields["phone"] == "+1 555 123 4567"
        assert state.escalation.fields["address"] == "123 Main St"

        # Phase should be ESCALATED.
        assert state.phase == ConversationPhase.ESCALATED.value

    asyncio.run(run())

