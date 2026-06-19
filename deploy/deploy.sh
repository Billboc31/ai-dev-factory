#!/usr/bin/env bash
# One-shot startup for the whole stack:
#   1. Host supervisor (filesystem delegate + daemon spawner) — runs on the host.
#   2. Docker stack: Postgres (db) + control API (api) + dashboard (web).
#
# Both halves load deploy/.env, so RUNTIME_DB_BACKEND, runtime/sandbox roots and
# GitHub config stay consistent (no SQLite/Postgres split-brain). The supervisor
# is started only if it is not already listening, so re-running is safe.
#
# Usage:
#   bash deploy/deploy.sh              # supervisor (if needed) + rebuild/recreate api & web (db untouched)
#   bash deploy/deploy.sh logs -f      # any extra args are forwarded to docker compose
#
# Notes:
# - The Postgres "db" service is part of the compose stack (named volume
#   adf-db-data). You do NOT start the database separately.
# - To stop the Docker stack:        docker compose down        (keeps data)
#   To wipe the database volume too:  docker compose down -v     (destroys data!)
# - The supervisor keeps running in the background; its log is printed below.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ── Load centralised config ──────────────────────────────────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
  echo "deploy: loaded $ENV_FILE (RUNTIME_DB_BACKEND=${RUNTIME_DB_BACKEND:-sqlite})"
else
  echo "deploy: WARNING — $ENV_FILE not found; copy deploy/.env.example and edit it" >&2
fi

SUP_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
SUP_LOG="${TMPDIR:-/tmp}/adf-supervisor.log"

# ── 1. Host supervisor (start only if not already listening) ──────────────────
if lsof -nP -iTCP:"$SUP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "supervisor: already running on 127.0.0.1:$SUP_PORT — leaving it"
else
  echo "supervisor: starting in background (log → $SUP_LOG)"
  nohup bash "$SCRIPT_DIR/start_supervisor.sh" >"$SUP_LOG" 2>&1 &
  disown || true
  printf "supervisor: waiting for health"
  for _ in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:$SUP_PORT/health" >/dev/null 2>&1; then
      echo " — ok (127.0.0.1:$SUP_PORT)"
      break
    fi
    printf "."
    sleep 1
  done
  if ! curl -sf "http://127.0.0.1:$SUP_PORT/health" >/dev/null 2>&1; then
    echo
    echo "supervisor: did NOT become healthy — last log lines:" >&2
    tail -n 20 "$SUP_LOG" >&2 || true
    exit 1
  fi
fi

# ── 2. Docker stack (db + api + web) ──────────────────────────────────────────
# up.sh re-sources deploy/.env so compose interpolation can't be fooled by stale
# shell exports, then runs `docker compose up -d` (or any forwarded subcommand).
echo "compose: rebuilding api + web (db left running, started via depends_on)…"
exec bash "$SCRIPT_DIR/up.sh" "$@"
