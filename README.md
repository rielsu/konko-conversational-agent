
# Konko Agent

Conversational data-collection agent for Konko AI: collects user fields (email, name, phone, address), handles corrections, off-topic redirection, and escalation with a structured yet simple architecture.

## Features

- **Structured Simplicity**: Three layers (config / domain / infrastructure+orchestration) without hexagonal overhead
- **Correction history**: Append-only `FieldAttempt` per field; corrections add a new attempt with `source="corrected"` without losing history
- **Explicit FSM**: `ConversationPhase` enum (GREETING → COLLECTING → ESCALATED/COMPLETED) and pure `next_phase(phase, state, required_fields)`
- **Protocol-based infra**: `LLMClient` and `StateStore` as `typing.Protocol` for easy mocking and swapping
- **Static config**: Pydantic models (`AgentConfig`, `FieldConfig`, etc.) loaded from YAML; no dynamic `create_model`

## Requirements

- Python 3.11+
- Dependencies: `pydantic`, `httpx`, `pyyaml`

## Install

```bash
pip install -e ".[dev]"
```

## Run interactive CLI

```bash
export OPENAI_API_KEY=your_key   # or set OPENAI_BASE_URL for another endpoint
python -m konko_agent.cli --config configs/default_agent.yaml
```

Or with the entry point (after install):

```bash
konko-agent -c configs/default_agent.yaml
```

## Config

YAML files in `configs/` define:

- **fields**: list of `name`, `type` (email, phone, name, address, custom), `prompt`, `required`, optional `validation_regex` for custom
- **personality**:
  - `tone`: high-level voice (friendly, neutral, etc.)
  - `style`: free-form description (e.g. conversational, supportive)
  - `formality`: casual / semi-formal / formal
  - `use_emojis`: whether the agent should naturally use emojis
  - `emoji_list`: optional list of emojis it may draw from
  - `greeting`: message shown at the start of a new conversation
  - `closing`: message used before escalation/completion
- **escalation**:
  - `enabled`: master toggle for escalation logic
  - `reason`: human-readable description for the default all-fields escalation
  - `after_all_fields`: whether to escalate automatically once required fields are collected
  - `trigger_phrases`: list of phrases that should trigger escalation on demand

Example: see `configs/default_agent.yaml`, `configs/casual_agent.yaml`, `configs/minimal_agent.yaml`.

## Tests

```bash
PYTHONPATH=src pytest -v
# or after install
pytest -v
```

- **test_config**: YAML validation, missing/invalid fields, personality optional fields
- **test_domain**: state, phases, validators, escalation (including enabled/disabled and configured reasons)
- **test_orchestration**: agent turn loop (field order, corrections), runtime session isolation, greeting behavior
- **test_e2e**: full multi-turn conversation (greeting, collection, correction, escalation) via `AgentRuntime` + `MockLLMClient`

## Manual testing with the CLI

You can exercise all assignment requirements manually with the CLI.

### Happy path: greeting, one-at-a-time collection, validation, escalation

```bash
PYTHONPATH=src python -m konko_agent.cli --config configs/default_agent.yaml
```

Suggested conversation:

- Agent (auto): shows the configured `personality.greeting` (custom greeting requirement).
- You: `alice@example.com`
  - Agent: accepts email and asks for name (collects first field, moves to next).
- You: `Alice Smith`
  - Agent: accepts name and asks for phone.
- You: `123`
  - Agent: rejects as invalid phone (minimal validation) and asks again.
- You: `+1 555 123 4567`
  - Agent: accepts phone and asks for address.
- You: `123 Main St, Springfield`
  - Agent: confirms it has all required fields and uses the configured `closing` message, effectively escalating the conversation for handoff (all-fields escalation).

This run demonstrates:

- Configured custom greeting at the start of a new conversation.
- One-at-a-time collection in the configured order (email, name, phone, address).
- Minimal validation for email/phone/address.
- Automatic escalation/closing when all required fields are collected.

### Corrections and multiple attempts

Using the same CLI run:

- You: `alice@example.com`
- You: `Alice Smith`
- You: `+1 555 123 4567`
- You: `123 Main St, Springfield`
- You: `Actually, my email is alice+new@example.com`
  - Agent: treats this as a correction, updates the email field, and keeps the previous attempt in its internal history.

This shows how multiple attempts are handled: the agent keeps an append-only history of attempts while exposing only the latest valid value.

### Off-topic handling and redirection

At any point while the agent is collecting a field:

- You: `By the way, what's your name?`
  - Agent: gives a brief friendly response and redirects you back to the current field (e.g. “Let's stay focused, can you share your email?”), satisfying the off-topic handling requirement.

### Escalation by trigger phrase

`configs/default_agent.yaml` configures `trigger_phrases` for escalation. In a conversation where not all fields are yet collected:

- You: `I want to speak to a human`
  - Agent: recognizes the trigger phrase, escalates early, and uses the configured closing message to indicate handoff to a human (policy-based escalation).

These manual CLI flows, combined with the automated tests, cover:

- Async runtime and multi-session state (via the underlying `AgentRuntime`).
- Conversation flow requirements (greeting, sequential fields, corrections, validation, escalation, off-topic handling).
- Configuration-driven behavior (personality, greeting, fields, escalation policies).

Fixtures use `MockLLMClient` (scripted JSON responses); no network or patches.

## Project layout

```
src/konko_agent/
  config/       # models.py, loader.py
  domain/       # state, phases, validators, escalation, intent
  infrastructure/  # LLMClient, StateStore, implementations
  orchestration/   # prompt_builder, agent, runtime
  cli.py
tests/
  conftest.py
  test_config/
  test_domain/
  test_orchestration/
configs/        # default_agent.yaml, casual_agent.yaml, minimal_agent.yaml
```

## Decisions

See [DECISIONS.md](DECISIONS.md) for architecture and design choices.
