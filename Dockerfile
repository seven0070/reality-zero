FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY grok_bot ./grok_bot

# Run as an unprivileged user inside the sandbox.
RUN useradd --create-home --uid 1000 sandbox
USER sandbox

# The sandbox this image runs in is provisioned with 8 CPU cores.
ENV SANDBOX_CPUS=8

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD ["python", "-m", "grok_bot", "info"]

CMD ["python", "-m", "grok_bot", "chat"]
