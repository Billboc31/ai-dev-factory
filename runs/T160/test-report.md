# Test Report — T160

## Summary

**Status: PASS**

All acceptance criteria are satisfied. No regressions introduced.

---

## Acceptance Criteria

### AC1 — Custom environments no longer resolve to `/sandboxes/...`

**PASS**

Grep confirms zero occurrences of `Path("/sandboxes")` or `"/sandboxes/"` in `services/`:

```
$ grep -r 'Path("/sandboxes")\|"/sandboxes/"' services/
(no output)
```

### AC2 — Runtime actions use the configured runtime root

**PASS**

`sandbox_manager.py` path helpers derive from `self.sandboxes_dir`, which is sourced from `runtime_resolver.get_project_sandbox_dir()`:

```python
# sandbox_manager.py:119-123
def _env_file_path(self, sandbox_id: str) -> Path:
    return self._sandbox_dir(sandbox_id) / ".env"

def _runtime_root_path(self, sandbox_id: str) -> Path:
    return self._sandbox_dir(sandbox_id) / "runtime"
```

All runtime operations (stop, logs, destroy, supervisor) use these helpers instead of stored state values.

### AC3 — Redeploy/Stop/Refresh/Delete/View Logs work correctly

**PASS**

All six environment routes catch `SandboxNotFoundError` and return HTTP 404 with a readable message. Verified in `environments.py:127-180`.

### AC4 — Environment metadata stores sandbox ids instead of absolute paths

**PASS**

`SandboxState` model fields marked informational with empty defaults:

```python
# models/sandbox.py:44
env_file: str = ""  # informational; runtime paths are reconstructed dynamically
sandbox_runtime_root: str = ""
```

Runtime code ignores these stored values and reconstructs paths dynamically from the configured root.

### AC5 — Missing sandbox errors are user-readable

**PASS**

`_read_state()` raises `SandboxNotFoundError("sandbox not found: {sandbox_id}")` on `FileNotFoundError`. Routes convert this to HTTP 404 with `"environment not found: {env_id}"`. No raw `FileNotFoundError` stack traces reach the API.

### AC6 — No hardcoded `/sandboxes` paths remain

**PASS**

Confirmed by grep above. The fragile string heuristic in `infra_service_manager.py` was also replaced:

```python
# OLD: if "sandboxes" not in p.parts:
# NEW: if not p.is_relative_to(get_sandbox_root()):
```

### AC7 — Environment actions work from arbitrary runtime roots

**PASS**

`test_custom_sandbox_root_resolves_correctly` exercises create/stop/delete with a custom `SANDBOX_ROOT` value and verifies all operations succeed without any hardcoded path assumption.

---

## Tests Executed

### T160-specific tests (all new or modified)

```
tests/test_environment_routes.py::test_custom_sandbox_root_resolves_correctly     PASS
tests/test_environment_routes.py::test_missing_sandbox_returns_readable_404       PASS
tests/test_environment_routes.py::test_no_hardcoded_sandboxes_path_in_sandbox_manager  PASS
tests/test_sandbox_manager.py::test_path_helpers_use_sandboxes_dir                PASS
tests/test_sandbox_manager.py::test_stop_uses_helper_path_ignoring_stale_env_file PASS
tests/test_sandbox_manager.py::test_logs_uses_helper_path_ignoring_stale_env_file PASS
```

### Full T160 test scope

```
tests/test_environment_routes.py  15/15 passed
tests/test_sandbox_manager.py     29/29 passed
Total: 44/44 passed in 1.13s
```

### Regression check (full suite)

```
1126 passed, 47 failed
```

The 47 failures are pre-existing: confirmed by running the same test files on the branch before T160 changes were applied. No new failures introduced.

---

## Blocking Issues

None.

---

## Result

**VALIDATION PASSED** — implementation satisfies all acceptance criteria.
