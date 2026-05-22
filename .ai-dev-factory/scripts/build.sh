#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PROJECT_ROOT"

# ── Load env (needed for HOST_RUNTIME_ROOT used by compose) ──────────────────
ENV_FILE="$PROJECT_ROOT/deploy/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
fi

echo "build: building Docker images (api, web)"
docker compose build --pull

echo "build: done"
