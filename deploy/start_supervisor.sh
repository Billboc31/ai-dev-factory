#!/usr/bin/env bash
# Start the AI dev factory host supervisor.
# Run this on the host before starting the Docker stack.
#
# Usage:
#   bash deploy/start_supervisor.sh
#
# The supervisor binds to 127.0.0.1:8090. Docker containers reach it via
# host.docker.internal:8090. Set AI_DEV_FACTORY_SUPERVISOR_URL accordingly
# in docker-compose.yml (see the commented example there).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"
source .venv/bin/activate

export AI_DEV_FACTORY_PROJECT_ROOT="${AI_DEV_FACTORY_PROJECT_ROOT:-$PROJECT_ROOT}"
export AI_DEV_FACTORY_RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}"

exec uvicorn services.supervisor.main:app --host 127.0.0.1 --port 8090
