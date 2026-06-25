# syntax=docker/dockerfile:1.8

###############################################################################
# ORACLE Backend
#
# Shared image for:
#   - FastAPI API
#   - Celery Worker
###############################################################################

FROM python:3.12-slim

###############################################################################
# Environment
###############################################################################

ENV \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/root/.cache/uv \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

###############################################################################
# System packages
###############################################################################

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
 && rm -rf /var/lib/apt/lists/*

###############################################################################
# Install uv
###############################################################################

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

###############################################################################
# Install dependencies
#
# This layer is only rebuilt when pyproject.toml changes.
###############################################################################

COPY pyproject.toml ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

###############################################################################
# Copy source
###############################################################################

COPY . .

EXPOSE 8000

###############################################################################
# Default command
###############################################################################

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]