"""LLM client: Protocol + httpx implementation + mock for tests."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM completion. Implement with httpx or mock for tests."""

    async def complete(self, system_prompt: str, user_message: str) -> str:
        """
        Send system + user message to LLM, return raw response text.
        Caller is responsible for parsing JSON into TurnAnalysis if needed.
        """
        ...


class KonkoLLMClient:
    """Async httpx-based LLM client. Expects OpenAI-compatible chat API."""

    def __init__(
        self,
        base_url: str,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key

    async def complete(self, system_prompt: str, user_message: str) -> str:
        import httpx

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        payload = {"model": self._model, "messages": messages}
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers=headers or None,
            )
            r.raise_for_status()
            data = r.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        return (choices[0].get("message") or {}).get("content", "") or ""


class MockLLMClient:
    """Implements LLMClient with scripted responses for tests. No network."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = list(responses) if responses else []
        self.call_count = 0

    async def complete(self, system_prompt: str, user_message: str) -> str:
        if self.call_count < len(self.responses):
            out = self.responses[self.call_count]
        else:
            out = '{"intent": "off_topic", "response_text": "I didn\'t understand.", "confidence": 0.5}'
        self.call_count += 1
        return out
