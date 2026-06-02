#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# ── Port + URL resolution ────────────────────────────────────────────────────
#
# Same precedence pattern as start.sh — sandbox-injected env wins
# over deploy/.env wins over documented defaults. We probe the SAME
# URLs that start.sh announced, otherwise a sandbox would emit
# "API http://sandbox-…" yet the healthcheck would silently probe
# localhost:8080 — a false positive that hid real sandbox-deploy
# failures.

__SB_API_PORT="${API_PORT:-}"
__SB_WEB_PORT="${WEB_PORT:-}"
__SB_SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"
__SB_SUPERVISOR_URL="${AI_DEV_FACTORY_SUPERVISOR_URL:-}"
__SB_SUPERVISOR_HEALTH_URL="${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-}"
__SB_API_URL="${SANDBOX_API_URL:-}"
__SB_WEB_URL="${SANDBOX_WEB_URL:-}"

# shellcheck source=/dev/null
[ -f deploy/.env ] && source deploy/.env || true

API_PORT="${__SB_API_PORT:-${API_PORT:-8080}}"
WEB_PORT="${__SB_WEB_PORT:-${WEB_PORT:-3000}}"
AI_DEV_FACTORY_SUPERVISOR_PORT="${__SB_SUPERVISOR_PORT:-${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}}"
AI_DEV_FACTORY_SUPERVISOR_URL="${__SB_SUPERVISOR_URL:-${AI_DEV_FACTORY_SUPERVISOR_URL:-http://host.docker.internal:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL="${__SB_SUPERVISOR_HEALTH_URL:-${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}}}"
SANDBOX_API_URL="${__SB_API_URL:-${SANDBOX_API_URL:-}}"
SANDBOX_WEB_URL="${__SB_WEB_URL:-${SANDBOX_WEB_URL:-}}"

unset __SB_API_PORT __SB_WEB_PORT
unset __SB_SUPERVISOR_PORT __SB_SUPERVISOR_URL __SB_SUPERVISOR_HEALTH_URL
unset __SB_API_URL __SB_WEB_URL

TIMEOUT=30
RETRIES=${HEALTHCHECK_RETRIES:-6}
DELAY=${HEALTHCHECK_DELAY:-5}

PASS=0
FAIL=0

probe() {
  local name="$1"
  local url="$2"
  local attempt=0
  local http_code="000"
  while [ "$attempt" -lt "$RETRIES" ]; do
    http_code="$(curl -sS -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")"
    case "$http_code" in
      2[0-9][0-9])
        echo "PASS  $name  ($url)"
        PASS=$((PASS + 1))
        return 0
        ;;
    esac
    attempt=$((attempt + 1))
    [ "$attempt" -lt "$RETRIES" ] && sleep "$DELAY"
  done
  echo "FAIL  $name  ($url)  — http=$http_code after $RETRIES attempts"
  FAIL=$((FAIL + 1))
  return 1
}

# Proxy-infra is not an application probe. Its only job is to verify
# that the reverse proxy route is reachable at transport level.
#
# curl -f would incorrectly mark valid HTTP responses such as 404, 405,
# 502 or 503 as failures. For proxy readiness, any HTTP response means
# Traefik/DNS/route matching is alive. Backend health is checked below by
# the API and web probes.
probe_proxy_infra() {
  local url="$1"
  local attempt=0
  local http_code=""
  while [ "$attempt" -lt "$RETRIES" ]; do
    http_code="$(curl -sS -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || true)"
    if [ -n "$http_code" ] && [ "$http_code" != "000" ]; then
      echo "PASS  proxy-infra  ($url)  — route reachable, http=$http_code"
      PASS=$((PASS + 1))
      return 0
    fi
    attempt=$((attempt + 1))
    [ "$attempt" -lt "$RETRIES" ] && sleep "$DELAY"
  done
  echo "FAIL  proxy-infra  ($url)  — no HTTP response after $RETRIES attempts"
  echo "PROXY_INFRA_FAIL"
  FAIL=$((FAIL + 1))
  return 1
}

# Prefer sandbox pretty URLs when set. These are the URLs users see
# in the dashboard and resolve via Traefik, so probing them validates
# the FULL deploy path (compose → containers → proxy routes →
# Traefik file provider → DNS resolution via *.localhost).
#
# In main-runtime mode SANDBOX_*_URL is empty and we fall back to
# the direct host port — exactly the behaviour we want there.
if [ -n "$SANDBOX_API_URL" ]; then
  probe_proxy_infra "${SANDBOX_API_URL}" || true
  probe "api" "${SANDBOX_API_URL}/health" || true
else
  probe "api" "http://localhost:${API_PORT}/health" || true
fi
if [ -n "$SANDBOX_WEB_URL" ]; then
  probe "web" "${SANDBOX_WEB_URL}" || true
else
  probe "web" "http://localhost:${WEB_PORT}" || true
fi
# Supervisor: ALWAYS probed via the host-side health URL. The
# regular SUPERVISOR_URL points at host.docker.internal which is
# not resolvable from the host shell — using it here used to fail
# every healthcheck on macOS / native-Docker hosts.
probe "supervisor" "${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL}/health" || true

echo ""
echo "healthcheck: ${PASS} passed, ${FAIL} failed"
if [ -n "${SANDBOX_ID:-}" ]; then
  echo "healthcheck: sandbox=${SANDBOX_ID}"
fi

[ "$FAIL" -eq 0 ]