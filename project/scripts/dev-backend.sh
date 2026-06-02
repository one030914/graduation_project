#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export WATCHFILES_FORCE_POLLING="${WATCHFILES_FORCE_POLLING:-true}"

exec uvicorn backend.interface:app \
  --reload \
  --reload-dir backend \
  --reload-dir pipeline \
  --reload-dir configs \
  --reload-dir agents \
  --reload-dir data \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}"
