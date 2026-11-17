import httpx
import pytest

from grok_bot.client import GrokAPIError, GrokClient
from grok_bot.config import Settings


def make_client(handler, **overrides):
    settings = Settings(api_key="test-key", backoff_s=0.0, **overrides)
    return GrokClient(settings, transport=httpx.MockTransport(handler))


def ok_response(request):
    assert request.headers["Authorization"] == "Bearer test-key"
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": "hello from grok"}}]},
    )


def test_chat_returns_reply():
    client = make_client(ok_response)
    reply = client.chat([{"role": "user", "content": "hi"}])
    assert reply == "hello from grok"


def test_chat_sends_model_and_messages():
    seen = {}

    def handler(request):
        seen["body"] = request.read()
        return ok_response(request)

    client = make_client(handler, model="grok-3")
    client.chat([{"role": "user", "content": "ping"}], temperature=0.1)
    body = seen["body"].decode()
    assert '"grok-3"' in body
    assert '"ping"' in body


def test_auth_error_raises():
    client = make_client(lambda request: httpx.Response(401, json={"error": "bad key"}))
    with pytest.raises(GrokAPIError) as excinfo:
        client.chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.status_code == 401


def test_retryable_status_is_retried():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, text="overloaded")
        return ok_response(request)

    client = make_client(handler, max_retries=2)
    assert client.chat([{"role": "user", "content": "hi"}]) == "hello from grok"
    assert len(calls) == 2


def test_retry_budget_is_respected():
    client = make_client(lambda request: httpx.Response(500, text="boom"), max_retries=1)
    with pytest.raises(GrokAPIError) as excinfo:
        client.chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.status_code == 500


def test_malformed_response_raises():
    client = make_client(lambda request: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(GrokAPIError):
        client.chat([{"role": "user", "content": "hi"}])
