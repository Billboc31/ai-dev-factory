#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Snapshot sandbox-injected env vars so they win over deploy/.env (rule C2)
__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"

[ -f deploy/.env ] && source deploy/.env || true

API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
unset __SB_API_PORT __SB_WEB_PORT __SB_SUPERVISOR_PORT

# Host-side scripts probe via 127.0.0.1, not host.docker.internal (see .env.example)
SUPERVISOR_HEALTH_URL="${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}"

FAIL=0

# Probe: control API (/health as specified in deploy profile)
if curl -sf --max-time 5 "http://localhost:${API_PORT}/health" &>/dev/null; then
  echo "healthcheck: api        OK  (http://localhost:${API_PORT}/health)"
else
  echo "healthcheck: api        FAIL (http://localhost:${API_PORT}/health)" >&2
  FAIL=1
fi

# Probe: web dashboard (nginx-served React SPA)
if curl -sf --max-time 5 "http://localhost:${WEB_PORT}/" &>/dev/null; then
  echo "healthcheck: web        OK  (http://localhost:${WEB_PORT}/)"
else
  echo "healthcheck: web        FAIL (http://localhost:${WEB_PORT}/)" >&2
  FAIL=1
fi

# Probe: host supervisor
if curl -sf --max-time 5 "${SUPERVISOR_HEALTH_URL}/health" &>/dev/null; then
  echo "healthcheck: supervisor OK  (${SUPERVISOR_HEALTH_URL}/health)"
else
  echo "healthcheck: supervisor FAIL (${SUPERVISOR_HEALTH_URL}/health)" >&2
  FAIL=1
fi

exit "$FAIL"
