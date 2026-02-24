"""Agent runtime: manages multiple concurrent sessions."""

from __future__ import annotations

from konko_agent.config.models import AgentConfig
from konko_agent.orchestration.agent import ConversationAgent


class AgentRuntime:
    """Holds config + LLM client + state store; creates one ConversationAgent; routes by session_id."""

    def __init__(
        self,
        config: AgentConfig,
        llm_client: object,
        state_store: object,
    ) -> None:
        self.config = config
        self._agent = ConversationAgent(config, llm_client, state_store)

    async def start_session(self, session_id: str) -> str:
        """
        Start a new session and return the greeting message.
        If the session already exists, returns the configured greeting.
        """
        return await self._agent.start_session(session_id)

    async def handle_message(self, session_id: str, user_message: str) -> str:
        """Route message to agent; return assistant reply. Sessions are isolated by session_id."""
        return await self._agent.handle_message(session_id, user_message)

    async def get_state(self, session_id: str):
        """Get current conversation state for session (or None)."""
        return await self._agent.get_state(session_id)

    def get_greeting(self) -> str:
        """Initial greeting for new sessions (from config)."""
        return self.config.personality.greeting
