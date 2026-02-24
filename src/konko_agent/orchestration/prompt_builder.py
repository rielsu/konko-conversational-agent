"""Build system prompt from config and current state."""

from __future__ import annotations

import json

from konko_agent.config.models import AgentConfig
from konko_agent.domain.state import ConversationState


# Instruction for LLM to return structured JSON (TurnAnalysis shape)
TURN_JSON_SCHEMA = """
You must reply with a single JSON object (no markdown, no extra text) with exactly these keys:
- "intent": one of "field_response", "correction", "escalation_request", "off_topic"
- "response_text": string (what to say to the user)
- "extracted_value": string or null (for field_response/correction: the value the user provided)
- "confidence": number 0.0-1.0
- "field_name": string or null (which field this value is for, e.g. "email")
"""


def build_system_prompt(config: AgentConfig, state: ConversationState) -> str:
    """
    Assemble system prompt: personality, current field, collected fields, and JSON format.
    """
    personality = config.personality
    parts = [
        f"You are {config.name}. Tone: {personality.tone}.",
    ]
    style_bits: list[str] = []
    if personality.style:
        style_bits.append(f"Style: {personality.style}.")
    if personality.formality:
        style_bits.append(f"Formality: {personality.formality}.")
    if personality.use_emojis:
        style_bits.append("Use emojis naturally where appropriate.")
        if personality.emoji_list:
            emoji_str = ", ".join(personality.emoji_list)
            style_bits.append(f"You may use these emojis in particular: {emoji_str}.")
    if style_bits:
        parts.append(" ".join(style_bits))
    parts.extend(
        [
            "",
            "Your job is to collect the following fields from the user, one at a time, and respond in JSON.",
            "",
            "Fields to collect (in order):",
        ]
    )
    for f in config.fields:
        parts.append(f"  - {f.name} ({f.type}): {f.prompt}")
    parts.append("")

    if state.current_field:
        parts.append(f"Current field you are collecting: {state.current_field}")
        parts.append("")
    parts.append("Already collected (do not ask again unless the user clearly corrects them):")
    for name, fs in state.fields.items():
        if fs.current_value:
            parts.append(f"  - {name}: {fs.current_value}")
    parts.append("")

    parts.append(
        "Conversation rules (follow these strictly):"
    )
    parts.append(
        "- Always work on exactly one field at a time: the current_field shown above."
    )
    parts.append(
        "- When you have a valid value for current_field, move on to the next field and do not ask for the old one again unless the user clearly corrects it."
    )
    parts.append(
        "- If the user replies with a short confirmation like 'yes', 'ok', 'that is right', or 'correct' just after you proposed a value, treat it as confirming that value for the current field. Do not re-ask; advance to the next field."
    )
    parts.append(
        "- Treat phrases like 'no, my X is ...', 'actually it is ...', or 'correction' as corrections for the relevant field."
    )
    parts.append(
        "- If the user talks about something unrelated (off-topic), give a brief friendly redirect and then ask about the current field only."
    )
    parts.append("")

    parts.append(
        "Handle intents as follows: field_response (user gives a value), correction (user corrects a previous value), escalation_request (user wants a human), off_topic (redirect back to collecting the current field)."
    )
    parts.append("")
    parts.append(TURN_JSON_SCHEMA.strip())

    return "\n".join(parts)


def build_user_message_for_turn(state: ConversationState) -> str:
    """Last user message for this turn (for LLM call)."""
    for m in reversed(state.messages):
        if m.role == "user":
            return m.content
    return ""
