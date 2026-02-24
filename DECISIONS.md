# DECISIONS.md

Architecture and design decisions for the Konko Agent 

## 1. Layered structure or Hexagonal?

- **Decision**: Three logical layers — config, domain, infrastructure+orchestration — without full hexagonal (ports/adapters) overhead.
- **Rationale**: Clear separation of concerns and testability without the boilerplate of formal hexagon. Domain has no I/O; infra implements Protocol; orchestration wires config + domain + infra.

## 2. Protocol-based LLM and state

- **Decision**: `LLMClient` and `StateStore` are `typing.Protocol`; implementations: `KonkoLLMClient` (httpx), `InMemoryStateStore`, `MockLLMClient`.
- **Rationale**: Extensibility and testing without framework lock-in. Tests use `MockLLMClient` with scripted responses; no `unittest.mock.patch` on network.

## 3. Append-only FieldAttempt, no Event Sourcing

- **Decision**: Each field has `FieldState.attempts: list[FieldAttempt]`. Corrections append a new attempt with `source="corrected"`. No full event store or replay.
- **Rationale**: Traces corrections and multiple attempts at low cost; avoids Event Sourcing complexity.

## 4. FSM: Enum + pure function

- **Decision**: `ConversationPhase` enum and pure `next_phase(phase, state, required_field_names)`.
- **Rationale**: More explicit than ad-hoc conditionals (Plan 1), simpler than OOP FSM (Plan 2). Easy to unit-test transitions in isolation.

## 5. Static Pydantic config

- **Decision**: Fixed models (`AgentConfig`, `FieldConfig`, `PersonalityConfig`, `EscalationPolicy`); YAML loaded and validated into these.
- **Rationale**: IDE support and validation; no fragile dynamic `create_model`. Config is the central contract.

## 6. LLM for off-topic, no Semantic Router

- **Decision**: Off-topic and intent classification via LLM response (JSON with `intent`, `response_text`, etc.). No sentence-transformers or Semantic Router.
- **Rationale**: Keeps dependencies minimal and respects "no heavy frameworks."

## 7. Single agent, in-memory store

- **Decision**: One conversational agent; state store is in-memory by default. No multi-agent (Analyst/Architect), no C4/ADR generation.
- **Rationale**: Scope aligned with the assignment; Protocol allows swapping to a persistent store later.

## 8. Turn loop responsibility

- **Decision**: Agent: load state → append user message → build prompt → LLM → parse TurnAnalysis → apply intent (add attempts, set escalation) → evaluate escalation → next_phase → advance current_field → append assistant message → persist.
- **Rationale**: Single place for turn logic; escalation evaluation uses domain `evaluate_escalation`; phase transition uses `next_phase` with required field names from config.

## 9. Enriched personality and escalation configuration

- **Decision**: Extend `PersonalityConfig` (tone, style, formality, emoji usage, emoji list) and `EscalationPolicy` (enabled, reason, after_all_fields, trigger_phrases) to better mirror the assignment's configuration requirements.
- **Rationale**: Keeps the core logic simple while giving callers more precise control over tone, emoji usage, and how escalation is described and toggled via config.

## 10. Greeting via runtime `start_session`

- **Decision**: Introduce `AgentRuntime.start_session(session_id)` / `ConversationAgent.start_session` to create initial state, populate fields, append the configured greeting as an assistant message, and persist it before any user input.
- **Rationale**: Ensures every conversation (CLI or other integration) consistently begins with the configured greeting, and that the greeting is part of the persisted conversation state for observability and testing.

## 11. End-to-end testing

- **Decision**: Add an E2E test (`tests/test_e2e/test_full_conversation.py`) that drives `AgentRuntime` with `MockLLMClient` through greeting, sequential field collection, correction, and escalation.
- **Rationale**: Complements unit and orchestration tests by validating the full flow and state transitions using the same public APIs that an integration would use.
