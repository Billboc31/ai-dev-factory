# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T164/reviews/implementation-review.md
- generated at: 2026-05-29T15:22:11Z

---

---

# PR Review — T164: Replace Docker Compose v2.5-style environment networking

## Résumé

The architecture change is correct and solves the root problem. However, two call sites were missed when removing the `compose_project` parameter from `ProxyManager.unregister()`, producing `TypeError` at runtime.

---

## Points validés

- `proxy_network.py` cleanly rewritten: `RUNTIME_NETWORK_NAME`, `sandbox_backend_urls()`, no `subprocess`/`docker network connect`.
- `proxy_manager.py:register()` correctly calls `sandbox_backend_urls(sandbox_id)`, no `compose_project`.
- `docker-compose.traefik.yml` connects Traefik to `ai-dev-factory-runtime`.
- `docker-compose.yml` declares `ai-dev-factory-runtime` as `external: true` with per-sandbox aliases using `${SANDBOX_ID:-default}`.
- Port alignment correct: API 8080, web 80 in both compose and `proxy_network.py`.
- `sandbox_manager.py:destroy()` (line 536) correctly calls `unregister()` without `compose_project`.
- `_dashboard.yml` protected from sandbox cleanup. `ensure_runtime_network()` idempotent.
- Integration tests for multi-env isolation, redeploy stability, and cleanup are thorough.

---

## Problèmes détectés

### [BLOCKING] B1 — `sandbox_runtime_deploy.py:389–393`

`ProxyManager.unregister()` called with `compose_project=state.compose_project` which no longer exists in the method signature. Raises `TypeError` uncaught in the deployment failure cleanup path, crashing `deploy_operational_runtime()` on any failed deployment after route registration.

**Fix:** Remove `compose_project=state.compose_project,` from lines 391.

### [BLOCKING] B2 — `run_sandbox.py:314–333` (`_unregister_proxy_route`)

Same stale kwarg: `compose_project=compose_project` passed to `ProxyManager.unregister()`. Caught by `try/except`, so no crash — but the route file is **never removed** on sandbox teardown, leaving stale subdomains pointing at recycled ports.

**Fix:** Remove `compose_project` parameter from `_unregister_proxy_route()` and from the `unregister()` call. Remove `compose_project=compose_project` from the call at `run_sandbox.py:1167`.

### [MINOR] M1 — `sandbox_runtime_deploy.py:284`

Stale docstring: "Attach Traefik to the compose network and write route file" — refers to the deleted `attach_traefik_to_compose_project()` pattern.

### [MINOR] M2 — Split network ownership

`ensure_runtime_network()` creates the network via `docker network create` before `TraefikManager().ensure_running()`, while `docker-compose.traefik.yml` also declares it as a compose-owned (non-external) network. Docker Compose v2 adopts pre-existing networks so this doesn't crash, but it's inconsistent with the plan's "Traefik compose as lifecycle owner" intent.

---

## Décision

The core architecture is sound. Two incomplete call-site cleanups (B1, B2) must be fixed before merge.

IMPLEMENTATION_FIX_REQUIRED
