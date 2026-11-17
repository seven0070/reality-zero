# reality-zero

A **Grok bot** packaged as a self-contained sandbox, built to run on a machine
with **8 CPU cores**. It talks to the [Grok (xAI) API](https://docs.x.ai)
through a small `httpx` client — no heavyweight SDK.

## Layout

| Path                  | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `grok_bot/`           | The bot package (config, API client, chat logic, workers) |
| `Dockerfile`          | Sandbox image (Python 3.12 slim, unprivileged user)       |
| `docker-compose.yml`  | Pins the sandbox to **8 CPUs** (`cpus: 8.0`)               |
| `.env.example`        | Configuration template                                    |
| `tests/`              | Unit tests (fully mocked — no API key or network needed)  |

## Quickstart (in the 8-core sandbox)

```bash
cp .env.example .env   # then put your XAI_API_KEY in .env

docker compose build
docker compose run --rm grok-bot                 # interactive chat
docker compose run --rm grok-bot ask "Hello"     # one-shot prompt
docker compose run --rm grok-bot info            # show detected config
```

Batch mode fans prompts out across the sandbox's cores (worker count =
detected CPUs, capped by `SANDBOX_CPUS`, i.e. 8 in the target environment):

```bash
docker compose run --rm grok-bot batch prompts.txt --json
```

## Running without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export XAI_API_KEY=...
python -m grok_bot chat
```

## Configuration

All settings come from the environment (see `.env.example`):

| Variable           | Default                 | Meaning                                  |
| ------------------ | ----------------------- | ---------------------------------------- |
| `XAI_API_KEY`      | — (required)            | xAI API key                              |
| `GROK_MODEL`       | `grok-4`                | Model to chat with                       |
| `GROK_BASE_URL`    | `https://api.x.ai/v1`   | API base URL                             |
| `GROK_TIMEOUT_S`   | `60`                    | Per-request timeout                      |
| `GROK_MAX_RETRIES` | `2`                     | Retries on 429/5xx and network errors    |
| `SANDBOX_CPUS`     | `8`                     | CPU budget of the sandbox                |

CPU detection is affinity-aware (`os.sched_getaffinity`), so when the sandbox
is limited to 8 cores the bot sizes its worker pool to exactly those 8 cores —
and it stays correct when run on smaller dev machines.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

Note: the tests are fully mocked. Live API calls require network access to
`api.x.ai`, which only needs to exist in the sandbox you deploy to.
