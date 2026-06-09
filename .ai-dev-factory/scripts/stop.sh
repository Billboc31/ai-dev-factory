#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Snapshot sandbox-injected env vars (rule C2)
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"

[ -f deploy/.env ] && source deploy/.env || true

AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
unset __SB_SUPERVISOR_PORT

# Host-side scripts probe via 127.0.0.1, not host.docker.internal
SUPERVISOR_HEALTH_URL="${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}"
COMPOSE_PROJECT="${PROJECT_NAME:-ai-dev-factory}"
PID_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
SUPERVISOR_PID_FILE="$PID_DIR/supervisor.pid"

# 1. Ask the supervisor to stop the daemon gracefully via its HTTP API (rule B2a)
if curl -sf --max-time 3 "${SUPERVISOR_HEALTH_URL}/health" &>/dev/null; then
  echo "stop: requesting daemon stop via supervisor API"
  curl -sf --max-time 5 -X POST "${SUPERVISOR_HEALTH_URL}/daemon/stop" &>/dev/null || true
  sleep 2
else
  echo "stop: supervisor not reachable — skipping daemon API stop"
fi

# 2. Stop Docker compose stack scoped to this project (rule B6)
echo "stop: stopping Docker stack (project=$COMPOSE_PROJECT)"
_COMPOSE_ARGS=("--project-name" "$COMPOSE_PROJECT")
[ -f deploy/.env ] && _COMPOSE_ARGS+=("--env-file" "deploy/.env")
docker compose "${_COMPOSE_ARGS[@]}" down || true

# 3. Stop supervisor via PID file (rule B2b)
if [ -f "$SUPERVISOR_PID_FILE" ]; then
  SUPERVISOR_PID="$(cat "$SUPERVISOR_PID_FILE")"
  if kill -0 "$SUPERVISOR_PID" 2>/dev/null; then
    echo "stop: stopping supervisor (pid $SUPERVISOR_PID)"
    kill "$SUPERVISOR_PID"
    for i in $(seq 1 10); do
      kill -0 "$SUPERVISOR_PID" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "$SUPERVISOR_PID" 2>/dev/null; then
      echo "stop: force-killing supervisor (pid $SUPERVISOR_PID)"
      kill -9 "$SUPERVISOR_PID" || true
    fi
  else
    echo "stop: supervisor (pid $SUPERVISOR_PID) already stopped"
  fi
  rm -f "$SUPERVISOR_PID_FILE"
else
  echo "stop: no supervisor PID file at $SUPERVISOR_PID_FILE"
fi

echo "stop: done"
