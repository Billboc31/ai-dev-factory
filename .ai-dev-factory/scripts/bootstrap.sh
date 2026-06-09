#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Verify required tools are available on the host
for tool in git docker gh claude; do
  if ! command -v "$tool" &>/dev/null; then
    echo "bootstrap: ERROR — required tool not found: $tool" >&2
    exit 1
  fi
done
echo "bootstrap: all required tools present"

# Create Python venv if absent, then install dependencies
if [ ! -f ".venv/bin/activate" ]; then
  echo "bootstrap: creating Python venv at .venv"
  python3 -m venv .venv
fi
source .venv/bin/activate

if [ -f "services/control_api/requirements.txt" ]; then
  echo "bootstrap: installing Python dependencies"
  pip install -q -r services/control_api/requirements.txt
fi

# Create deploy/.env from the example template if it does not yet exist
if [ ! -f "deploy/.env" ]; then
  if [ -f "deploy/.env.example" ]; then
    echo "bootstrap: WARNING — deploy/.env missing; copying from .env.example (edit before first run)" >&2
    cp "deploy/.env.example" "deploy/.env"
  else
    echo "bootstrap: WARNING — deploy/.env missing and no .env.example found; create it manually" >&2
  fi
fi

# Load env to resolve AI_DEV_FACTORY_RUNTIME_ROOT for the runtime root setup
[ -f deploy/.env ] && source deploy/.env || true
AI_DEV_FACTORY_RUNTIME_ROOT="${AI_DEV_FACTORY_RUNTIME_ROOT:-$HOME/runtime/ai-dev-factory}"
export AI_DEV_FACTORY_RUNTIME_ROOT

# Initialise the runtime directory structure (idempotent)
bash deploy/bootstrap.sh

# Create the PID directory used by start.sh / stop.sh
mkdir -p "$PROJECT_ROOT/.ai-dev-factory/run"

echo "bootstrap: done — edit deploy/.env then run start.sh"
