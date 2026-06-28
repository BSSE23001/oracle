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

# Only packages required to build Python dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

###############################################################################
# Dependency layer
###############################################################################

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --frozen \
        --no-dev

###############################################################################
# Copy application
###############################################################################

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
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

# Only runtime libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

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

CMD [
    "uv",
    "run",
    "uvicorn",
    "app.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]