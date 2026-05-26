#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# ── Port resolution ──────────────────────────────────────────────────────────
#
# Sandbox runs (tools/agent_runner/run_sandbox.py) allocate isolated
# ports and inject them via the process environment. The main runtime
# normally reads its ports from `deploy/.env`. When both are present
# the **sandbox-injected values win** — otherwise sourcing deploy/.env
# would silently downgrade the sandbox to 8080/3000 and produce false-
# positive healthchecks against the main runtime.
#
# To preserve precedence we snapshot the inbound env first, source
# deploy/.env (which may export other useful vars like HOST_*), then
# restore the snapshot.

__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"
__SB_SUPERVISOR_URL="${AI_DEV_FACTORY_SUPERVISOR_URL:-}"

# shellcheck source=/dev/null
[ -f deploy/.env ] && source deploy/.env || true

# Restore precedence: sandbox > deploy/.env > documented default.
API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
AI_DEV_FACTORY_SUPERVISOR_URL="${__SB_SUPERVISOR_URL:-${AI_DEV_FACTORY_SUPERVISOR_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
export API_PORT WEB_PORT AI_DEV_FACTORY_SUPERVISOR_PORT AI_DEV_FACTORY_SUPERVISOR_URL

unset __SB_API_PORT __SB_WEB_PORT __SB_SUPERVISOR_PORT __SB_SUPERVISOR_URL

RUN_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
mkdir -p "$RUN_DIR"

SUPERVISOR_PID_FILE="$RUN_DIR/supervisor.pid"

# ── Supervisor ───────────────────────────────────────────────────────────────

if [ -f "$SUPERVISOR_PID_FILE" ] && kill -0 "$(cat "$SUPERVISOR_PID_FILE")" 2>/dev/null; then
  echo "start: supervisor already running (PID $(cat "$SUPERVISOR_PID_FILE"))"
else
  if [ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    echo "start: ERROR — .venv not found, run bootstrap.sh first" >&2
    exit 1
  fi
  echo "start: starting supervisor on port ${AI_DEV_FACTORY_SUPERVISOR_PORT}..."
  bash "$PROJECT_ROOT/deploy/start_supervisor.sh" &
  SUPERVISOR_PID=$!
  echo "$SUPERVISOR_PID" > "$SUPERVISOR_PID_FILE"
  echo "start: supervisor started (PID $SUPERVISOR_PID)"
  sleep 2
fi

# ── Docker stack ─────────────────────────────────────────────────────────────

echo "start: starting Docker stack..."
if [ -f deploy/.env ]; then
  docker compose --env-file deploy/.env up -d
else
  docker compose up -d
fi

# ── Resolved URLs ────────────────────────────────────────────────────────────

echo "start: done"
echo "start:   API        http://localhost:${API_PORT}"
echo "start:   web        http://localhost:${WEB_PORT}"
echo "start:   supervisor ${AI_DEV_FACTORY_SUPERVISOR_URL}"
if [ -n "${SANDBOX_ID:-}" ]; then
  echo "start:   sandbox    ${SANDBOX_ID}"
fi
