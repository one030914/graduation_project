#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export WATCHFILES_FORCE_POLLING="${WATCHFILES_FORCE_POLLING:-true}"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif [[ -x "$PROJECT_ROOT/venv/bin/python" ]]; then
  PYTHON="$PROJECT_ROOT/venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON" >&2
  echo "Install Python 3 or set PYTHON=/path/to/python." >&2
  exit 1
fi

if ! "$PYTHON" -c "import uvicorn" >/dev/null 2>&1; then
  echo "uvicorn is not installed for: $PYTHON" >&2
  echo "Install backend dependencies, for example: $PYTHON -m pip install uvicorn fastapi python-dotenv" >&2
  exit 1
fi

reload_args=()
for dir in backend pipeline configs agents data; do
  if [[ -d "$dir" ]]; then
    reload_args+=(--reload-dir "$dir")
  fi
done

exec "$PYTHON" -m uvicorn backend.interface:app \
  --reload \
  "${reload_args[@]}" \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}"
