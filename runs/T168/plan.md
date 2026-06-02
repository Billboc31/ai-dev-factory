I now have a complete picture of the codebase. Let me write the plan.

---

## Objective

Fix the SANDBOX_ID mismatch that causes Traefik routes to target `sandbox-main-api` while Docker Compose registers aliases as `sandbox-default-api`, resulting in 502 errors on all routed sandbox/environment URLs.

## Included

### 1. `.ai-dev-factory/scripts/start.sh` — Preserve and export SANDBOX_ID

Add `SANDBOX_ID` to the existing snapshot/restore/export pattern (currently only covers `API_PORT`, `WEB_PORT`, `AI_DEV_FACTORY_SUPERVISOR_*`, etc.):

```bash
# Before source deploy/.env:
__SB_SANDBOX_ID="${SANDBOX_ID:-}"

# After source deploy/.env, before docker compose:
SANDBOX_ID="${__SB_SANDBOX_ID:-${SANDBOX_ID:-}}"
export SANDBOX_ID
unset __SB_SANDBOX_ID
```

Add a fail-fast guard: if `COMPOSE_PROJECT_NAME` is set (sandbox/environment mode) but `SANDBOX_ID` is empty after restore, print a clear error and exit non-zero before `docker compose up`.

### 2. `.ai-dev-factory/scripts/start.sh` — Explicit SANDBOX_ID in `docker compose` call

Pass `SANDBOX_ID` explicitly to the `docker compose` invocation so it cannot silently fall back to the `${SANDBOX_ID:-default}` placeholder in `docker-compose.yml`:

```bash
SANDBOX_ID="$SANDBOX_ID" docker compose --env-file deploy/.env up -d
```

(Both `--env-file` and inline env var are needed: the env file carries the rest of the deployment config; the inline var guarantees SANDBOX_ID is not shadowed.)

### 3. `services/control_api/services/sandbox_runtime_deploy.py` — Pre-flight consistency check

In `deploy_operational_runtime()`, before calling `rs._run_scripts(...)`, validate that `extra_env["SANDBOX_ID"]` is non-empty and matches the aliases that `proxy_network.sandbox_dns_aliases(state.id)` would produce. If the value is empty or diverges from `state.id`, raise immediately with a descriptive message rather than producing a silent 502.

This uses the already-imported `proxy_network` functions — no new dependencies.

### 4. `services/control_api/services/proxy_manager.py` — Log the expected alias at registration time

In `ProxyManager.register()`, log the expected Docker DNS aliases (from `sandbox_dns_aliases(sandbox_id)`) alongside the backend URL. This makes the route file and the compose alias both visible in the same log line and simplifies future debugging.

### 5. `services/control_api/services/sandbox_runtime_deploy.py` — Validation probe uses canonical alias

In `_register_proxy_routes_after_compose()`, ensure the backend diagnostics probe (already delegated to `rs._log_proxy_backend_diagnostics(state.id, log_path)`) is consistent: `probe_backend_from_traefik_container` must resolve the alias `sandbox-<slug>-api` derived from `proxy_network.sandbox_dns_aliases(state.id)`, not a hardcoded or fallback value. Verify this is already using `sandbox_dns_aliases`; add the call if it is not.

## Excluded

- Changes to `docker-compose.yml` aliases — `${SANDBOX_ID:-default}` is correct and intentional; the fix is upstream (propagation), not in the compose template.
- Multi-environment concurrent isolation logic — the fix ensures each env uses its own slug; scheduling or ordering of multiple envs is out of scope.
- Alias handling in the deployer/CD branch flow (`deployer_runner`) — different deploy path, separate ticket if needed.
- Port allocation or supervisor logic changes.
- Any changes to `proxy_network.py` or `proxy_route_files.py` — existing normalization logic is correct.

## Acceptance criteria

- `docker inspect <api-container>` shows alias `sandbox-main-api` when `state.id = "main"`.
- The route file generated in `proxy/routes/main.yml` points to `http://sandbox-main-api:8080`.
- `docker exec <traefik-container> wget http://sandbox-main-api:8080/health` returns HTTP 200.
- `sandbox-default-*` aliases do not appear unless the actual environment/sandbox ID is literally `"default"`.
- Deploying with a missing or empty SANDBOX_ID fails immediately with a human-readable error before `docker compose up` is called.
- Multiple named environments (`main`, `develop`, `feature-x`) deployed concurrently each get distinct aliases and routes without collision.
- Traefik-routed URLs return real backend responses (no 502) after a fresh environment deploy.
