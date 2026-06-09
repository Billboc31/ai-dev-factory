#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

[ -f deploy/.env ] && source deploy/.env || true

COMPOSE_PROJECT="${PROJECT_NAME:-ai-dev-factory}"

echo "build: building Docker images for project '$COMPOSE_PROJECT'"

_COMPOSE_ARGS=("--project-name" "$COMPOSE_PROJECT")
[ -f deploy/.env ] && _COMPOSE_ARGS+=("--env-file" "deploy/.env")

docker compose "${_COMPOSE_ARGS[@]}" build --parallel

echo "build: done"
