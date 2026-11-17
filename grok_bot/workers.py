"""Fan work out across the sandbox's CPU cores (8 in the target environment).

The work here is network I/O (Grok API calls), so a thread pool is the right
tool: threads release the GIL while waiting on the network, and the pool is
sized to the number of CPU cores the sandbox was provisioned with.
"""
from __future__ import annotations

import dataclasses
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable


@dataclasses.dataclass(frozen=True)
class BatchResult:
    prompt: str
    reply: str | None
    error: str | None


def run_batch(
    fn: Callable[[str], str],
    prompts: Iterable[str],
    *,
    workers: int,
) -> list[BatchResult]:
    """Apply ``fn`` to every prompt using ``workers`` threads.

    Results come back in the same order the prompts were given; a failing
    prompt does not abort the rest of the batch.
    """
    prompt_list = list(prompts)
    if not prompt_list:
        return []
    workers = max(1, min(workers, len(prompt_list)))

    results: list[BatchResult | None] = [None] * len(prompt_list)

    def _run(prompt: str) -> BatchResult:
        try:
            return BatchResult(prompt=prompt, reply=fn(prompt), error=None)
        except Exception as exc:  # noqa: BLE001 - batch must not die on one failure
            return BatchResult(prompt=prompt, reply=None, error=str(exc))

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="grok-bot") as pool:
        futures = {pool.submit(_run, prompt): i for i, prompt in enumerate(prompt_list)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    return [r for r in results if r is not None]
