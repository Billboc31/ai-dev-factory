All 25 tests pass. Here's a summary of what was implemented:

## Files created

- **`services/supervisor/auto_fix_loop.py`** — The full loop orchestrator: `apply_patches`, `run_scripts_validation`, `run_auto_fix_loop`, session persistence (`make_session`, `persist_session`, `load_session`, `list_sessions`)
- **`tests/test_auto_fix_loop.py`** — 9 new tests covering all required cases

## Files modified

- **`services/supervisor/auto_fix_proposer.py`** — Fixed `_is_allowed_path`: removed the `normalized == _ALLOWED_PREFIX` branch
- **`services/control_api/models/auto_fix.py`** — Added `AutoFixIteration`, `AutoFixSession`, `SessionStatus`, `IterationStatus`
- **`services/supervisor/main.py`** — Removed `exec_cmd` default, added `AutoFixLoopStartRequest` model + `_run_loop_bg` + 3 loop endpoints (`POST /auto-fix/{id}/loop/start`, `GET /auto-fix/{id}/loop/{session_id}`, `GET /auto-fix/{id}/loops`)
- **`services/control_api/services/auto_fix_runner.py`** — Added `start_auto_fix_loop`, `get_auto_fix_session`, `list_auto_fix_sessions`
- **`services/control_api/routes/auto_fix.py`** — Removed `exec_cmd` default, added 3 loop routes, extracted `_raise_on_supervisor_error` helper
- **`apps/dashboard/src/api/autoFix.js`** — Added `startAutoFixLoop`, `getAutoFixSession`, `listAutoFixSessions`; removed dangerous default
- **`apps/dashboard/src/components/AutoFixPanel.jsx`** — Added loop start form, session list table, session detail panel with per-iteration history
- **`tests/test_auto_fix_routes.py`** — Updated to pass `exec_cmd` explicitly

## Acceptance criteria now met

| Criterion | Status |
|---|---|
| sandbox reruns after fixes | ✅ `run_scripts_validation` in-place |
| retries bounded and observable | ✅ `max_retries`, `current_iteration` persisted |
| iteration history persisted and visible | ✅ session + iterations in `auto-fix-sessions/` |
| system never enters infinite retry loops | ✅ loop exits after `max_retries` |
| successful fixes → sandbox success state | ✅ `session.status = "success"` |
| failed retries → clean terminal state | ✅ `session.status = "failed"` |
