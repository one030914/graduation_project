#!/usr/bin/env bash
set -euo pipefail

# Short Linux-friendly dev launcher
cd "$(dirname "$0")/.."

export WATCHFILES_FORCE_POLLING="${WATCHFILES_FORCE_POLLING:-true}"

# Use PYTHON env if set, otherwise python3
PYTHON="${PYTHON:-python3}"

# Quick check for uvicorn
if ! command -v "$PYTHON" >/dev/null 2>&1 || ! "$PYTHON" -c "import uvicorn" >/dev/null 2>&1; then
  echo "Python or uvicorn not found. Install dependencies or set PYTHON." >&2
  echo "Example: python3 -m pip install uvicorn fastapi python-dotenv" >&2
  exit 1
fi

# Start uvicorn with common reload dirs
exec "$PYTHON" -m uvicorn backend.interface:app \
  --reload \
  --reload-dir backend \
  --reload-dir pipeline \
  --reload-dir configs \
  --reload-dir agents \
  --reload-dir data \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}"
