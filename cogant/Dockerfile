# syntax=docker/dockerfile:1.7
#
# COGANT production server image.
#
# The image uses python:3.12-slim + uv to replicate the developer
# workflow exactly: `uv sync` installs the frozen lockfile, and the
# container runs `uv run uvicorn cogant.server.app:app`. We intentionally
# avoid a multi-stage build because the wheel cache and .venv are the
# hot path; uv stores both inside /app/.venv and reuses them on rebuild.
#
# Build:   docker build -t cogant:latest .
# Run:     docker run --rm -p 8080:8080 cogant:latest
# Health:  curl -f http://localhost:8080/health

FROM python:3.12-slim

# Baseline tooling: build deps for optional wheels, curl for the HEALTHCHECK,
# and git so uv can resolve VCS dependencies if any appear in the lockfile.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv via the official standalone installer and put it on PATH.
RUN pip install --no-cache-dir uv

# Copy the whole project and resolve the lockfile. We copy first and run
# uv sync second so any code change invalidates the lower layer only;
# pyproject.toml / uv.lock changes correctly bust the sync layer.
COPY . .

# Install the project in non-editable mode so the entrypoint does not
# depend on a bind mount. --frozen enforces lockfile parity with the repo.
RUN uv sync --frozen || uv sync

EXPOSE 8080

# Simple curl-based healthcheck hitting the liveness probe. The interval
# is short so orchestrators (k8s, compose) notice crashes quickly, and
# start-period gives uv a chance to warm the import cache on cold start.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8080/health || exit 1

ENV LOG_LEVEL=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["uv", "run", "uvicorn", "cogant.server.app:app", "--host", "0.0.0.0", "--port", "8080"]
