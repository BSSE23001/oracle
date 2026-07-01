# syntax=docker/dockerfile:1.8
###############################################################################
# Builder
###############################################################################
FROM python:3.12-slim-bookworm AS builder
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# apt layer: cached via mount instead of re-fetched every build
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git

# Install uv (pinned, cached by digest — this layer basically never rebuilds)
COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

###############################################################################
# Dependency layer — only invalidated when pyproject.toml / uv.lock change
###############################################################################
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync \
        --frozen \
        --no-dev \
        --no-install-project

###############################################################################
# App layer — code changes never bust the dependency cache above
###############################################################################
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync \
        --frozen \
        --no-dev

###############################################################################
# Runtime
###############################################################################
FROM python:3.12-slim-bookworm
ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    TOKENIZERS_PARALLELISM=false
WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl

# Copy installed packages
COPY --from=builder /usr/local /usr/local
# Copy application
COPY --from=builder /app /app

###############################################################################
# Security
###############################################################################
RUN addgroup --system app && \
    adduser --system --ingroup app app
RUN mkdir -p /cache/huggingface && \
    chown -R app:app /cache /app
USER app

###############################################################################
# Healthcheck
###############################################################################
HEALTHCHECK --interval=30s \
             --timeout=5s \
             --start-period=20s \
             --retries=3 \
CMD curl -f http://127.0.0.1:8000/health || exit 1

EXPOSE 8000

###############################################################################
# Default command
###############################################################################
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
