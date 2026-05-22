#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# ── Verify required tools ─────────────────────────────────────────────────────
for tool in git docker gh claude; do
  if ! command -v "$tool" &>/dev/null; then
    echo "ERROR: required tool not found: $tool" >&2
    exit 1
  fi
done

# ── deploy/.env ───────────────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/deploy/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "bootstrap: creating deploy/.env from example — edit it before starting"
  cp "$PROJECT_ROOT/deploy/.env.example" "$ENV_FILE"
fi

# ── Host Python venv ──────────────────────────────────────────────────────────
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
  echo "bootstrap: creating .venv"
  python3 -m venv "$PROJECT_ROOT/.venv"
fi

source "$PROJECT_ROOT/.venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_ROOT/services/control_api/requirements.txt"

# ── Runtime root directory tree ───────────────────────────────────────────────
# Source deploy/.env so AI_DEV_FACTORY_RUNTIME_ROOT is available here too.
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
fi

RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}"
mkdir -p \
  "${RUNTIME_ROOT}/runs" \
  "${RUNTIME_ROOT}/worktrees" \
  "${RUNTIME_ROOT}/clones" \
  "${RUNTIME_ROOT}/logs" \
  "${RUNTIME_ROOT}/state" \
  "${RUNTIME_ROOT}/registry" \
  "${RUNTIME_ROOT}/sandboxes" \
  "${RUNTIME_ROOT}/.runtime"

echo "bootstrap: runtime root ready at ${RUNTIME_ROOT}"
echo "bootstrap: done — edit deploy/.env then run start.sh"
