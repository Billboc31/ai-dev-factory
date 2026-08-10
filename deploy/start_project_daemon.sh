#!/usr/bin/env bash
# Canonical host launcher for a managed-project daemon.
#
# Prevents the classic new-project footguns:
#   - wrong cwd → poll ai-dev-factory issues instead of the target repo
#   - inherited PROJECT_NAME=ai-dev-factory → rows/batches in the wrong project
#   - system Python without psycopg while RUNTIME_DB_BACKEND=postgres
#
# Usage:
#   bash deploy/start_project_daemon.sh iptvflix /Users/you/iptvflix
#   bash deploy/start_project_daemon.sh timizer-like /Users/you/timizer-like Billboc31/timizer-like
set -euo pipefail

PROJECT_ID="${1:?usage: start_project_daemon.sh <project_id> <project_root> [owner/repo]}"
PROJECT_ROOT="${2:?usage: start_project_daemon.sh <project_id> <project_root> [owner/repo]}"
ISSUE_REPO="${3:-}"

FACTORY_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/$PROJECT_ID}"
VENV_PY="${FACTORY_ROOT}/.venv/bin/python"
EXEC_CMD="${AI_DEV_FACTORY_EXEC_CMD:-claude --dangerously-skip-permissions --model sonnet}"

if [[ ! -x "$VENV_PY" ]]; then
  echo "error: factory venv python missing at $VENV_PY" >&2
  echo "       create it (install deps including psycopg) before launching daemons" >&2
  exit 2
fi
if [[ ! -d "$PROJECT_ROOT/.git" && ! -f "$PROJECT_ROOT/.git" ]]; then
  echo "error: project root is not a git checkout: $PROJECT_ROOT" >&2
  exit 2
fi

if [[ -z "$ISSUE_REPO" ]]; then
  ORIGIN_URL="$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null || true)"
  if [[ "$ORIGIN_URL" =~ github.com[:/]([^/]+)/([^/.]+) ]]; then
    ISSUE_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  else
    echo "error: pass owner/repo as 3rd arg (could not parse git origin)" >&2
    exit 2
  fi
fi

# Load shared RUNTIME_DB_* when present (Postgres for batches / dashboard).
if [[ -f "$FACTORY_ROOT/deploy/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$FACTORY_ROOT/deploy/.env"
  set +a
fi

mkdir -p "$RUNTIME_ROOT"/{runs,logs,state,worktrees}

export PROJECT_NAME="$PROJECT_ID"
export AI_DEV_FACTORY_RUNTIME_ROOT="$RUNTIME_ROOT"

echo "starting project daemon"
echo "  project_id   = $PROJECT_ID"
echo "  project_root = $PROJECT_ROOT"
echo "  runtime_root = $RUNTIME_ROOT"
echo "  issue_repo   = $ISSUE_REPO"
echo "  python       = $VENV_PY"
echo "  RUNTIME_DB   = ${RUNTIME_DB_BACKEND:-sqlite}"

exec "$VENV_PY" "$FACTORY_ROOT/tools/agent_runner/run_daemon.py" \
  --exec-cmd "$EXEC_CMD" \
  --poll-issues --issue-label ai-ready \
  --issue-repo "$ISSUE_REPO" \
  --auto-commit --auto-push --auto-include-code \
  --worktrees-dir "$RUNTIME_ROOT/worktrees" \
  --project-root "$PROJECT_ROOT" \
  --project "$PROJECT_ID" \
  --max-workers "${MAX_WORKERS:-5}"
