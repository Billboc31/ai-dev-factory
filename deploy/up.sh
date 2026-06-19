#!/usr/bin/env bash
# Start the Docker stack (api + web) with deploy/.env as the authoritative
# source for compose variable interpolation (HOST_RUNTIME_ROOT, HOST_SANDBOX_ROOT…).
#
# Why this exists: `docker compose` interpolates ${VAR} from the *shell*
# environment first, then from the root .env file. A stale `HOST_RUNTIME_ROOT`
# exported in an interactive shell silently overrides deploy/.env and makes the
# container mount the wrong runtime root (→ "project not found"). Sourcing
# deploy/.env here re-exports the correct values so compose can't be fooled.
#
# Usage:
#   bash deploy/up.sh            # == docker compose up -d
#   bash deploy/up.sh up         # explicit subcommand
#   bash deploy/up.sh logs -f    # any docker compose subcommand/flags

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090,SC1091
  source "$ENV_FILE"
  set +a
  echo "compose: loaded $ENV_FILE (HOST_RUNTIME_ROOT=${HOST_RUNTIME_ROOT:-<unset>})"
else
  echo "compose: WARNING — $ENV_FILE not found; copy deploy/.env.example and edit it" >&2
fi

if [ "$#" -eq 0 ]; then
  exec docker compose up -d
fi
exec docker compose "$@"
