"""Conversation agent: single-turn loop (load, LLM, apply intent, persist)."""

from __future__ import annotations

import json
from datetime import datetime

from konko_agent.config.models import AgentConfig
from konko_agent.domain.escalation import evaluate_escalation
from konko_agent.domain.intent import Intent, TurnAnalysis
from konko_agent.domain.phases import ConversationPhase, next_phase
from konko_agent.domain.state import (
    ConversationState,
    EscalationState,
    FieldAttempt,
    FieldState,
    Message,
)
from konko_agent.domain.validators import validate_field
from konko_agent.orchestration.prompt_builder import (
    build_system_prompt,
    build_user_message_for_turn,
)


def _parse_turn_response(raw: str) -> TurnAnalysis:
    """Parse LLM response into TurnAnalysis. On failure return off_topic."""
    raw = raw.strip()
    # Strip markdown code block if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    try:
        data = json.loads(raw)
        return TurnAnalysis.model_validate(data)
    except (json.JSONDecodeError, Exception):
        return TurnAnalysis(
            intent=Intent.OFF_TOPIC,
            response_text=raw or "I didn't understand. Could you rephrase?",
            confidence=0.0,
        )


def _required_field_names(config: AgentConfig) -> list[str]:
    return [f.name for f in config.fields if f.required]


def _next_field_to_collect(state: ConversationState, config: AgentConfig) -> str | None:
    """First field in config order that is not yet collected."""
    for f in config.fields:
        fs = state.fields.get(f.name)
        if not fs or not fs.is_collected:
            return f.name
    return None


def _ensure_fields_from_config(state: ConversationState, config: AgentConfig) -> None:
    """Ensure state.fields has an entry for each config field (mutation)."""
    for f in config.fields:
        if f.name not in state.fields:
            state.fields[f.name] = FieldState(field_name=f.name)


class ConversationAgent:
    """One agent instance: config + LLM client + state store. Handles one turn at a time."""

    def __init__(
        self,
        config: AgentConfig,
        llm_client: object,  # LLMClient protocol
        state_store: object,  # StateStore protocol
    ) -> None:
        self.config = config
        self._llm = llm_client
        self._store = state_store

    async def start_session(self, session_id: str) -> str:
        """
        Initialize a new session if it does not exist yet, append the greeting,
        persist state, and return the greeting text.
        """
        state = await self._store.get(session_id)
        if state is None:
            state = _initial_state(session_id)
            _ensure_fields_from_config(state, self.config)
            state.current_field = _next_field_to_collect(state, self.config)
            greeting = self.config.personality.greeting
            state.messages.append(Message(role="assistant", content=greeting))
            await self._store.set(session_id, state)
            return greeting

        # Session already exists; just return configured greeting.
        return self.config.personality.greeting

    async def handle_message(self, session_id: str, user_message: str) -> str:
        """
        Process one user message: load state, run turn loop, persist, return assistant reply.
        """
        state = await self._store.get(session_id)
        if state is None:
            state = _initial_state(session_id)
            _ensure_fields_from_config(state, self.config)
            state.current_field = _next_field_to_collect(state, self.config)
            await self._store.set(session_id, state)

        state.messages.append(Message(role="user", content=user_message))
        _ensure_fields_from_config(state, self.config)

        system_prompt = build_system_prompt(self.config, state)
        user_text = build_user_message_for_turn(state)
        raw = await self._llm.complete(system_prompt, user_text)
        analysis = _parse_turn_response(raw)
        if analysis.intent == Intent.FIELD_RESPONSE and analysis.extracted_value is not None:
            field_name = analysis.field_name or state.current_field
            if field_name and field_name in state.fields:
                cfg = next((f for f in self.config.fields if f.name == field_name), None)
                if cfg:
                    field_state = state.fields[field_name]
                    if field_state.is_collected:
                       
                        next_field = _next_field_to_collect(state, self.config)
                        if next_field and next_field != field_name:
                            next_cfg = next(
                                (f for f in self.config.fields if f.name == next_field),
                                None,
                            )
                            if next_cfg:
                                analysis.response_text = (
                                    analysis.response_text
                                    or f"I already have your {field_name}. {next_cfg.prompt}"
                                )      
                    else:
                        ok, _ = validate_field(
                            analysis.extracted_value,
                            cfg.type,
                            cfg.validation_regex,
                        )
                        status = "valid" if ok else "invalid"
                        field_state.attempts.append(
                            FieldAttempt(
                                value=analysis.extracted_value,
                                timestamp=datetime.utcnow(),
                                confidence=analysis.confidence,
                                validation_status=status,
                                source="user_provided",
                            )
                        )

        elif analysis.intent == Intent.CORRECTION and analysis.extracted_value is not None:
            field_name = analysis.field_name or state.current_field
            if field_name and field_name in state.fields:
                cfg = next((f for f in self.config.fields if f.name == field_name), None)
                if cfg:
                    ok, _ = validate_field(
                        analysis.extracted_value,
                        cfg.type,
                        cfg.validation_regex,
                    )
                    state.fields[field_name].attempts.append(
                        FieldAttempt(
                            value=analysis.extracted_value,
                            timestamp=datetime.utcnow(),
                            confidence=analysis.confidence,
                            validation_status="valid" if ok else "invalid",
                            source="corrected",
                        )
                    )

        elif analysis.intent == Intent.ESCALATION_REQUEST:
            pass  # escalation evaluated below

        # Evaluate escalation (may set state.escalation)
        if state.escalation is None:
            state.escalation = evaluate_escalation(
                state,
                self.config,
                user_message.lower(),
            )

        required = _required_field_names(self.config)
        phase = ConversationPhase(state.phase)
        next_p = next_phase(phase, state, required)
        state.phase = next_p.value

        # If we have escalated, prefer a deterministic closing over the model's reply.
        if state.escalation is not None and state.phase == ConversationPhase.ESCALATED.value:
            analysis.response_text = self.config.personality.closing

        state.current_field = _next_field_to_collect(state, self.config)

        state.messages.append(Message(role="assistant", content=analysis.response_text))
        await self._store.set(session_id, state)

        return analysis.response_text

    async def get_state(self, session_id: str) -> ConversationState | None:
        """Return current state for session (e.g. for CLI display)."""
        return await self._store.get(session_id)


def _initial_state(session_id: str) -> ConversationState:
    return ConversationState(
        session_id=session_id,
        phase=ConversationPhase.GREETING.value,
        messages=[],
        fields={},
        current_field=None,
        escalation=None,
    )
