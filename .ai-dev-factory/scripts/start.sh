#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

[ -f deploy/.env ] && source deploy/.env || true

RUN_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
mkdir -p "$RUN_DIR"

SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
SUPERVISOR_PID_FILE="$RUN_DIR/supervisor.pid"

# Start supervisor if not already running
if [ -f "$SUPERVISOR_PID_FILE" ] && kill -0 "$(cat "$SUPERVISOR_PID_FILE")" 2>/dev/null; then
  echo "start: supervisor already running (PID $(cat "$SUPERVISOR_PID_FILE"))"
else
  if [ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    echo "start: ERROR — .venv not found, run bootstrap.sh first" >&2
    exit 1
  fi
  echo "start: starting supervisor on port ${SUPERVISOR_PORT}..."
  # start_supervisor.sh uses exec, so the PID captured here becomes uvicorn's PID
  bash "$PROJECT_ROOT/deploy/start_supervisor.sh" &
  SUPERVISOR_PID=$!
  echo "$SUPERVISOR_PID" > "$SUPERVISOR_PID_FILE"
  echo "start: supervisor started (PID $SUPERVISOR_PID)"
  # Give the supervisor a moment to bind its port before compose contacts it
  sleep 2
fi

# Start Docker stack (idempotent — compose skips already-running containers)
echo "start: starting Docker stack..."
if [ -f deploy/.env ]; then
  docker compose --env-file deploy/.env up -d
else
  docker compose up -d
fi

echo "start: done"
echo "start:   API        http://localhost:8080"
echo "start:   web        http://localhost:3000"
echo "start:   supervisor http://127.0.0.1:${SUPERVISOR_PORT}"
