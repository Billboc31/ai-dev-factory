#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

[ -f deploy/.env ] && source deploy/.env || true

SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
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

probe "api"        "http://localhost:8080/health"           || true
probe "web"        "http://localhost:3000"                  || true
probe "supervisor" "http://127.0.0.1:${SUPERVISOR_PORT}/health" || true

echo ""
echo "healthcheck: ${PASS} passed, ${FAIL} failed"

[ "$FAIL" -eq 0 ]
