## Context

 A conversational agent that can collect user data, handle light interruptions, apply corrections, and escalate conversations to a human when appropriate. The research document compares two contrasting implementation plans:

- **Plan 1 (Pragmatic)**: Modular monolith, snapshotting, FSM implicit in conditionals, direct `httpx` usage, dynamic `create_model`.
- **Plan 2 (Ambitious)**: Hexagonal Architecture, Event Sourcing, formal OOP FSM, Semantic Router with embeddings, multi‑agent (Analyst + Architect), C4/ADR generation.

## Comparative Analysis Against the Rubric

| Evaluation Criterion          | Plan 1                                                       | Plan 2                                           | Verdict                                          |
| ----------------------------- | ------------------------------------------------------------ | ------------------------------------------------ | ------------------------------------------------ |
| **Architecture & SoC**  | Blurry separation between logic/orchestration/infrastructure | Oversized for a take‑home assignment            | Neither nails it: balance is missing             |
| **Config & Validation** | Fragile dynamic `create_model`, no IDE support             | Does not define a config schema                  | Both fail here                                   |
| **Agent Behavior**      | Loses history of corrections                                 | Event Sourcing is disproportionate               | Plan 2 is right, Plan 1 is insufficient          |
| **Agentic Patterns**    | Minimal extensibility                                        | Semantic Router violates “no heavy frameworks” | Both are at the extremes                         |
| **Test Quality**        | Easy to test, but implicit FSM makes isolated testing harder | Test infra is complex for multi‑agent           | Plan 1 wins on practicality                      |
| **Code Clarity**        | Risk of spaghetti code                                       | Steep learning curve                             | Plan 1 wins, but only slightly                   |
| **Practical Judgment**  | Does not push far enough                                     | Multi‑agent and C4 are out of scope             | **Decisive criterion**: both miss the mark |

## Recommendation: Hybrid Approach “Structured Simplicity”

Take the **architectural clarity** of Plan 2 (without full hexagonal), the **pragmatism** of Plan 1, and add **selective sophistication** only where the rubric clearly rewards it.

### Key Decisions

| Aspect        | Decision                                                 | Origin              | Justification                                                 |
| ------------- | -------------------------------------------------------- | ------------------- | ------------------------------------------------------------- |
| Structure     | Three layers (config / domain / infra+orchestration)     | Adapted from Plan 2 | Clean SoC without hexagonal overhead                          |
| Abstractions  | `typing.Protocol` for `LLMClient` and `StateStore` | Adapted from Plan 2 | Demonstrates extensibility; enables clean testing             |
| Field state   | Append‑only history of `FieldAttempt` per field       | Simplified Plan 2   | Answers the assignment’s “consider multiple attempts” note |
| State store   | In‑memory dict behind a swappable Protocol              | Plan 1              | Meets constraints; Protocol proves the abstraction            |
| LLM client    | Direct async `httpx`                                   | Plan 1              | No framework dependencies                                     |
| FSM           | `ConversationPhase` enum + pure transition function    | New                 | More explicit than Plan 1, simpler than Plan 2                |
| Config models | Static Pydantic with `list[FieldConfig]`               | New                 | No dynamic `create_model`; better IDE support & validation  |
| Off‑topic    | LLM‑based classification (intent in JSON response)      | New                 | Zero dependencies vs semantic router                          |

### What Is Discarded From Plan 2

- Full Hexagonal Architecture (unnecessary overhead).
- Full Event Sourcing (append‑only attempts give ~80% of the value at ~10% of the cost).
- Semantic Router (needs sentence‑transformers; violates the “no heavy frameworks” constraint).
- Multi‑Agent setup (out of scope for the assignment).
- C4/ADR generation (not relevant for the core assignment).
- Dynamic `create_model` from Plan 1 (fragile, poor IDE support).

## Proposed Architecture

```text
src/konko_agent/
  config/
    models.py          # AgentConfig, FieldConfig, PersonalityConfig, EscalationPolicy (Pydantic)
    loader.py          # Load YAML + validation

  domain/
    state.py           # ConversationState, FieldState, FieldAttempt, Message
    phases.py          # ConversationPhase (Enum) + pure next_phase()
    validators.py      # Validators for email, phone, name, address, custom regex
    escalation.py      # EscalationEvaluator: all-fields-collected + policy triggers
    intent.py          # TurnAnalysis model, Intent enum

  infrastructure/
    llm_client.py      # LLMClient(Protocol) + KonkoLLMClient(httpx) + MockLLMClient
    state_store.py     # StateStore(Protocol) + InMemoryStateStore

  orchestration/
    runtime.py         # AgentRuntime: manages N concurrent sessions
    agent.py           # ConversationAgent: per-turn loop (the core)
    prompt_builder.py  # Assembles system prompt from config + state

  cli.py              # Interactive CLI demo

tests/
  conftest.py          # Fixtures: MockLLMClient, sample configs, factories
  test_config/         # Config validation (malformed YAML, missing fields)
  test_domain/         # State, phases, validators, escalation (no mocks)
  test_orchestration/  # Full conversation flows, multi-session runtime

configs/
  default_agent.yaml   # Standard agent (friendly, semi-formal)
  casual_agent.yaml    # Casual tone with emojis
  minimal_agent.yaml   # Minimal config for testing
```

