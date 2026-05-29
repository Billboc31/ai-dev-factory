I now have everything I need. Here is the implementation plan:

---

## Objective

Replace the fragile per-sandbox compose-default network + dynamic `docker network connect` pattern with a single pre-created `ai-dev-factory-runtime` ingress network that Traefik always belongs to and that every sandbox service explicitly joins, using per-environment DNS aliases to keep service discovery deterministic across concurrent environments.

## Included

### Infrastructure — shared ingress network

**`deploy/infra/docker-compose.traefik.yml`**
- Declare and create the `ai-dev-factory-runtime` bridge network (driver: bridge) directly in the Traefik compose file — this makes Traefik the lifecycle owner of the ingress network.
- Connect the `traefik` service to `ai-dev-factory-runtime` in its `networks:` section (in addition to the default infra network).

### Sandbox services — explicit network membership

**`docker-compose.yml`**
- Add a top-level `networks:` block declaring `ai-dev-factory-runtime` as external.
- Attach both `api` and `web` services to `ai-dev-factory-runtime` in their `networks:` section alongside `default`.
- Give each service a unique, sandbox-scoped network alias using the already-injected `SANDBOX_ID` env var:
  - `api` → alias `sandbox-${SANDBOX_ID}-api`
  - `web` → alias `sandbox-${SANDBOX_ID}-web`
- Keep the compose `default` network for intra-sandbox communication (api ↔ web).

### Route backend URLs — deterministic aliases

**`services/control_api/services/proxy_network.py`**
- Remove `attach_traefik_to_compose_project()`, `detach_traefik_from_compose_project()`, and `resolve_route_backends()` — the attach/detach pattern is the root cause of instability and is no longer needed.
- Remove `host_port_backend_urls()` fallback — the host-port path was masking the real networking failure; eliminate it.
- Expose a single function `sandbox_backend_urls(sandbox_id)` returning:
  - `api` → `http://sandbox-{id}-api:8080`
  - `web` → `http://sandbox-{id}-web:80`
- Keep `compose_default_network_name()` only if still used elsewhere; otherwise remove.

**`services/control_api/services/proxy_manager.py`**
- Replace the `resolve_route_backends(ports, compose_project)` call in `register()` with `sandbox_backend_urls(sandbox_id)`.
- Remove the `compose_project` parameter from `register()` (network attachment no longer happens here).
- Remove the `detach_traefik_from_compose_project()` call from `unregister()` (Traefik stays on `ai-dev-factory-runtime` permanently; no per-env detach needed).
- Remove imports of the deleted functions from `proxy_network`.

**`services/control_api/services/sandbox_manager.py`**
- Remove `compose_project=state.compose_project` from the `ProxyManager.register()` call in `start()`.
- Add `ensure_runtime_network()` call before `docker compose up` (or rely on Traefik infra pre-creating it — see below).

### Runtime network lifecycle

**`services/control_api/services/infra_service_manager.py`** (or `traefik_manager.py`)
- Add a `ensure_runtime_network()` helper: runs `docker network create --driver bridge ai-dev-factory-runtime` idempotently (ignore error if it already exists).
- Call `ensure_runtime_network()` inside `_ensure_traefik_reverse_proxy()` before starting Traefik — this guarantees the network is present whenever infra is up.

### Non-sandbox default handling

**`docker-compose.yml`** (dev / direct `docker compose up` without sandbox env)
- Use `${SANDBOX_ID:-default}` in the network aliases so the file remains valid when `SANDBOX_ID` is not set (no functional impact — no route files reference `sandbox-default-*`).
- Document in the compose file header that `ai-dev-factory-runtime` must exist before `docker compose up`; point to `start_traefik.sh` as the creator.

### Tests

- `tests/integration/test_multi_env_networking.py` (new):
  - Start two sandboxes concurrently; assert both URLs reachable via Traefik and no network conflicts.
- `tests/integration/test_redeploy_stability.py` (new):
  - Redeploy the same sandbox twice; assert route stays valid after second deploy.
- `tests/integration/test_env_cleanup.py` (new):
  - Destroy one sandbox while a second is running; assert second sandbox routes unaffected and `ai-dev-factory-runtime` still exists.
- Update existing `proxy_network`/`proxy_manager` unit tests to remove references to `attach_traefik_to_compose_project` and `resolve_route_backends`.

## Excluded

- Switching Traefik from file provider to Docker label discovery (separate architectural decision, not needed to fix the networking instability).
- Per-environment internal networks (`sandbox-{id}-internal`) for api ↔ db isolation — the ticket notes this as optional; deferred.
- Changes to the supervisor port allocation or host-side supervisor lifecycle.
- Modifying the healthcheck or smoke test scripts.
- Migrating or restarting currently running sandboxes — a process restart picks up the new compose config.
- Any change to deployer-mode flows (the deployer does not use `SandboxManager` or `ProxyManager`).
- TLS / HTTPS configuration.

## Acceptance criteria

1. After `bash deploy/infra/start_traefik.sh up`, `docker network ls` shows `ai-dev-factory-runtime` with Traefik connected to it — no manual `docker network connect` invoked.
2. Creating and starting a sandbox immediately produces working pretty URLs (`sandbox-{id}.ai-dev-factory.localhost`, `api.sandbox-{id}.ai-dev-factory.localhost`) without any post-start manual intervention.
3. `proxy_network.py` contains no `docker network connect` or `docker network disconnect` calls.
4. Route backend URLs in generated `.yml` files are of the form `http://sandbox-{id}-api:8080` (not `http://api:8080` and not `http://host.docker.internal:*`).
5. Two sandboxes running concurrently each respond correctly through Traefik with no cross-environment DNS collision.
6. Destroying sandbox A does not break sandbox B's routes or remove `ai-dev-factory-runtime`.
7. Redeploying the same sandbox twice leaves a valid, reachable route with no orphaned networks.
8. All existing `proxy_manager` and `proxy_network` unit tests pass after removing the deleted functions; the three new integration tests pass.
