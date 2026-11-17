"""Environment-driven configuration for the Grok bot sandbox."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL = "grok-4"
DEFAULT_SANDBOX_CPUS = 8


def detect_cpu_count() -> int:
    """Return the CPUs actually usable by this process.

    Scheduler affinity (Linux) reflects container/sandbox CPU limits much
    better than the machine-wide ``os.cpu_count()``.
    """
    try:
        return len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    count = os.cpu_count()
    return count if count else DEFAULT_SANDBOX_CPUS


@dataclass(frozen=True)
class Settings:
    """Runtime settings, typically loaded from the environment."""

    api_key: str = ""
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_s: float = 60.0
    max_retries: int = 2
    backoff_s: float = 0.5
    sandbox_cpus: int = DEFAULT_SANDBOX_CPUS

    @property
    def worker_count(self) -> int:
        """Workers the bot fans out across.

        Sized to the CPUs the process can actually use, capped by the
        sandbox's provisioned CPUs (8 in the target environment).
        """
        available = detect_cpu_count()
        return max(1, min(self.sandbox_cpus, available))

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            api_key=env.get("XAI_API_KEY", ""),
            base_url=env.get("GROK_BASE_URL", DEFAULT_BASE_URL),
            model=env.get("GROK_MODEL", DEFAULT_MODEL),
            timeout_s=float(env.get("GROK_TIMEOUT_S", "60")),
            max_retries=int(env.get("GROK_MAX_RETRIES", "2")),
            backoff_s=float(env.get("GROK_BACKOFF_S", "0.5")),
            sandbox_cpus=int(env.get("SANDBOX_CPUS", str(DEFAULT_SANDBOX_CPUS))),
        )

    def require_api_key(self) -> str:
        if not self.api_key:
            raise RuntimeError(
                "XAI_API_KEY is not set. Get a key at https://console.x.ai "
                "and put it in your environment or .env file."
            )
        return self.api_key
