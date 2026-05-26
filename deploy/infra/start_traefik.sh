#!/usr/bin/env bash
# Idempotently start the **global** Traefik reverse proxy.
#
# Traefik is shared infrastructure — there must only ever be ONE instance
# running per host. Running this multiple times is safe: ``docker compose
# up -d`` is a no-op when the service is already up.
#
# Sandbox compose runs (``docker compose -p sandbox-… up -d``) MUST NOT
# bring Traefik up themselves; the service definition lives in a
# dedicated compose file (``docker-compose.traefik.yml``) so the root
# project's compose file (``docker-compose.yml``) never accidentally
# spawns a Traefik per sandbox — see the original failure mode:
#
#     Container sandbox-ai-dev-factory-…-traefik-1 Starting
#     Bind for 0.0.0.0:80 failed: port is already allocated
#
# Usage::
#
#     bash deploy/infra/start_traefik.sh         # start (idempotent)
#     bash deploy/infra/start_traefik.sh down    # stop

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.traefik.yml"
PROJECT_NAME="ai-dev-factory-infra"

# Source deploy/.env if it exists so HOST_RUNTIME_ROOT is interpolated
# correctly in the compose file. Falls back to the documented default
# baked into the compose file when absent.
ENV_FILE="$REPO_ROOT/deploy/.env"
COMPOSE_ENV_ARGS=()
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
  COMPOSE_ENV_ARGS=(--env-file "$ENV_FILE")
fi

action="${1:-up}"
case "$action" in
  up|start)
    echo "traefik: starting global proxy (project=$PROJECT_NAME)"
    docker compose \
      -f "$COMPOSE_FILE" \
      -p "$PROJECT_NAME" \
      "${COMPOSE_ENV_ARGS[@]}" \
      up -d traefik
    echo "traefik: dashboard at http://traefik.ai-dev-factory.localhost"
    ;;
  down|stop)
    echo "traefik: stopping global proxy"
    docker compose \
      -f "$COMPOSE_FILE" \
      -p "$PROJECT_NAME" \
      "${COMPOSE_ENV_ARGS[@]}" \
      down
    ;;
  *)
    echo "usage: $0 [up|down]" >&2
    exit 2
    ;;
esac
