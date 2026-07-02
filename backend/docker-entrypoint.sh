#!/bin/sh
set -e

CHROMA_DIR=${CHROMA_PERSIST_DIR:-/app/data/chroma}
HF_DIR=${HF_HOME:-/cache/huggingface}

mkdir -p "$CHROMA_DIR" "$HF_DIR"
chown -R app:app /app/data /cache

exec gosu app "$@"
