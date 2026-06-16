## T190 Test Report

**Result: PASS**

### T190-specific tests (81 tests across 5 files)

All 81 pass:

**`tests/test_supervisor_projects.py`** — 29 tests covering supervisor bootstrap endpoint:
- `test_bootstrap_creates_runtime_directories` ✓
- `test_bootstrap_creates_clones_directory` ✓ (new)
- `test_bootstrap_runtime_dirs_under_runtime_base_root` ✓ (new — asserts "projects" not in path)
- `test_bootstrap_uses_parent_of_factory_runtime_root_when_no_base` ✓ (new)
- `test_bootstrap_not_writable_runtime_base_returns_422` ✓ (new)
- All other validate-path and bootstrap tests ✓

**`tests/test_project_id.py`** — 24 tests covering `normalize_project_id`, `validate_project_id`, `assert_contained`:
- Updated `assert_contained` tests expect paths without `/projects/` segment ✓

**`tests/test_project_bootstrap.py`** — 13 tests covering control_api bootstrap service:
- Updated to use `runtime_base_root/{project_id}` (no `/projects/`) ✓
- `test_bootstrap_persists_project_runtime_root` ✓ (new)

**`tests/test_project_registry_persistence.py`** — 15 tests covering registry persistence:
- `test_register_persists_project_runtime_root` ✓ (new)
- `test_load_rehydrates_project_runtime_root` ✓ (new)
- `test_resolve_runtime_root_returns_none_when_absent` ✓ (new)
- `test_resolve_runtime_root_returns_none_for_unknown_project` ✓ (new)
- `test_roundtrip_preserves_project_runtime_root` ✓ (new)
- `test_ensure_registered_preserves_existing_project_runtime_root` ✓ (new — idempotency)

**`tests/test_project_registry.py`** — 18 tests ✓

### Regression check (all other test files touched by T190)

All pass:
- `tests/test_runtime_resolver.py` — 10 passed ✓
- `tests/test_projects_endpoint.py` — 9 passed ✓
- `tests/test_project_scoped_routes.py` — 9 passed ✓

### Pre-existing failures (unrelated to T190)

72 failures reproduce on `main` — none in any file modified by T190:

- `tests/test_sandbox_worktree.py` — 11 failures (pre-existing, confirmed on main)
- `tests/test_ticket_timeline.py` — 8 failures (404 on timeline routes, pre-existing)
- `tests/test_control_api_artifacts.py` — 13 failures (test isolation / filesystem state, pre-existing)
- `tests/test_control_api_endpoints.py` — 10 failures (test isolation, pre-existing)
- Others (`test_control_api_subprocess`, `test_daemon_checkpoint`, `test_daemon_issue_polling`,
  `test_environment_*`, `test_operational_scripts`, `test_run_daemon`) — all pre-existing

Zero regressions. No file modified by T190 has any failing test.

### Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Supervisor uses `RUNTIME_BASE_ROOT` env var | **PASS** — `_runtime_base_root()` resolution order implemented |
| No `/projects/` segment in bootstrap paths | **PASS** — `runtime_base / project_id` (no intermediate segment) |
| Unwritable `runtime_base_root` returns 422 | **PASS** — writability check before mkdir |
| Fallback: parent of `AI_DEV_FACTORY_RUNTIME_ROOT` | **PASS** — tested in `test_bootstrap_uses_parent_of_factory_runtime_root_when_no_base` |
| `project_runtime_root` persisted in registry | **PASS** — `workspace.json` includes field |
| Re-import preserves existing `project_runtime_root` | **PASS** — `ensure_registered` is idempotent |
| All project-scoped routes use persisted runtime root | **PASS** — `Depends(resolve_project_runtime_root)` on all 23 routes |
| No `/projects/` in fallback path resolution | **PASS** — `runtime_resolver.py` updated |
