Implementation complete. Here's a summary:

## Files modified

### `.ai-dev-factory/scripts/start.sh`
- **Snapshot/restore**: Added `__SB_SANDBOX_ID="${SANDBOX_ID:-}"` before `source deploy/.env`, then restores `SANDBOX_ID="${__SB_SANDBOX_ID:-${SANDBOX_ID:-}}"` and `export SANDBOX_ID` afterward — same pattern as all other injected env vars. This prevents `deploy/.env` from silently overriding the caller-injected value.
- **Fail-fast guard**: After restore, exits non-zero with a clear error if `COMPOSE_PROJECT_NAME` is set (named-env mode) but `SANDBOX_ID` is empty.
- **Explicit compose invocation**: `SANDBOX_ID="$SANDBOX_ID" docker compose --env-file deploy/.env up -d` — the inline env var takes precedence over `--env-file`, preventing fallback to `${SANDBOX_ID:-default}` in `docker-compose.yml`.

### `services/control_api/services/sandbox_runtime_deploy.py`
- **Import**: Added `from .proxy_network import sandbox_dns_aliases`.
- **Pre-flight check**: Before `rs._run_scripts(...)`, validates that `extra_env["SANDBOX_ID"]` is non-empty and equals `state.id`. If either check fails, the supervisor is stopped cleanly and `OperationalDeployResult(success=False, ...)` is returned with a descriptive message — no compose is ever invoked.

### `services/control_api/services/proxy_manager.py`
No change needed — DNS alias logging via `sandbox_dns_aliases(sandbox_id)` was already present in the `register()` method on the main branch.
