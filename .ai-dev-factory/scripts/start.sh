#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# ── Load deploy/.env ──────────────────────────────────────────────────────────
ENV_FILE="$PROJECT_ROOT/deploy/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
else
  echo "ERROR: deploy/.env not found — run bootstrap.sh first" >&2
  exit 1
fi

# ── Activate host venv ────────────────────────────────────────────────────────
if [ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
  echo "ERROR: .venv not found — run bootstrap.sh first" >&2
  exit 1
fi
source "$PROJECT_ROOT/.venv/bin/activate"

# ── 1. Supervisor (must start before Docker so API can register path maps) ───
SUPERVISOR_PORT="${AI_DEV_FACTORY_SUPERVISOR_PORT:-8090}"
if lsof -ti tcp:"$SUPERVISOR_PORT" &>/dev/null; then
  echo "start: supervisor already listening on :$SUPERVISOR_PORT — skipping"
else
  echo "start: starting supervisor on :$SUPERVISOR_PORT"
  nohup bash "$PROJECT_ROOT/deploy/start_supervisor.sh" \
    >"${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}/logs/supervisor.log" 2>&1 &
  # Wait up to 10 s for the supervisor to become ready.
  for i in $(seq 1 10); do
    if curl -sf "http://127.0.0.1:$SUPERVISOR_PORT/health" &>/dev/null; then
      echo "start: supervisor ready"
      break
    fi
    sleep 1
    if [ "$i" -eq 10 ]; then
      echo "ERROR: supervisor did not become ready within 10 s" >&2
      exit 1
    fi
  done
fi

# ── 2. Docker stack (api + web) ───────────────────────────────────────────────
echo "start: bringing up Docker stack"
docker compose up -d

# ── 3. Daemon (optional — set START_DAEMON=1 to enable) ──────────────────────
if [ "${START_DAEMON:-0}" = "1" ]; then
  if pgrep -f "run_daemon.py" &>/dev/null; then
    echo "start: daemon already running — skipping"
  else
    ISSUE_REPO="${GITHUB_REPO:-Billboc31/ai-dev-factory}"
    EXEC_CMD="${DAEMON_EXEC_CMD:-claude --dangerously-skip-permissions}"
    INTERVAL="${DAEMON_INTERVAL:-30}"
    RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}"
    echo "start: starting daemon (repo=$ISSUE_REPO, interval=${INTERVAL}s)"
    nohup python "$PROJECT_ROOT/tools/agent_runner/run_daemon.py" \
      --exec-cmd "$EXEC_CMD" \
      --poll-issues \
      --issue-repo "$ISSUE_REPO" \
      --auto-commit --auto-push --auto-include-code \
      --interval "$INTERVAL" \
      >"${RUNTIME_ROOT}/logs/daemon.log" 2>&1 &
    echo "start: daemon started (pid $!)"
  fi
else
  echo "start: daemon not started (set START_DAEMON=1 to enable)"
fi

echo "start: stack is up — API: http://localhost:8080  Dashboard: http://localhost:3000  Supervisor: http://localhost:${SUPERVISOR_PORT}"
