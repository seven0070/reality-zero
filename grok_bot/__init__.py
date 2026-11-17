"""Grok bot for the reality-zero sandbox."""

from .bot import DEFAULT_SYSTEM_PROMPT, GrokBot
from .client import GrokAPIError, GrokClient
from .config import Settings, detect_cpu_count
from .workers import BatchResult, run_batch

__version__ = "0.1.0"

__all__ = [
    "BatchResult",
    "DEFAULT_SYSTEM_PROMPT",
    "GrokAPIError",
    "GrokBot",
    "GrokClient",
    "Settings",
    "detect_cpu_count",
    "run_batch",
    "__version__",
]
