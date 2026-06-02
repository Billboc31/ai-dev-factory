Now I have enough context to write the plan. Let me produce it.

## Objective

Ensure the SANDBOX_ID (environment slug) is propagated consistently from environment selection through Docker Compose invocation to Traefik route generation, so network aliases and backend URLs always match. Eliminate the silent `:-default` fallback in `docker-compose.yml` that causes the current `sandbox-main-api` vs `sandbox-default-api` mismatch.

## Included

**`docker-compose.yml`** (lines 64, 79):
- Change `${SANDBOX_ID:-default}` → `${SANDBOX_ID}` (no fallback) for both `sandbox-${SANDBOX_ID:-default}-api` and `sandbox-${SANDBOX_ID:-default}-web` network aliases.
- A missing SANDBOX_ID will now cause compose to produce an empty alias and fail visibly rather than silently aliasing everything to `default`.

**`services/control_api/services/sandbox_runtime_deploy.py`**:
- Audit the compose invocation: confirm `SANDBOX_ID` is present in the environment dict passed to the subprocess (currently `extra_env["SANDBOX_ID"] = state.id` at line 74). If it is absent or not reaching the subprocess, fix the injection.
- Add an explicit pre-deploy guard: raise `RuntimeError` if `SANDBOX_ID` is empty or unset before the compose call.
- Confirm `proxy_manager.register()` is called with the same slug as `state.id`, not a re-derived value.

**`services/control_api/services/proxy_network.py`**:
- Expose a `canonical_sandbox_slug(sandbox_id: str) -> str` helper that applies `_to_docker_safe_alias` and assert-validates the result is non-empty. This becomes the single normalization entry point used everywhere.

**`services/control_api/services/proxy_manager.py`**:
- Replace any direct use of `sandbox_id` for alias/backend-URL generation with `canonical_sandbox_slug(sandbox_id)` from `proxy_network.py` (likely already done via `sandbox_backend_urls()`, but verify).

**`tools/agent_runner/run_sandbox.py`**:
- Verify that the host-side compose invocation injects SANDBOX_ID into the subprocess environment (the `extra_env` path). Add assertion if it is missing before compose startup.

**Validation probe** (in the deploy flow — `sandbox_runtime_deploy.py` or a new `_validate_aliases` helper in the same file):
- After compose up, run `docker exec <traefik-container> wget -q -O- http://sandbox-<slug>-api:8080/health` using the canonical slug.
- Fail the deploy if the probe does not return HTTP 200, with a clear error message that names the alias attempted.

**Tests** (existing test files for proxy or sandbox deploy, wherever they live):
- Add a unit test that asserts `sandbox_dns_aliases("main")` produces `{"api": "sandbox-main-api", "web": "sandbox-main-web"}`.
- Add a test that asserts `sandbox_dns_aliases("")` or `sandbox_dns_aliases(None)` raises rather than silently producing `"sandbox--api"`.

## Excluded

- Changes to how sandbox IDs are generated (UUID vs timestamp — not the cause of this bug).
- Changes to Traefik configuration files or routing rules beyond the backend URL alignment already described.
- Multi-sandbox concurrency testing or load-balancing logic.
- The broader agent runner orchestration in `run_sandbox.py` beyond the SANDBOX_ID injection fix.
- Any UI or control-API endpoint changes.
- Migration of existing running sandboxes named `default`.

## Acceptance criteria

1. `docker inspect <api-container>` shows alias `sandbox-main-api` when the environment is `main` (no `sandbox-default-api` alias present).
2. The generated Traefik route file at `routes/main.yml` (or equivalent) lists `http://sandbox-main-api:8080` as the API backend URL.
3. `docker exec <traefik-container> wget -q -O- http://sandbox-main-api:8080/health` returns HTTP 200.
4. No `sandbox-default-*` aliases appear in `docker network inspect ai-dev-factory-runtime` unless an environment is explicitly named `default`.
5. Deploying an environment with SANDBOX_ID unset or empty fails immediately with an explicit error message before compose starts.
6. Traefik-routed URLs (`http://api.sandbox-main.ai-dev-factory.localhost/...`) return real backend responses (not 502).
7. A second environment deployed concurrently (e.g., `dev`) produces `sandbox-dev-api` aliases and independent Traefik routes without interfering with `main`.
