"""Escalation: evaluate when to escalate and build payload."""

from __future__ import annotations

from konko_agent.config.models import AgentConfig, EscalationPolicy
from konko_agent.domain.state import ConversationState, EscalationState, FieldState


def _collected_fields_dict(fields: dict[str, FieldState]) -> dict[str, str]:
    """Build field_name -> current_value for all collected fields."""
    return {
        name: fs.current_value
        for name, fs in fields.items()
        if fs.current_value is not None
    }


def evaluate_escalation(
    state: ConversationState,
    config: AgentConfig,
    user_message_lower: str,
) -> EscalationState | None:
    """
    If escalation conditions are met, return EscalationState (reason + fields + optional history).
    Otherwise return None. Pure function, no I/O.
    """
    policy: EscalationPolicy = config.escalation
    if not policy.enabled:
        return None
    collected = _collected_fields_dict(state.fields)
    all_required = len(config.fields) > 0 and all(
        state.fields.get(f.name) and state.fields[f.name].is_collected
        for f in config.fields
        if f.required
    )

    # Trigger phrases (e.g. "speak to human")
    if policy.trigger_phrases and user_message_lower:
        for phrase in policy.trigger_phrases:
            if phrase.lower() in user_message_lower:
                return EscalationState(
                    reason="user_request",
                    fields=collected,
                    history_summary=None,
                )

    if policy.after_all_fields and all_required:
        reason = policy.reason or "all_fields_collected"
        return EscalationState(
            reason=reason,
            fields=collected,
            history_summary=_brief_history_summary(state),
        )

    return None


def _brief_history_summary(state: ConversationState) -> str:
    """Short summary of collection (e.g. counts of attempts)."""
    parts = []
    for name, fs in state.fields.items():
        n = len(fs.attempts)
        if n > 1:
            parts.append(f"{name}: {n} attempts")
        elif n == 1:
            parts.append(f"{name}: 1 attempt")
    return "; ".join(parts) if parts else ""
