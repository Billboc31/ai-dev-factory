#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# ── Load deploy/.env for port overrides ───────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/deploy/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
fi

SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
RETRIES="${HEALTHCHECK_RETRIES:-3}"
DELAY="${HEALTHCHECK_DELAY:-5}"
TIMEOUT="${HEALTHCHECK_TIMEOUT:-30}"
FAIL=0

probe() {
  local name="$1"
  local url="$2"
  local attempt=0
  while [ "$attempt" -lt "$RETRIES" ]; do
    if curl -sf --max-time "$TIMEOUT" "$url" &>/dev/null; then
      echo "  [OK]   $name  ($url)"
      return 0
    fi
    attempt=$((attempt + 1))
    [ "$attempt" -lt "$RETRIES" ] && sleep "$DELAY"
  done
  echo "  [FAIL] $name  ($url) — did not respond after $RETRIES attempts" >&2
  FAIL=1
}

echo "healthcheck: probing all services"

# Primary healthcheck from deploy profile
probe "api (control API)"     "http://localhost:8080/health"
probe "web (dashboard nginx)" "http://localhost:3000"
probe "supervisor (host)"     "http://127.0.0.1:${SUPERVISOR_PORT}/health"

# Daemon: host process — check whether it is alive
if pgrep -f "run_daemon.py" &>/dev/null; then
  echo "  [OK]   daemon (host process running)"
else
  echo "  [WARN] daemon not running (optional — start with START_DAEMON=1)"
fi

if [ "$FAIL" -ne 0 ]; then
  echo "healthcheck: UNHEALTHY"
  exit 1
fi

echo "healthcheck: HEALTHY"
