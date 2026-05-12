61/61 passing, zero regressions. Here's a summary of what was implemented:

---

## Changes

**`tools/agent_runner/run_step.py`**
- Added 3 pattern constant tuples (`_QUOTA_PATTERNS`, `_WRITE_PERMISSION_PATTERNS`, `_PROVIDER_ERROR_PATTERNS`) covering the main failure signals
- Added `classify_runtime_failure(return_code, stdout, stderr) -> str` with 7 categories ordered by priority: `process_crashed`, `quota_exceeded`, `write_permission_missing`, `provider_error`, `empty_output`, `process_failed`, `unknown`
- Called it in the `exec_cmd` branch after `execute_external_command`: logs `"runtime failure: X"` on non-zero exit, logs `"runtime warning: X"` (non-blocking) when `write_permission_missing` or `empty_output` is detected with rc=0

**`tools/agent_runner/run_ticket.py`**
- Added `classify_runtime_failure` to the importlib import block alongside `validate_planner_output`
- In `_call_run_step`: logs classification when `result.returncode != 0` (uses output file content + stderr from run_step)
- In `auto_run`: logs `"auto-run: runtime failure: X"` in the `rc != 0` branch (uses `output_content` from the returned tuple, so it works even when `_call_run_step` is mocked in tests)

**`tests/test_runtime_failure_detection.py`** — 18 new tests covering every category, priority ordering, state-unchanged invariant, and runtime log content.
