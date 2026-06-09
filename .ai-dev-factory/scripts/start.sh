#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Snapshot sandbox-injected env vars so they win over deploy/.env (rule C2)
__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"
__SB_SUPERVISOR_URL="${AI_DEV_FACTORY_SUPERVISOR_URL:-}"

[ -f deploy/.env ] && source deploy/.env || true

API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
AI_DEV_FACTORY_SUPERVISOR_URL="${__SB_SUPERVISOR_URL:-${AI_DEV_FACTORY_SUPERVISOR_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
unset __SB_API_PORT __SB_WEB_PORT __SB_SUPERVISOR_PORT __SB_SUPERVISOR_URL

# Host-side scripts probe via 127.0.0.1, not host.docker.internal
SUPERVISOR_HEALTH_URL="${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}"
COMPOSE_PROJECT="${PROJECT_NAME:-ai-dev-factory}"
PID_DIR="$PROJECT_ROOT/.ai-dev-factory/run"
SUPERVISOR_PID_FILE="$PID_DIR/supervisor.pid"

mkdir -p "$PID_DIR"

# Ensure the shared Docker network exists (idempotent)
if ! docker network inspect ai-dev-factory-runtime &>/dev/null; then
  echo "start: creating Docker network ai-dev-factory-runtime"
  docker network create ai-dev-factory-runtime
fi

# Start supervisor if not already running
if [ -f "$SUPERVISOR_PID_FILE" ] && kill -0 "$(cat "$SUPERVISOR_PID_FILE")" 2>/dev/null; then
  echo "start: supervisor already running (pid $(cat "$SUPERVISOR_PID_FILE"))"
else
  echo "start: starting supervisor on port ${AI_DEV_FACTORY_SUPERVISOR_PORT}"
  nohup bash deploy/start_supervisor.sh \
    >"$PID_DIR/supervisor.log" 2>&1 &
  echo $! >"$SUPERVISOR_PID_FILE"
  echo "start: supervisor pid $! — waiting for readiness"
  for i in $(seq 1 30); do
    if curl -sf --max-time 2 "${SUPERVISOR_HEALTH_URL}/health" &>/dev/null; then
      echo "start: supervisor ready"
      break
    fi
    sleep 1
    if [ "$i" -eq 30 ]; then
      echo "start: WARNING — supervisor did not become ready within 30s; continuing" >&2
    fi
  done
fi

# Start Docker compose stack (api + web)
echo "start: starting Docker stack (api=:${API_PORT} web=:${WEB_PORT})"
_COMPOSE_ARGS=("--project-name" "$COMPOSE_PROJECT")
[ -f deploy/.env ] && _COMPOSE_ARGS+=("--env-file" "deploy/.env")

API_PORT="$API_PORT" WEB_PORT="$WEB_PORT" \
  docker compose "${_COMPOSE_ARGS[@]}" up -d --remove-orphans

echo "start: done"
echo "start: api  → http://localhost:${API_PORT}"
echo "start: web  → http://localhost:${WEB_PORT}"
echo "start: supervisor → ${SUPERVISOR_HEALTH_URL}"
