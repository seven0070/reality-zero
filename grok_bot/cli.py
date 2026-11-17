"""Command-line interface for the Grok bot."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .bot import DEFAULT_SYSTEM_PROMPT, GrokBot
from .client import GrokAPIError, GrokClient
from .config import Settings, detect_cpu_count
from .workers import run_batch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grok-bot",
        description="Grok bot designed to run inside an 8-CPU-core sandbox.",
    )
    parser.add_argument(
        "--system-prompt",
        default=DEFAULT_SYSTEM_PROMPT,
        help="Override the default system prompt.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="Print sandbox/runtime configuration as JSON.")

    ask = sub.add_parser("ask", help="Send a single prompt and print the reply.")
    ask.add_argument("prompt")

    sub.add_parser("chat", help="Interactive chat REPL.")

    batch = sub.add_parser(
        "batch",
        help="Run prompts from a file (one per line) across the sandbox's cores.",
    )
    batch.add_argument("file", help="UTF-8 file with one prompt per line ('-' for stdin).")
    batch.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Worker threads (default: detected CPUs, capped by SANDBOX_CPUS).",
    )
    batch.add_argument("--json", action="store_true", help="Emit results as JSON lines.")
    return parser


def _cmd_info(settings: Settings) -> int:
    print(
        json.dumps(
            {
                "model": settings.model,
                "base_url": settings.base_url,
                "sandbox_cpus": settings.sandbox_cpus,
                "detected_cpus": detect_cpu_count(),
                "worker_count": settings.worker_count,
                "api_key_set": bool(settings.api_key),
            },
            indent=2,
        )
    )
    return 0


def _cmd_ask(settings: Settings, args: argparse.Namespace) -> int:
    with GrokClient(settings) as client:
        bot = GrokBot(client, system_prompt=args.system_prompt)
        print(bot.ask(args.prompt))
    return 0


def _cmd_chat(settings: Settings, args: argparse.Namespace) -> int:
    with GrokClient(settings) as client:
        bot = GrokBot(client, system_prompt=args.system_prompt)
        print("grok-bot interactive chat — 'exit'/Ctrl-D to quit, 'reset' to clear history.")
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.lower() in {"exit", "quit"}:
                break
            if line.lower() == "reset":
                bot.reset()
                print("(history cleared)")
                continue
            try:
                print(f"grok> {bot.ask(line)}")
            except GrokAPIError as exc:
                print(f"! grok api error: {exc}", file=sys.stderr)
    return 0


def _cmd_batch(settings: Settings, args: argparse.Namespace) -> int:
    if args.file == "-":
        prompts = [line.strip() for line in sys.stdin if line.strip()]
    else:
        with open(args.file, "r", encoding="utf-8") as fh:
            prompts = [line.strip() for line in fh if line.strip()]
    if not prompts:
        print("no prompts to run", file=sys.stderr)
        return 1

    workers = args.workers or settings.worker_count
    print(f"running {len(prompts)} prompt(s) across {workers} workers...", file=sys.stderr)

    def process(prompt: str) -> str:
        with GrokClient(settings) as client:
            return GrokBot(client, system_prompt=args.system_prompt).ask(prompt)

    failures = 0
    for result in run_batch(process, prompts, workers=workers):
        if result.error is not None:
            failures += 1
        if args.json:
            print(
                json.dumps(
                    {"prompt": result.prompt, "reply": result.reply, "error": result.error}
                )
            )
        else:
            status = "ERROR" if result.error else "OK"
            print(f"[{status}] {result.prompt}\n{result.error or result.reply}\n")
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = Settings.from_env()

    if args.command == "info":
        return _cmd_info(settings)

    try:
        settings.require_api_key()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    handler = {
        "ask": _cmd_ask,
        "chat": _cmd_chat,
        "batch": _cmd_batch,
    }[args.command]
    return handler(settings, args)
