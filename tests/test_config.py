from grok_bot import config
from grok_bot.config import Settings


def test_from_env_defaults():
    settings = Settings.from_env({})
    assert settings.model == config.DEFAULT_MODEL
    assert settings.base_url == config.DEFAULT_BASE_URL
    assert settings.sandbox_cpus == 8  # the sandbox this bot targets


def test_from_env_overrides():
    settings = Settings.from_env(
        {
            "XAI_API_KEY": "secret",
            "GROK_MODEL": "grok-3",
            "SANDBOX_CPUS": "16",
            "GROK_TIMEOUT_S": "5",
        }
    )
    assert settings.api_key == "secret"
    assert settings.model == "grok-3"
    assert settings.sandbox_cpus == 16
    assert settings.timeout_s == 5.0


def test_worker_count_capped_by_sandbox_cpus(monkeypatch):
    # On a big machine the bot must still respect the 8-core sandbox budget.
    monkeypatch.setattr(config, "detect_cpu_count", lambda: 64)
    assert Settings(sandbox_cpus=8).worker_count == 8


def test_worker_count_uses_detected_when_smaller(monkeypatch):
    monkeypatch.setattr(config, "detect_cpu_count", lambda: 2)
    assert Settings(sandbox_cpus=8).worker_count == 2


def test_require_api_key_raises_when_missing():
    settings = Settings(api_key="")
    try:
        settings.require_api_key()
    except RuntimeError as exc:
        assert "XAI_API_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
