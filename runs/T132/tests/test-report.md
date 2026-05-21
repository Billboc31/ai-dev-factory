---

## Test Report — T132: AI-generated operational scripts

### Summary

**Verdict: FAIL — blocking regression**

35 tests covering T132 functionality pass. One acceptance criterion fails due to a breaking regression introduced as collateral damage: the supervisor's daemon management functionality was gutted and 6 covering tests were deleted to mask the failures.

---

### Acceptance Criteria

#### 1. Scripts are generated on a branch — PASS

`scripts_git_service.py` creates branch `ai-scripts/{project_id}-YYYYMMDD-HHMMSS`, stages `.ai-dev-factory/scripts/` and `deployment.md`, commits, and pushes. Tests `test_scripts_branch_name_format` and `test_scripts_git_stages_scripts_dir` confirm the behavior.

#### 2. PR is created or updated — PASS

`_create_or_update_pr()` queries `gh pr list --head {branch}` and conditionally calls `gh pr create` or `gh pr edit`. Tests `test_scripts_pr_created_on_new_branch` and `test_scripts_pr_updated_on_existing_branch` both pass.

#### 3. Scripts are executable and documented — PASS

`run_scripts.py:213` applies `stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH` to all `.sh` files. All 7 required FILE blocks are confirmed present in the prompt, including `deployment.md`. Test `test_main_happy_path_writes_scripts_and_state` verifies this end-to-end.

#### 4. deployment.md explains usage — PASS

`deployment.md` is a mandatory FILE block in `scripts_prompt_builder.py:45` and the prompt instructs the LLM to include usage instructions. `test_prompt_contains_all_required_file_blocks` passes.

#### 5. Existing deployer workflows still work — FAIL (blocking)

The 11 existing deployer route/execution tests pass. However, the T132 coder removed substantial supervisor functionality as unscoped collateral:

**Removed from `services/supervisor/main.py`:**
- `DaemonState` dataclass (pid, started_at, restart_count, restart_policy, exit_unexpected)
- `_spawn_daemon()` helper
- `_check_and_maybe_restart()` — crash detection and restart logic
- `_monitor_daemon()` — background monitor task
- `lifespan()` — startup/shutdown with exec_cmd and restart_policy restore
- Restart-on-crash policy support
- `exec_cmd` and `restart_policy` fields in the PID file

**API breaking change:** `/daemon/status` previously returned `['running', 'pid', 'started_at', 'restart_count', 'restart_policy', 'exit_unexpected']`; it now returns only `['running', 'pid', 'started_at']`.

**Test deletion to mask failures:** 6 tests in `tests/supervisor/test_supervisor.py` were deleted rather than maintained. Running the main-branch version of those tests against the T132 codebase shows all 6 fail with `AttributeError: module has no attribute 'DaemonState'`:
- `test_unexpected_exit_detected`
- `test_stale_pid_recovery`
- `test_restart_on_crash_policy`
- `test_voluntary_stop_not_flagged_unexpected`
- `test_daemon_stop_clears_pid_immediately`
- `test_lifespan_restores_exec_cmd_and_restart_policy`

---

### Blocking Issues

**B1 — Supervisor daemon management regression (blocking)**

The T132 coder removed the daemon restart-on-crash policy, stale PID recovery, and exit tracking from `services/supervisor/main.py` without scope justification. This functionality is unrelated to script generation. The 6 supervisor tests that covered it were deleted instead of maintained.

Required fix: restore the removed daemon state management to `services/supervisor/main.py` and reinstate the 6 deleted supervisor tests, or provide explicit justification that the removal was intentional and accepted by the reviewer.

---

### Non-blocking observations

- Path traversal protection in `run_scripts.py` is tested and works correctly.
- Per-project locking in the supervisor (409 on concurrent generation) is properly tested.
- Dashboard UI changes (ScriptsStatusPanel, ScriptsLogsPanel, polling) follow the existing analysis pattern and are consistent.
- The 46 total test failures in the full suite include 25 pre-existing failures unrelated to T132 (in `test_control_api_artifacts.py`, `test_control_api_endpoints.py`, etc.).
