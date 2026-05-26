# Test Report — T150 Local DNS and Reverse Proxy for Sandbox Environments

**Date:** 2026-05-26  
**Branch:** ticket/T150-t150-local-dns-and-reverse-proxy-for-sandbox-envir  
**Verdict:** PASS

---

## Acceptance Criteria

### AC1 — Stable local hostnames instead of raw ports
**Status: PASS**

`ProxyManager.register()` generates:
- `http://sandbox-{id}.ai-dev-factory.localhost` (web)
- `http://api.sandbox-{id}.ai-dev-factory.localhost` (API)

URLs stored in `SandboxState.urls` and returned by the API. Confirmed by model serialization test and manual integration check.

### AC2 — Multiple concurrent sandbox environments coexist
**Status: PASS**

- Each sandbox gets a separate route file: `{runtime_root}/proxy/routes/{id}.yml`
- Hostnames are unique across sandboxes: no collision possible since they embed the sandbox ID
- Verified: `test_hostnames_unique_across_sandboxes`, `test_concurrent_sandboxes_have_separate_files`, manual multi-sandbox check

### AC3 — Routes automatically registered and cleaned up
**Status: PASS**

- `SandboxManager.start()` calls `self._proxy.register(sandbox_id, state.ports)` after compose up succeeds
- `SandboxManager.destroy()` calls `self._proxy.unregister(sandbox_id)` before undeploy
- `unregister` is safe when file is already missing (no exception)
- Verified: `test_unregister_removes_route_file`, `test_unregister_missing_file_is_safe`, code inspection of `sandbox_manager.py:184` and `sandbox_manager.py:349`

### AC4 — Dashboard displays sandbox URLs
**Status: PASS**

- `SandboxPanel.jsx:119-121`: renders `UrlsTable` with clickable `<a>` links when `sandbox.urls` is non-empty, falls back to `PortsTable` otherwise
- `SandboxRunsTable.jsx:86-98`: renders URL links in the "Access" column when `run.urls` is present, falls back to raw ports

### AC5 — Routing generic and project-agnostic
**Status: PASS**

`ProxyManager` contains no project-specific logic. Hostnames are derived solely from `sandbox_id` and the fixed suffix `ai-dev-factory.localhost`.

---

## Ticket Test Scenarios

| Scenario | Status | Evidence |
|---|---|---|
| Multiple concurrent sandbox hostnames | PASS | `test_hostnames_unique_across_sandboxes`, `test_concurrent_sandboxes_have_separate_files` |
| Route registration and cleanup | PASS | `test_register_creates_route_file`, `test_unregister_removes_route_file` |
| API and web routing separation | PASS | YAML validated: separate router+service entries per endpoint |
| Sandbox deletion removes routes | PASS | `test_unregister_removes_route_file`; `destroy()` calls `unregister` |
| Persistent environments reachable after worker exit | PASS by design | Routes are filesystem-level; Traefik watches directory; worker exit does not delete route files |
| Hostname collisions handled safely | PASS | Idempotent register (`test_register_is_idempotent`); IDs are hex-unique |

---

## Unit Test Results

```
tests/test_proxy_manager.py — 12/12 PASSED (0.02s)
tests/test_sandbox_manager.py — 24/24 PASSED
tests/test_sandbox_routes.py — 13/13 PASSED
tests/test_sandbox_isolation.py — 12/12 PASSED
tests/test_sandbox_worktree.py — 13/13 PASSED
All sandbox-related tests: 148/148 PASSED
```

---

## Regression Check

Full test suite: **961 passed, 47 failed** — identical failure count to main branch. The 47 pre-existing failures (`test_control_api_endpoints`, `test_ticket_timeline`, `test_daemon_checkpoint`, etc.) are unrelated to T150 changes and exist on main.

T150 changed files:
- `services/control_api/models/sandbox.py`
- `services/control_api/services/proxy_manager.py` (new)
- `services/control_api/services/sandbox_manager.py`
- `apps/dashboard/src/components/SandboxPanel.jsx`
- `apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`
- `deploy/traefik/traefik.yml` (new)
- `docker-compose.yml`
- `tests/test_proxy_manager.py` (new)

No regressions introduced.

---

## Generated YAML Validation

Parsed `{id}.yml` output with PyYAML and confirmed:
- `http.routers.sandbox-{id}-web.rule = Host('sandbox-{id}.ai-dev-factory.localhost')`
- `http.routers.sandbox-{id}-api.rule = Host('api.sandbox-{id}.ai-dev-factory.localhost')`
- `http.services.sandbox-{id}-web.loadBalancer.servers[0].url = http://host.docker.internal:{web_port}`
- `http.services.sandbox-{id}-api.loadBalancer.servers[0].url = http://host.docker.internal:{api_port}`
- Atomic write via `.yml.tmp` → `.rename()` prevents partial reads by Traefik

---

## Observations (Non-Blocking)

1. **HTTPS deferred** — The plan explicitly defers TLS. Browsers treat `.localhost` as a secure context over HTTP (Chrome, Firefox). Acceptable for local dev scope.

2. **Port 80 requires permissions on macOS** — Traefik binds to port 80 in docker-compose. This requires Docker port binding permissions; Docker Desktop handles this automatically on macOS. Operational note, not a code issue.

3. **SandboxManager tests don't mock ProxyManager** — `SandboxManager(sandboxes_dir=...)` in tests instantiates a real `ProxyManager()` pointing to `~/runtime/ai-dev-factory/proxy/routes/`. This creates real route files as a test side-effect. Tests pass regardless; minor test isolation concern for a follow-up.

---

## Conclusion

All five acceptance criteria are met. All 12 `test_proxy_manager.py` tests pass. No regressions detected. The implementation is ready for the memory update step.
