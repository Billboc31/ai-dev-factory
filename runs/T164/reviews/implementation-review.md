---

# PR Review — T164: Replace Docker Compose v2.5-style environment networking

## Résumé

Second review pass following `IMPLEMENTATION_FIX_REQUIRED`. The two blocking issues identified in the previous review (B1: stale `compose_project` kwarg in `sandbox_runtime_deploy.py`, B2: same in `run_sandbox.py`) are now fixed and verified against the actual diff. The core architecture — shared `ai-dev-factory-runtime` network with per-sandbox DNS aliases, zero dynamic `docker network connect` calls — is correct and complete.

## Vérifications effectuées

- Full `git diff main...HEAD` read for all 11 changed files
- Verified B1 fix: `sandbox_runtime_deploy.py:388–392` — `compose_project=` kwarg absent from `unregister()` call ✓
- Verified B2 fix: `run_sandbox.py:314–333` — `compose_project` removed from `_unregister_proxy_route()` signature and all call sites ✓
- Verified M1 fix: `sandbox_runtime_deploy.py:284` docstring updated ✓
- Read full `proxy_manager.py` post-change (not just diff) to confirm `_dashboard.yml` initialization
- Verified integration tests exercise the ticket's acceptance criteria scenarios

## Points validés

- **Networking architecture correct**: `ai-dev-factory-runtime` declared in `docker-compose.traefik.yml` (non-external, bridge), referenced as `external: true` in `docker-compose.yml`. Traefik is permanently on the shared network; sandboxes join via declarative aliases.
- **DNS aliases deterministic**: `sandbox-${SANDBOX_ID:-default}-api` / `sandbox-${SANDBOX_ID:-default}-web` — one alias per service per sandbox, no collision possible between concurrent environments.
- **Zero dynamic network mutation**: `proxy_network.py` is now 26 lines, no `subprocess`, no `docker network connect/disconnect`. Root cause of instability eliminated.
- **`ensure_runtime_network()`**: idempotent — ignores `"already exists"` / `"network with name"` stderr patterns. Called before `TraefikManager().ensure_running()`.
- **`_dashboard.yml` protected**: `ProxyManager.__init__` creates it on first use; `cleanup_stale_routes()` skips `_`-prefixed files.
- **`ports` param made optional not removed**: `ProxyManager.register(ports: dict[str, int] | None = None)` — existing callers not broken.
- **All acceptance criteria covered by tests**: multi-env isolation, redeploy stability, per-env cleanup with surviving sandbox unaffected.

## Problèmes détectés

### [MINOR] Dead parameters in `_register_proxy_route()` (`run_sandbox.py`)

`_register_proxy_route(sandbox_id, api_port, web_port, log_path, ...)` still accepts `api_port` and `web_port` in its signature, and the call site at line 1038 still passes them. However they are no longer forwarded to `ProxyManager.register()`. Both parameters are now dead code — accepted but ignored. No runtime impact; minor code smell.

### [MINOR] Dead parameter in `ProxyManager.register()`

`ports: dict[str, int] | None = None` is kept in the signature for back-compat but is never read. Acceptable as a transition aid; cleanup in a future ticket.

### [MINOR] M2 retained — Network ownership split (unchanged from prior review)

`ensure_runtime_network()` creates the network via `docker network create` before `docker-compose.traefik.yml` runs. Compose v2 adopts pre-existing networks with matching names, so no crash expected. However if the pre-created network's configuration ever diverges from what compose expects (labels, driver options), Compose may reject it. The risk is very low with a plain bridge network.

## Risques éventuels

- `SANDBOX_ID` unset at compose runtime falls back to the alias `sandbox-default-api/web`. Since no route file references that name in practice, there is no functional risk — just a cosmetic alias on the network. Low risk.
- If `ensure_runtime_network()` is called concurrently at infra start-up (e.g. two workers both start Traefik), both `docker network create` calls fire; the second gets an "already exists" error and is silently ignored. Safe.

## Décision

All blocking issues from the first review are fixed. The implementation correctly solves the T164 root cause, respects the planned scope, and is backed by comprehensive tests covering the ticket's three acceptance scenarios. The remaining observations are minor and do not block merge.

IMPLEMENTATION_APPROVED
