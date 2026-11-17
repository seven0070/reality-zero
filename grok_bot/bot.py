"""Conversation logic for the Grok bot."""
from __future__ import annotations

from .client import GrokClient

DEFAULT_SYSTEM_PROMPT = (
    "You are Grok, running inside the reality-zero sandbox. "
    "Be concise, accurate, and helpful."
)


class GrokBot:
    """A stateful chat bot backed by the Grok API.

    Keeps a bounded conversation history so long sessions inside the
    sandbox do not grow memory (or token usage) without limit.
    """

    def __init__(
        self,
        client: GrokClient,
        *,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_history: int = 40,
    ) -> None:
        self._client = client
        self._system_prompt = system_prompt
        self._max_history = max_history
        self._messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    @property
    def history(self) -> list[dict[str, str]]:
        return list(self._messages)

    def reset(self) -> None:
        """Clear the conversation, keeping only the system prompt."""
        self._messages = [{"role": "system", "content": self._system_prompt}]

    def ask(self, user_text: str, **kwargs: object) -> str:
        """Send a user message and return the assistant's reply."""
        self._messages.append({"role": "user", "content": user_text})
        reply = self._client.chat(self._messages, **kwargs)  # type: ignore[arg-type]
        self._messages.append({"role": "assistant", "content": reply})
        self._trim()
        return reply

    def _trim(self) -> None:
        overflow = len(self._messages) - 1 - self._max_history
        if overflow > 0:
            del self._messages[1 : 1 + overflow]
