from grok_bot.bot import DEFAULT_SYSTEM_PROMPT, GrokBot


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(list(messages))
        return f"reply-{len(self.calls)}"


def test_ask_appends_exchange_to_history():
    bot = GrokBot(FakeClient())
    reply = bot.ask("hello")
    assert reply == "reply-1"
    roles = [m["role"] for m in bot.history]
    assert roles == ["system", "user", "assistant"]


def test_history_is_sent_to_client():
    client = FakeClient()
    bot = GrokBot(client)
    bot.ask("first")
    bot.ask("second")
    second_call = client.calls[-1]
    assert second_call[0]["content"] == DEFAULT_SYSTEM_PROMPT
    assert [m["content"] for m in second_call[1:]] == ["first", "reply-1", "second"]


def test_reset_keeps_only_system_prompt():
    bot = GrokBot(FakeClient())
    bot.ask("hello")
    bot.reset()
    assert len(bot.history) == 1
    assert bot.history[0]["role"] == "system"


def test_history_is_trimmed():
    bot = GrokBot(FakeClient(), max_history=4)
    for i in range(5):
        bot.ask(f"q{i}")
    history = bot.history
    assert len(history) == 1 + 4  # system + last 4 messages
    assert history[0]["role"] == "system"
    assert history[-1]["content"] == "reply-5"
