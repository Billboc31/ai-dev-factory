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
#   bash deploy/up.sh            # rebuild + recreate ONLY api & web (db untouched)
#   bash deploy/up.sh up         # explicit subcommand (no rebuild)
#   bash deploy/up.sh logs -f    # any docker compose subcommand/flags

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/load-env.sh"
ENV_FILE="$SCRIPT_DIR/.env"
if load_deploy_env "$ENV_FILE"; then
  echo "compose: loaded $ENV_FILE (HOST_RUNTIME_ROOT=${HOST_RUNTIME_ROOT:-<unset>})"
else
  echo "compose: WARNING — $ENV_FILE not found; copy deploy/.env.example and edit it" >&2
fi

if [ "$#" -eq 0 ]; then
  # Default redeploy: rebuild + recreate ONLY the application services.
  # The db (postgres:16-alpine, no build context) is intentionally NOT
  # rebuilt or recreated — it is started on demand through api's
  # depends_on, and its data lives in the adf-db-data named volume, so a
  # redeploy never touches the database.
  exec docker compose up -d --build api web
fi
exec docker compose "$@"
