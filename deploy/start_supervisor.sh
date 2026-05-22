#!/usr/bin/env bash
# Start the AI dev factory host supervisor.
# Run this on the host before starting the Docker stack.
#
# Usage:
#   bash deploy/start_supervisor.sh
#
# The supervisor binds to 127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}.
# Docker containers reach it via host.docker.internal:<port>.
# Both halves of the stack load deploy/.env so the configuration is centralised.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# ── Load centralised deploy configuration ────────────────────────────────────
# deploy/.env is the single source of truth for runtime/project roots,
# Docker → host path mappings, and the supervisor port. Edit that file on
# a fresh machine — do NOT hardcode user-specific paths here.
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  # set -a exports every variable defined while sourcing, so the supervisor
  # subprocess sees all of them. Restore the default behavior afterwards.
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
  echo "supervisor: loaded $ENV_FILE"
else
  echo "supervisor: WARNING — $ENV_FILE not found; copy deploy/.env.example and edit it" >&2
fi

# ── Sane defaults if .env is incomplete (do not override what was sourced) ──
export AI_DEV_FACTORY_PROJECT_ROOT="${AI_DEV_FACTORY_PROJECT_ROOT:-$PROJECT_ROOT}"
export AI_DEV_FACTORY_RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}"
SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"

# ── Activate the host venv ──────────────────────────────────────────────────
source .venv/bin/activate

# ── Diagnostic banner (shows the resolved mapping configuration) ────────────
echo "supervisor: project_root=$AI_DEV_FACTORY_PROJECT_ROOT"
echo "supervisor: runtime_root=$AI_DEV_FACTORY_RUNTIME_ROOT"
echo "supervisor: container_project_root=${CONTAINER_PROJECT_ROOT:-<unset>} -> host_project_root=${HOST_PROJECT_ROOT:-<unset>}"
echo "supervisor: container_runtime_root=${CONTAINER_RUNTIME_ROOT:-<unset>} -> host_runtime_root=${HOST_RUNTIME_ROOT:-<unset>}"
echo "supervisor: listening on 127.0.0.1:$SUPERVISOR_PORT"

exec uvicorn services.supervisor.main:app --host 127.0.0.1 --port "$SUPERVISOR_PORT"
