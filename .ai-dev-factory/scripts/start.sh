#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# ── Port + URL resolution ────────────────────────────────────────────────────
#
# Sandbox runs allocate isolated ports and pretty URLs and inject
# them via the process env (API_PORT / WEB_PORT /
# AI_DEV_FACTORY_SUPERVISOR_PORT / AI_DEV_FACTORY_SUPERVISOR_URL /
# AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL / SANDBOX_API_URL /
# SANDBOX_WEB_URL). The main runtime normally reads its ports from
# ``deploy/.env`` or falls back to documented defaults.
#
# When both an injected value and a deploy/.env value exist, the
# **sandbox-injected value wins** — otherwise sourcing deploy/.env
# would silently downgrade the sandbox to the main runtime's
# 8080/3000/8090 ports and produce false-positive healthchecks
# against the main runtime.
#
# Implementation: snapshot inbound env, source deploy/.env, then
# restore the snapshot as the final answer.

__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"
__SB_SUPERVISOR_URL="${AI_DEV_FACTORY_SUPERVISOR_URL:-}"
__SB_SUPERVISOR_HEALTH_URL="${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-}"
__SB_API_URL="${SANDBOX_API_URL:-}"
__SB_WEB_URL="${SANDBOX_WEB_URL:-}"
__SB_SUPERVISOR_ALREADY_STARTED="${AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED:-}"

# shellcheck source=/dev/null
[ -f deploy/.env ] && source deploy/.env || true

API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
# AI_DEV_FACTORY_SUPERVISOR_URL is consumed by Docker containers (it
# must use host.docker.internal which is not resolvable from host
# shells). Host-side scripts probe a separate URL — see below.
AI_DEV_FACTORY_SUPERVISOR_URL="${__SB_SUPERVISOR_URL:-${AI_DEV_FACTORY_SUPERVISOR_URL:-http://host.docker.internal:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL="${__SB_SUPERVISOR_HEALTH_URL:-${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
# Pretty URLs: only set in sandbox mode (or when an operator manually
# sets them for the main runtime). When unset, the URL block below
# falls back to direct host:port for both display and probes.
SANDBOX_API_URL="${__SB_API_URL:-${SANDBOX_API_URL:-}}"
SANDBOX_WEB_URL="${__SB_WEB_URL:-${SANDBOX_WEB_URL:-}}"
AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED="${__SB_SUPERVISOR_ALREADY_STARTED:-${AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED:-0}}"
export API_PORT WEB_PORT
export AI_DEV_FACTORY_SUPERVISOR_PORT AI_DEV_FACTORY_SUPERVISOR_URL
export AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL
export SANDBOX_API_URL SANDBOX_WEB_URL
export AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED

unset __SB_API_PORT __SB_WEB_PORT
unset __SB_SUPERVISOR_PORT __SB_SUPERVISOR_URL __SB_SUPERVISOR_HEALTH_URL
unset __SB_API_URL __SB_WEB_URL __SB_SUPERVISOR_ALREADY_STARTED

RUN_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
mkdir -p "$RUN_DIR"

SUPERVISOR_PID_FILE="$RUN_DIR/supervisor.pid"

# ── Supervisor ───────────────────────────────────────────────────────────────
#
# Sandbox validation starts the supervisor in run_sandbox.py before
# invoking this script. Starting again here would bind the same port
# twice ([Errno 48] address already in use).

if [ "${AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED:-0}" = "1" ]; then
  echo "start: supervisor already managed by sandbox worker, skipping startup"
elif [ -f "$SUPERVISOR_PID_FILE" ] && kill -0 "$(cat "$SUPERVISOR_PID_FILE")" 2>/dev/null; then
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
#
# Announce the URLs that the human operator (and healthcheck.sh)
# will actually probe. When the sandbox supplied pretty URLs, those
# are printed instead of ``localhost:<port>`` so the dashboard /
# CLI log matches the browser experience.

echo "start: done"
if [ -n "${SANDBOX_API_URL:-}" ]; then
  echo "start:   API        ${SANDBOX_API_URL}"
else
  echo "start:   API        http://localhost:${API_PORT}"
fi
if [ -n "${SANDBOX_WEB_URL:-}" ]; then
  echo "start:   web        ${SANDBOX_WEB_URL}"
else
  echo "start:   web        http://localhost:${WEB_PORT}"
fi
echo "start:   supervisor ${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL}"
if [ -n "${SANDBOX_ID:-}" ]; then
  echo "start:   sandbox    ${SANDBOX_ID}"
fi
