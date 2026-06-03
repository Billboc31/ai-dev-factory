Now I have a complete understanding of the codebase. Let me write the plan.

---

## Objective

Ensure that `api` and `web` containers always join the `ai-dev-factory-runtime` shared ingress network with correct per-sandbox DNS aliases during the environment deploy flow, so Traefik can resolve backend targets regardless of which branch's `docker-compose.yml` is used.

## Included

**Root cause**: `start.sh` runs `docker compose up -d` against the worktree's `docker-compose.yml`. If the worktree is on a branch that predates the T164 network config (or if `ai-dev-factory-runtime` is absent from that compose file for any reason), containers are created on `sandbox-<id>_default` only. `deploy_operational_runtime()` creates the network via `_ensure_required_infra()` before scripts run, but compose only attaches containers to networks it knows about from its file.

**Fix 1 — `.ai-dev-factory/scripts/start.sh`** (primary fix):
After `docker compose up -d`, add a post-compose block that, when `SANDBOX_ID` is non-empty:
- Queries the compose project for the `api` container ID (`docker compose -p "$COMPOSE_PROJECT_NAME" ps -q api`)
- Same for `web`
- For each container: check if it is already attached to `ai-dev-factory-runtime` (`docker inspect <id> --format '{{json .NetworkSettings.Networks}}'`)
- If not attached: `docker network connect --alias sandbox-${SANDBOX_ID}-api ai-dev-factory-runtime <id>` (and same for web)
- Log success/skip per container
- Do NOT fail the entire deploy if `docker network connect` returns a benign "already connected" error

**Fix 2 — `services/control_api/services/sandbox_manager.py`, `SandboxManager.start()`** (defensive fix):
Call `ensure_runtime_network()` (already in `infra_service_manager.py`) before `_run_compose(state, "up", "-d")`. Without this, when `docker-compose.yml` declares `ai-dev-factory-runtime` as `external: true` and the network does not yet exist, compose fails hard and the container never starts.

**Tests**:
- `tests/test_start_sh_network_attach.py` (new): Verify that the post-compose block connects containers to `ai-dev-factory-runtime` when they lack it, and is idempotent when they already have it.
- `tests/test_sandbox_manager_network.py` or extend `tests/test_sandbox_runtime_deploy.py`: Verify `ensure_runtime_network()` is called before `_run_compose` in `SandboxManager.start()`.

## Excluded

- Changes to `docker-compose.yml` (already correct from T164).
- Changes to the Traefik compose file.
- Changes to `proxy_manager.py`, `proxy_network.py`, or route file generation.
- Changes to SANDBOX_ID propagation (fixed in T168/T169).
- Support for deploy profiles other than `api` + `web`.
- Network cleanup / disconnect on sandbox stop.

## Acceptance criteria

- `docker inspect <api-container> --format '{{json .NetworkSettings.Networks}}' | jq 'keys'` returns `["ai-dev-factory-runtime", "sandbox-<id>_default"]` after a full environment deploy.
- Same check passes for the `web` container.
- `docker exec <traefik-container> wget -qO- http://sandbox-<id>-api:8080/health` returns HTTP 200.
- The post-compose `docker network connect` step is idempotent: re-running `start.sh` against an already-running stack does not fail.
- `SandboxManager.start()` does not abort with "Network ai-dev-factory-runtime declared as external, but could not be found" when the network pre-exists from T164's compose config and infra was not previously bootstrapped.
- All new tests pass; existing tests are unaffected.
