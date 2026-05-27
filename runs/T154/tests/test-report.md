I have all the information needed. Here is the test report.

---

## Test Report — T154: Stabilize Traefik Dynamic Route Lifecycle

### Test execution

```
43 tests passed — tests/test_proxy_manager.py, tests/test_traefik_manager.py,
                   tests/test_proxy_route_wait.py, tests/test_healthcheck_classification.py
 0 tests failed
```

Full suite regression check: **51 failures on branch, 51 failures on `main`** — no regressions introduced.

---

### Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Sandbox proxy URLs become reachable after route registration | **PASS** | `_wait_for_proxy_url()` polls post-registration; `test_wait_returns_true_when_backend_healthy` and `test_wait_returns_true_when_traefik_responds_http_error` verify it returns `True` on any HTTP response |
| Traefik no longer logs missing route file errors during normal lifecycle | **PASS** | Atomic write (tmp + rename, `proxy_manager.py:126-128`) ensures the file is only visible to Traefik when complete; no partial files exposed |
| Cleanup removes only the target sandbox route | **PASS** | `unregister()` targets `{sandbox_id}.yml` explicitly; `test_unregister_only_removes_target_sandbox` confirms the sibling route file survives |
| Stale route files can be pruned safely | **PASS** | `cleanup_stale_routes()` skips `_`-prefixed infra files; `test_cleanup_stale_routes_preserves_dashboard` and `test_cleanup_stale_routes_does_not_remove_global_traefik` confirm |
| Sandbox healthcheck distinguishes proxy infra failure from app failure | **PASS** | `healthcheck.sh:74` probes proxy-infra first and emits `PROXY_INFRA_FAIL` on connection failure; `test_healthcheck_emits_proxy_infra_fail` verifies this path end-to-end |
| Implementation remains generic and project-agnostic | **PASS** | `resolve_proxy_routes_dir()` uses env vars; no hardcoded project paths; Traefik conflict detection uses label inspection, not name matching |

---

### Ticket scope tests

| Test | Status |
|------|--------|
| Atomic route file creation | PASS — `test_register_creates_route_file` + code inspection |
| Idempotent unregister | PASS — `test_unregister_missing_file_is_safe` |
| Stale route cleanup | PASS — 4 tests covering empty dir, active-sandbox preservation, infra prefix guard |
| Tests do not pollute real route directory | PASS — all tests use `tmp_path` fixture; `test_proxy_routes_dir_uses_host_runtime_not_sandbox` enforces directory isolation at resolver level |
| Registered route becomes reachable before proxy healthcheck | PASS — `_wait_for_proxy_url()` called immediately after `_register_proxy_route()` at `run_sandbox.py:1007-1009` |
| Normal sandbox lifecycle does not create missing-file watcher errors | PASS — atomic write means Traefik never sees a partial file; no temporary file is exposed in the watched `/routes` directory |

---

### Anomalies

**Minor (non-blocking):**
- `test_healthcheck_classification.py` uses `@pytest.mark.integration` which is not registered in `pytest.ini`/`pyproject.toml`, producing a `PytestUnknownMarkWarning`. The test passes but the mark is non-functional (won't filter correctly with `-m integration`). This is cosmetic and does not affect test correctness.

**Pre-existing (not introduced by T154):**
- `tests/supervisor/test_supervisor.py::test_lifespan_restores_exec_cmd_and_restart_policy` fails on `main` and on this branch equally.

---

**Validation: PASS.** All acceptance criteria are met. One minor cosmetic anomaly (unregistered pytest mark) is worth noting but does not block merge.
