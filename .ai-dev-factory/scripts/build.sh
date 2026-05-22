#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

[ -f deploy/.env ] && source deploy/.env || true

echo "build: building Docker images..."
if [ -f deploy/.env ]; then
  docker compose --env-file deploy/.env build
else
  docker compose build
fi

echo "build: done"