## State Model 

Sketch of the core state model:

```python
class FieldAttempt(BaseModel):
    value: str
    timestamp: datetime
    confidence: float  # 0.0–1.0 from the LLM
    validation_status: str  # "valid" | "invalid" | "pending"
    source: str  # "user_provided" | "corrected"


class FieldState(BaseModel):
    field_name: str
    attempts: list[FieldAttempt] = []
    # current_value: property -> last valid attempt
    # is_collected: property -> at least one valid attempt exists


class ConversationState(BaseModel):
    session_id: str
    phase: ConversationPhase
    messages: list[Message]
    fields: dict[str, FieldState]
    current_field: str | None
    escalation: EscalationState | None
```

This provides **traceability of corrections** (every attempt is preserved) without the full complexity of Event Sourcing. A correction simply adds a new `FieldAttempt` with `source="corrected"`, and the previous value remains in the history.

## FSM: Enum + Pure Transitions

```python
class ConversationPhase(str, Enum):
    GREETING = "greeting"
    COLLECTING = "collecting"
    ESCALATED = "escalated"
    COMPLETED = "completed"
```

Transitions are encoded in a pure function `next_phase(phase, state) -> phase`, which can be tested in isolation.

## Agent Turn Loop (Pseudocode)

```text
1. Load session state
2. Record the user message
3. Build prompt (personality + current field + collected fields + JSON format)
4. Call the LLM -> obtain TurnAnalysis (intent, extracted value, confidence, response text)
5. Based on intent:
   - field_response: append FieldAttempt, validate
   - correction: append FieldAttempt with source="corrected"
   - escalation_request: mark escalation
   - off_topic: LLM already redirects in its response
6. Evaluate escalation conditions (all_fields OR policy match)
7. Advance current_field to the next not-yet-collected field
8. Record the assistant response
9. Persist state
```

## Testing Strategy

| Category                 | File                                         | What it validates                                     |
| ------------------------ | -------------------------------------------- | ----------------------------------------------------- |
| Config validation errors | `tests/test_config/test_validation.py`     | Malformed YAML, missing fields, invalid types         |
| Field collection order   | `tests/test_orchestration/test_agent.py`   | Sequential order,`current_field` advances correctly |
| Correction handling      | `tests/test_orchestration/test_agent.py`   | New `FieldAttempt` added, `current_value` updated |
| Escalation payload       | `tests/test_domain/test_escalation.py`     | Payload contains fields, history, and correct reason  |
| Phase transitions        | `tests/test_domain/test_phases.py`         | greeting→collecting→escalated, invalid transitions  |
| Session isolation        | `tests/test_orchestration/test_runtime.py` | N concurrent sessions with no state leakage           |

**Principle**: `MockLLMClient` implements the Protocol directly (no `unittest.mock.patch`), returns scripted responses. Tests assert on state and outputs, not on mock call details.

## Cursor/AI Builder Rules and Time Proyections of Implementation

1. **Scaffold** (~30 min): `pyproject.toml`, directory structure, `config/models.py` first (it is the central contract).
2. **Domain** (1–2 hr): `state.py`, `phases.py`, `validators.py`, `escalation.py` — all pure, no I/O, easily testable.
3. **Infrastructure** (~45 min): Protocol definitions + concrete implementations.
4. **Orchestration** (2–3 hr): `prompt_builder` → `agent.py` → `runtime.py` (build incrementally).
5. **Tests** (1.5–2 hr): `conftest` first, then config → domain → orchestration.
6. **Docs + polish** (~45 min): `README`, `DECISIONS.md`, sample YAMLs, CLI.

**Cursor tips**: Generate Pydantic models first (anchor for autocomplete), write signatures/docstrings before bodies to guide AI, and use “Generate from context” for tests once fixtures are in place.

## End-to-End Verification

1. `pytest -v` — full suite passes with clear statistics.
2. `python -m konko_agent.cli --config configs/default_agent.yaml` — interactive conversation.
3. Manual check: greeting → collect 4 fields → correct one → complete → escalation with correct payload.
4. Off-topic behavior: send an irrelevant message, verify redirection.
5. Invalid config: malformed YAML produces a readable validation error.
