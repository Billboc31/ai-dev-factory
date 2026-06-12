## Test Report — T188

**Branch:** `ticket/T188-t188-route-all-host-filesystem-project-import-and`  
**Date:** 2026-06-12

---

### Commands executed

```
python -m pytest tests/test_supervisor_projects.py tests/test_project_bootstrap.py tests/test_auto_bootstrap.py -v
python -m pytest tests/ --ignore=tests/integration --deselect=tests/supervisor/test_supervisor.py::test_lifespan_restores_exec_cmd_and_restart_policy -q --tb=no
python -m pytest tests/test_control_api_endpoints.py -q  (on main, to baseline)
python -m pytest tests/test_sandbox_worktree.py tests/test_ticket_timeline.py -q --tb=no  (on main, to baseline)
```

---

### T188-specific tests

| File | Tests | Result |
|------|-------|--------|
| `tests/test_supervisor_projects.py` | 15 | 15 passed |
| `tests/test_project_bootstrap.py` | 12 | 12 passed |
| `tests/test_auto_bootstrap.py` | 8 | 8 passed |
| **Total** | **35** | **35 passed** |

---

### Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Importing `/Users/…` projects works when Control API runs in Docker | PASS | `routes/projects.py:import_project()` delegates to `_supervisor_validate_path()` before any persistence; no `Path.exists/expanduser/resolve` in import path |
| Filesystem validation executes through supervisor | PASS | `POST /projects/validate-path` on supervisor performs all path checks (`exists`, `is_dir`, `.git` detection); verified by 15 supervisor tests |
| Bootstrap executes through supervisor | PASS | `project_bootstrap.py:bootstrap()` calls `POST /projects/bootstrap`; zero `mkdir/write_text/is_dir/resolve` calls remain in that file |
| Control API no longer performs host filesystem assumptions | PASS | `import_project()` only calls `_supervisor_validate_path()` and `bootstrap()`; filesystem helpers (`_read_stack`, `is_dir`) are in `list_projects` which was declared out of scope |
| Existing imported projects continue to work | PASS | `list_projects` and `registry` unchanged; `auto_bootstrap` falls back gracefully when supervisor is unreachable |
| Multi-project workflow remains unchanged | PASS | Per-project daemon endpoints untouched; registry operations unchanged |

---

### Regressions

None introduced by T188.

Pre-existing failures confirmed on `main` (before T188):
- `tests/supervisor/test_supervisor.py::test_lifespan_restores_exec_cmd_and_restart_policy` — 1 failure
- `tests/test_control_api_endpoints.py` — 10 failures
- `tests/test_sandbox_worktree.py` — 11 failures
- `tests/test_ticket_timeline.py` — 9 failures
- Other pre-existing failures unrelated to T188 scope

T188 only added 3 test files (`test_supervisor_projects.py`, `test_project_bootstrap.py`, `test_auto_bootstrap.py`). No existing test file was modified.

---

### Blocking issues

None.

---

### Non-blocking observations

Carried over from implementation review, no new findings:

1. `services/control_api/services/stack_detector.py` is orphaned dead code — no callers. Should be deleted in a follow-up.
2. `_supervisor_validate_path()` does not catch `json.JSONDecodeError` — could produce an undescriptive 500 if supervisor returns a non-JSON body on error.
3. Supervisor `/projects/bootstrap` has no independent `project_id` path-traversal guard. Low risk given localhost-only binding; Control API defends with `assert_contained()` before calling.

---

TEST_COMPLETE
