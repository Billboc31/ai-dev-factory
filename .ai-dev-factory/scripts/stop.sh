#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

[ -f deploy/.env ] && source deploy/.env || true

RUN_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
SUPERVISOR_URL="http://127.0.0.1:${SUPERVISOR_PORT}"
SUPERVISOR_PID_FILE="$RUN_DIR/supervisor.pid"

# 1. Stop the daemon via the supervisor HTTP API (B2-a)
echo "stop: requesting daemon stop via supervisor API..."
if curl -sf --max-time 5 -X POST "$SUPERVISOR_URL/daemon/stop" >/dev/null 2>&1; then
  echo "stop: daemon stop acknowledged"
else
  echo "stop: supervisor not reachable or daemon already stopped, continuing"
fi

# 2. Stop Docker stack (project-scoped by working directory)
echo "stop: stopping Docker stack..."
if [ -f deploy/.env ] && [ -f "${RUN_DIR}/.env.compose" ]; then
  docker compose --env-file deploy/.env --env-file "${RUN_DIR}/.env.compose" down
elif [ -f deploy/.env ]; then
  docker compose --env-file deploy/.env down
else
  docker compose down
fi

# 3. Stop supervisor via PID file (B2-b)
if [ -f "$SUPERVISOR_PID_FILE" ]; then
  SUPERVISOR_PID="$(cat "$SUPERVISOR_PID_FILE")"
  if kill -0 "$SUPERVISOR_PID" 2>/dev/null; then
    echo "stop: stopping supervisor (PID $SUPERVISOR_PID)..."
    kill "$SUPERVISOR_PID"
    # Wait up to 10 s for clean exit
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$SUPERVISOR_PID" 2>/dev/null || break
      sleep 1
    done
    # Force-kill only if still alive after grace period
    if kill -0 "$SUPERVISOR_PID" 2>/dev/null; then
      echo "stop: supervisor did not exit cleanly, sending SIGKILL..."
      kill -9 "$SUPERVISOR_PID" || true
    fi
  else
    echo "stop: supervisor PID $SUPERVISOR_PID not running"
  fi
  rm -f "$SUPERVISOR_PID_FILE"
else
  echo "stop: no supervisor PID file found, nothing to stop"
fi

echo "stop: done"
