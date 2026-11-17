from grok_bot.workers import run_batch


def test_run_batch_preserves_order():
    prompts = [f"prompt-{i}" for i in range(10)]
    results = run_batch(lambda p: p.upper(), prompts, workers=4)
    assert [r.prompt for r in results] == prompts
    assert [r.reply for r in results] == [p.upper() for p in prompts]
    assert all(r.error is None for r in results)


def test_run_batch_captures_errors_without_aborting():
    def flaky(prompt):
        if prompt == "bad":
            raise ValueError("nope")
        return f"ok:{prompt}"

    results = run_batch(flaky, ["good", "bad", "also-good"], workers=2)
    assert results[0].reply == "ok:good"
    assert results[1].error == "nope"
    assert results[1].reply is None
    assert results[2].reply == "ok:also-good"


def test_run_batch_empty():
    assert run_batch(lambda p: p, [], workers=8) == []
