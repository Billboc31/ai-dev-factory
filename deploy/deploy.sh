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
# shellcheck disable=SC1091
source "$SCRIPT_DIR/load-env.sh"
ENV_FILE="$SCRIPT_DIR/.env"
if load_deploy_env "$ENV_FILE"; then
  echo "deploy: loaded $ENV_FILE (RUNTIME_DB_BACKEND=${RUNTIME_DB_BACKEND:-sqlite})"
else
  echo "deploy: WARNING — $ENV_FILE not found; copy deploy/.env.example and edit it" >&2
fi

# Command passed to run_ticket / run_daemon workers (--exec-cmd). Without --model,
# Claude Code defaults to Opus (expensive). Sonnet is the deploy default.
export DAEMON_EXEC_CMD="${DAEMON_EXEC_CMD:-claude --dangerously-skip-permissions --model sonnet}"
echo "deploy: DAEMON_EXEC_CMD=$DAEMON_EXEC_CMD"

SUP_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
SUP_LOG="${TMPDIR:-/tmp}/adf-supervisor.log"

# ── 1. Host supervisor ───────────────────────────────────────────────────────
# On a real (re)deploy we RESTART the supervisor so host-side code changes
# (services/supervisor, tools/agent_runner) take effect: uvicorn runs without
# --reload, so a supervisor left running after a `git pull` keeps serving stale
# code and silently 404s newly added routes. For non-deploy subcommands
# (logs, down, ps, …) we only ensure it is running and never restart it.
_is_deploy=false
if [ "$#" -eq 0 ] || [ "${1:-}" = "up" ]; then
  _is_deploy=true
fi

_start_supervisor() {
  echo "supervisor: starting in background (log → $SUP_LOG)"
  nohup bash "$SCRIPT_DIR/start_supervisor.sh" >"$SUP_LOG" 2>&1 &
  disown || true
  printf "supervisor: waiting for health"
  for _ in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:$SUP_PORT/health" >/dev/null 2>&1; then
      echo " — ok (127.0.0.1:$SUP_PORT)"
      return 0
    fi
    printf "."
    sleep 1
  done
  echo
  echo "supervisor: did NOT become healthy — last log lines:" >&2
  tail -n 20 "$SUP_LOG" >&2 || true
  return 1
}

if lsof -nP -iTCP:"$SUP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if [ "$_is_deploy" = true ]; then
    echo "supervisor: restarting to pick up host code changes…"
    pkill -f "supervisor.main:app" 2>/dev/null || true
    for _ in $(seq 1 10); do
      lsof -nP -iTCP:"$SUP_PORT" -sTCP:LISTEN >/dev/null 2>&1 || break
      sleep 1
    done
    _start_supervisor || exit 1
  else
    echo "supervisor: already running on 127.0.0.1:$SUP_PORT — leaving it"
  fi
else
  _start_supervisor || exit 1
fi

# ── 2. Docker stack (db + api + web) ──────────────────────────────────────────
# up.sh re-sources deploy/.env so compose interpolation can't be fooled by stale
# shell exports, then runs `docker compose up -d` (or any forwarded subcommand).
echo "compose: rebuilding api + web (db left running, started via depends_on)…"
exec bash "$SCRIPT_DIR/up.sh" "$@"
