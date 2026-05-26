#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# ── Port resolution ──────────────────────────────────────────────────────────
#
# Probe the SAME URLs that start.sh exposed: sandbox-injected ports
# (API_PORT / WEB_PORT / AI_DEV_FACTORY_SUPERVISOR_PORT /
# AI_DEV_FACTORY_SUPERVISOR_URL) take precedence over anything that
# `deploy/.env` would set. Without this, a sandbox healthcheck would
# silently probe the MAIN runtime on 8080/3000 and report a green
# light even though the sandbox itself never came up — a false
# positive that hid real deploy failures.

__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"
__SB_SUPERVISOR_URL="${AI_DEV_FACTORY_SUPERVISOR_URL:-}"

# shellcheck source=/dev/null
[ -f deploy/.env ] && source deploy/.env || true

API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
AI_DEV_FACTORY_SUPERVISOR_URL="${__SB_SUPERVISOR_URL:-${AI_DEV_FACTORY_SUPERVISOR_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"

unset __SB_API_PORT __SB_WEB_PORT __SB_SUPERVISOR_PORT __SB_SUPERVISOR_URL

TIMEOUT=30
RETRIES=3
DELAY=5

PASS=0
FAIL=0

probe() {
  local name="$1"
  local url="$2"
  local attempt=0
  while [ "$attempt" -lt "$RETRIES" ]; do
    if curl -sf --max-time "$TIMEOUT" "$url" >/dev/null 2>&1; then
      echo "PASS  $name  ($url)"
      PASS=$((PASS + 1))
      return 0
    fi
    attempt=$((attempt + 1))
    [ "$attempt" -lt "$RETRIES" ] && sleep "$DELAY"
  done
  echo "FAIL  $name  ($url)  — no response after $RETRIES attempts"
  FAIL=$((FAIL + 1))
  return 1
}

probe "api"        "http://localhost:${API_PORT}/health"     || true
probe "web"        "http://localhost:${WEB_PORT}"            || true
probe "supervisor" "${AI_DEV_FACTORY_SUPERVISOR_URL}/health" || true

echo ""
echo "healthcheck: ${PASS} passed, ${FAIL} failed"
if [ -n "${SANDBOX_ID:-}" ]; then
  echo "healthcheck: sandbox=${SANDBOX_ID}"
fi

[ "$FAIL" -eq 0 ]
