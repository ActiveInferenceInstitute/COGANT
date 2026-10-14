# syntax=docker/dockerfile:1.7
#
# COGANT production server image.
#
# The image uses python:3.12-slim + uv to replicate the developer
# workflow: `uv sync --frozen --no-dev` installs the runtime dependencies
# pinned in uv.lock, and the container runs
# `uv run uvicorn cogant.server.app:app`. We intentionally avoid a
# multi-stage build. Instead the dependency layer is keyed on
# pyproject.toml + uv.lock only (a source-only change reuses it), and uv's
# download cache lives in a BuildKit cache mount, so rebuilds stay fast
# without the cache being baked into the image.
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

# Official uv binaries from Astral's distroless image, pinned to an exact
# release so every build uses the same resolver/installer (the former
# `pip install uv` took whatever release was newest at build time).
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

# These apply to every uv command in the image: the build-time syncs, the
# CMD's `uv run`, and ad-hoc `docker run ... uv run cogant ...`.
#   UV_FROZEN=1                install exactly what uv.lock pins; never re-lock.
#   UV_NO_DEV=1                skip the dev dependency group (test/docs tooling);
#                              without it `uv run` would try to install that
#                              group, over the network, at container start.
#   UV_PYTHON_DOWNLOADS=never  always use the image's own Python 3.12.
#   UV_LINK_MODE=copy          the cache mount is a separate filesystem, so uv
#                              copies instead of hardlinking (and stays quiet).
ENV UV_FROZEN=1 \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

WORKDIR /app

# Layer 1: third-party dependencies only, keyed on the lockfile inputs.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Layer 2: the project itself. `uv sync` installs cogant in editable mode
# from /app/py; the source is baked into the image, so no bind mount is
# needed. A missing or unreadable uv.lock now fails the build instead of
# silently re-resolving: the former `|| uv sync` retry could ship an image
# whose dependency set matched no committed lockfile.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

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
