"""Minimal client for the Grok (xAI) chat-completions API.

xAI exposes an OpenAI-compatible REST API, so a small httpx-based client is
all that is needed — no heavyweight SDK dependency.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from .config import Settings

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GrokAPIError(RuntimeError):
    """Raised when the Grok API cannot be reached or returns an error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GrokClient:
    """Synchronous client for the Grok chat-completions endpoint."""

    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.base_url,
            headers={"Authorization": f"Bearer {settings.require_api_key()}"},
            timeout=settings.timeout_s,
            transport=transport,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Send a conversation and return the assistant's reply text."""
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        data = self._post_with_retry("/chat/completions", payload)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise GrokAPIError(f"Unexpected Grok API response shape: {data!r}") from exc

    def _post_with_retry(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                response = self._client.post(path, json=payload)
            except httpx.HTTPError as exc:
                if attempt >= self._settings.max_retries:
                    raise GrokAPIError(f"Network error talking to the Grok API: {exc}") from exc
                self._sleep_before_retry(attempt)
                attempt += 1
                continue

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise GrokAPIError("Grok API returned invalid JSON") from exc

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < self._settings.max_retries:
                self._sleep_before_retry(attempt)
                attempt += 1
                continue

            raise GrokAPIError(
                f"Grok API error {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(self._settings.backoff_s * (2**attempt))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GrokClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
