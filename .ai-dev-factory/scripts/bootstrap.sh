#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

[ -f deploy/.env ] && source deploy/.env || true

RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}"

# Create runtime directory structure (idempotent)
mkdir -p \
  "${RUNTIME_ROOT}/runs" \
  "${RUNTIME_ROOT}/worktrees" \
  "${RUNTIME_ROOT}/clones" \
  "${RUNTIME_ROOT}/logs" \
  "${RUNTIME_ROOT}/state" \
  "${RUNTIME_ROOT}/registry" \
  "${RUNTIME_ROOT}/sandboxes" \
  "${RUNTIME_ROOT}/.runtime"

# Create scripts run directory for PID files
mkdir -p "$PROJECT_ROOT/.ai-dev-factory/run"

# Best-effort artifact migration (never overwrites existing files)
if [ -f "/app/.runtime/ai-dev-factory.sqlite" ] && [ ! -f "${RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite" ]; then
  echo "bootstrap: migrating sqlite db /app/.runtime/ -> ${RUNTIME_ROOT}/.runtime/"
  cp "/app/.runtime/ai-dev-factory.sqlite" "${RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite"
fi
if [ -f "${RUNTIME_ROOT}/runs/workers.json" ] && [ ! -f "${RUNTIME_ROOT}/state/workers.json" ]; then
  echo "bootstrap: migrating workers.json runs/ -> state/"
  cp "${RUNTIME_ROOT}/runs/workers.json" "${RUNTIME_ROOT}/state/workers.json"
fi
if [ -f "${RUNTIME_ROOT}/runs/.issue-intake.json" ] && [ ! -f "${RUNTIME_ROOT}/state/.issue-intake.json" ]; then
  echo "bootstrap: migrating .issue-intake.json runs/ -> state/"
  cp "${RUNTIME_ROOT}/runs/.issue-intake.json" "${RUNTIME_ROOT}/state/.issue-intake.json"
fi

# Check required tools
for tool in git docker gh claude; do
  if ! command -v "$tool" &>/dev/null; then
    echo "bootstrap: WARNING — required tool '$tool' not found in PATH" >&2
  fi
done

# Set up Python venv if not present
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
  echo "bootstrap: creating Python venv..."
  python3 -m venv "$PROJECT_ROOT/.venv"
fi

# Install/upgrade Python dependencies
echo "bootstrap: installing Python dependencies..."
"$PROJECT_ROOT/.venv/bin/pip" install --quiet -r "$PROJECT_ROOT/services/control_api/requirements.txt"

echo "bootstrap: runtime root ready at ${RUNTIME_ROOT}"
echo "bootstrap: done"
