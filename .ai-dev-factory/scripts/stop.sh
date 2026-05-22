#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# ── 1. Daemon ─────────────────────────────────────────────────────────────────
if pgrep -f "run_daemon.py" &>/dev/null; then
  echo "stop: stopping daemon"
  pkill -TERM -f "run_daemon.py" || true
  sleep 2
  pkill -KILL -f "run_daemon.py" 2>/dev/null || true
else
  echo "stop: daemon not running"
fi

# ── 2. Docker stack ───────────────────────────────────────────────────────────
if docker compose ps --quiet 2>/dev/null | grep -q .; then
  echo "stop: stopping Docker stack"
  docker compose down
else
  echo "stop: Docker stack not running"
fi

# ── 3. Supervisor ─────────────────────────────────────────────────────────────
if pgrep -f "services.supervisor.main" &>/dev/null; then
  echo "stop: stopping supervisor"
  pkill -TERM -f "services.supervisor.main" || true
  sleep 2
  pkill -KILL -f "services.supervisor.main" 2>/dev/null || true
else
  echo "stop: supervisor not running"
fi

echo "stop: all services stopped"
