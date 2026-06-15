The 20 failures in `test_sandbox_worktree.py` and `test_ticket_timeline.py` are confirmed pre-existing — identical failure count before and after our changes.

The implementation is complete. Here's the final state:

**All tests from our implementation pass (60 tests total):**
- `tests/test_project_bootstrap.py` — 13 passed
- `tests/test_project_id.py` — 17 passed
- `tests/test_auto_bootstrap.py` — 8 passed
- `tests/test_supervisor_projects.py` — 15 passed (1 test renamed and updated)

**Pre-existing failures (unrelated to T189):** 20 failures in sandbox worktree and ticket timeline tests — confirmed unchanged by stash comparison.

**Files modified:**
| File | Change |
|------|--------|
| `services/supervisor/main.py` | Added `_runtime_base_root()`, updated bootstrap endpoint to use it, added `clones_dir` |
| `services/control_api/services/project_id.py` | `assert_contained()` now checks `runtime_base_root/project_id` directly |
| `services/control_api/services/project_bootstrap.py` | `runtime_root` → `runtime_base_root` param, `clones_dir` in result |
| `services/control_api/main.py` | Reads `RUNTIME_BASE_ROOT`, stores as `app.state.runtime_base_root` |
| `services/control_api/routes/projects.py` | Uses `runtime_base_root` in import and list endpoints |
| `services/control_api/services/runtime_resolver.py` | `project_id` branch uses `RUNTIME_BASE_ROOT/project_id` |
| `services/control_api/models/schemas.py` | `BootstrapResult` gains `clones_dir` field |
| `deploy/.env.example` | Added `RUNTIME_BASE_ROOT=/Users/<you>/runtime` |
| `tests/test_project_bootstrap.py` | Updated path assertions + new sibling isolation test |
| `tests/test_project_id.py` | Updated `assert_contained` path assertions |
| `tests/test_auto_bootstrap.py` | Updated mock responses to new path model |
| `tests/test_supervisor_projects.py` | Updated test to verify new `RUNTIME_BASE_ROOT` behavior |
