# T164 — Test Report

**Date**: 2026-05-29  
**Branch**: `ticket/T164-t164-replace-docker-compose-v2-5-style-environment`  
**Tester**: Claude (Sonnet 4.6)

---

## Summary

**PASS** — All acceptance criteria satisfied. One regression found and fixed (stale test assertion).

52 tests pass across unit, integration, and regression suites covering all acceptance criteria.

---

## Acceptance Criteria

### 1. Dynamic environments work reliably through Traefik
**PASS**

- Route files reference DNS aliases (`sandbox-{id}-api:8080`, `sandbox-{id}-web:80`) declared in `docker-compose.yml`
- Traefik permanently connected to `ai-dev-factory-runtime` network via `docker-compose.traefik.yml`
- No dynamic network mutation required post-deploy

Evidence: `test_register_route_file_contains_alias_urls`, `test_route_files_reference_correct_aliases`

---

### 2. No manual network attach/debugging required
**PASS**

- Old `attach_traefik_to_compose_project()` / `detach_traefik_from_compose_project()` deleted
- `proxy_network.py` rewritten to 26 lines — zero subprocess calls
- Grep of `services/` and `tools/` for `docker network connect` / `docker network disconnect` returns empty

Evidence: code review of `proxy_network.py:1-27`

---

### 3. Traefik consistently resolves environment services
**PASS**

- Backend URLs are pure DNS aliases: `http://sandbox-{id}-api:8080`
- No `host.docker.internal` fallback in routes
- `ensure_runtime_network()` idempotently pre-creates the shared network before Traefik starts

Evidence: `test_sandbox_backend_urls_no_host_docker_internal`, `test_no_host_docker_internal_in_routes`

---

### 4. Networking architecture supports multiple concurrent environments
**PASS**

- Unique per-sandbox aliases via `SANDBOX_ID` variable in compose
- No hardcoded network names or project assumptions
- Concurrent sandboxes get separate, non-colliding route files and backend URLs

Evidence: `test_two_sandboxes_have_unique_backend_aliases`, `test_two_sandboxes_each_get_route_file`, `test_route_files_reference_correct_aliases` (no cross-contamination assertion)

---

### 5. Runtime networking ownership is clearly defined
**PASS**

- **Shared network**: created by `ensure_runtime_network()` in `infra_service_manager.py`, declared by `docker-compose.traefik.yml`
- **Service aliases**: declared per-sandbox in `docker-compose.yml`
- **Routes**: owned by `ProxyManager`
- **Infra routes** (`_dashboard.yml`): protected by `_` prefix convention
- **Cleanup**: `ProxyManager.cleanup_stale_routes()` skips infra files

Evidence: `test_cleanup_stale_routes_preserves_dashboard`, `test_destroy_does_not_remove_infra_dashboard`

---

### 6. Compose-generated default-network fragility is eliminated
**PASS**

- `ai-dev-factory-runtime` is an explicit named network in every compose file
- Services declare `external: true` for the shared network
- No reliance on compose-generated `{project}_default` networks for Traefik routing

Evidence: `docker-compose.yml:81-83`, `proxy_network.py` (no compose-default references)

---

### 7. Existing deployer/runtime flows continue functioning
**PASS**

- `ProxyManager.register()` retains `ports` parameter (optional, backward-compatible)
- `sandbox_manager.py` `start()` / `destroy()` flows updated cleanly
- `sandbox_runtime_deploy.py` and `run_sandbox.py` call sites updated

Evidence: `tests/test_sandbox_runtime_deploy.py` — all 5 tests pass

---

## Regression Found and Fixed

**File**: `tests/test_sandbox_runtime_deploy.py:143-147`  
**Test**: `test_deploy_operational_runtime_script_failure_cleans_up`

The test asserted `unregister()` was called with `compose_project=state.compose_project`, which was removed by T164. The implementation is correct; the test was stale. Fixed by removing the obsolete `compose_project` kwarg from the assertion.

**Before**:
```python
mock_unreg.assert_called_once_with(
    state.id,
    compose_project=state.compose_project,
    remove_route_file=False,
)
```

**After**:
```python
mock_unreg.assert_called_once_with(
    state.id,
    remove_route_file=False,
)
```

---

## Test Execution Results

```
52 passed in 5.74s
```

| Suite | Tests | Result |
|-------|-------|--------|
| `tests/test_proxy_network.py` | 6 | PASS |
| `tests/test_proxy_manager.py` | 29 | PASS |
| `tests/test_sandbox_runtime_deploy.py` | 5 | PASS |
| `tests/integration/test_multi_env_networking.py` | 5 | PASS |
| `tests/integration/test_redeploy_stability.py` | 4 | PASS |
| `tests/integration/test_env_cleanup.py` | 4 | PASS (incl. `test_proxy_route_files.py` via suite) |

### Other suite failures (50 tests)
Verified pre-existing on `main` branch, unrelated to T164 (environment state pollution in `test_list_tickets_empty`, mock mismatch in unrelated daemon tests). None introduced by this branch.

---

## Verdict

**TEST_COMPLETE**

All 7 acceptance criteria pass. One regression (stale test assertion) was found and fixed. The implementation correctly replaces fragile per-compose isolated networking with a shared declarative ingress network model.
