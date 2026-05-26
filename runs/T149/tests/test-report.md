Now I have all the information needed. Let me produce the test report.

---

## Test Report — T149: Sandbox Lifecycle Modes and Stale Running Cleanup

### Test Execution

**60/60 tests passed** across three test files:

| File | Tests | Result |
|---|---|---|
| `tests/test_supervisor_sandbox.py` | 14 | PASS |
| `tests/test_run_sandbox_worker.py` | 36 | PASS |
| `tests/test_sandbox_runner.py` | 10 | PASS |

---

### Acceptance Criteria

**AC1 — After a completed validation, starting another validation never incorrectly returns `already running`**
**PASS**

- `_watch_worker` thread removes the PID file when the worker process exits naturally.
- `_sandbox_release_stale_lock` is called before every `sandbox_start`; if PID file exists but process is dead, it removes the file and resets the in-memory lock entry.
- `_sandbox_current_pid` always does a live `_is_alive(pid)` check before returning a PID, and removes the file on dead processes.
- Covered by: `test_stale_pid_cleared_before_new_start` PASSED.

**AC2 — After deleting a sandbox, starting a new one never incorrectly returns `already running`**
**PASS**

- `sandbox_delete` explicitly calls `_sandbox_pid_path(project_id).unlink()` after completing the stop/cleanup sequence and writes state `cleaned`.
- Next `sandbox_start` finds no PID file; proceeds without 409.
- Covered by: `test_delete_transitions_state_to_cleaned` PASSED.

**AC3 — User can choose between ephemeral validation and persistent environment**
**PASS**

- Dashboard exposes two separate buttons: "Deploy & Test" (mode=`validation`) and "Start Environment" (mode=`environment`).
- API route (`POST /projects/{project_id}/sandbox/start`) validates `mode` param with regex `^(validation|environment)$`.
- Supervisor forwards `--mode` arg to worker.
- Worker: validation → deploy, healthcheck, stop, teardown; environment → deploy, healthcheck, stay running.
- Covered by: `test_validation_mode_writes_validated_state`, `test_environment_mode_writes_environment_state` PASSED.

**AC4 — Persistent environments stay alive until explicitly stopped/deleted**
**PASS**

- Environment mode sets `keep_environment = True` → `finally` block skips stop.sh and port release on success.
- Worker exits cleanly; compose services and port slot remain allocated.
- State file shows `"environment"`.
- Covered by: `test_environment_mode_keeps_port_slot_allocated`, `test_environment_mode_writes_environment_state` PASSED.

**AC5 — Dashboard clearly shows lifecycle mode and state**
**PASS**

- `SandboxRunsPanel.jsx`: Mode column in the table; all 10 states have color mappings (idle, pending, running, validating, validated, environment, success, failed, stopped, cleaned).
- `DeployerPage.jsx`: Mode badge displayed when mode ≠ 'validation'; active spinner shown for `validating` state; Stop/Delete buttons appear conditionally on environment/stopped state.

**AC6 — Cleanup remains safe and idempotent**
**PASS**

- `_do_sandbox_stop` is a no-op if state is already `stopped` or `cleaned`.
- Worktree removal tries `git worktree remove --force` first, falls back to `shutil.rmtree`.
- Port slot release uses fcntl file locking and silently handles missing files.
- `cleanup_sandbox_run` API validates sandbox_id with regex before any filesystem operations.
- Covered by: `test_stop_is_idempotent_when_already_stopped`, `test_stop_when_no_worker_is_idempotent` PASSED.

---

### Ticket Test Scenarios

| Scenario | Status |
|---|---|
| Validation mode releases running locks after completion | PASS (`test_stale_pid_cleared_before_new_start`, `test_validation_mode_releases_port_slot_on_success`) |
| Cleanup clears stale running state | PASS (`test_stale_pid_cleared_before_new_start`, `test_delete_transitions_state_to_cleaned`) |
| Deploy & Test again after cleanup starts a new validation | PASS (stale lock release mechanism proven) |
| Start Environment keeps sandbox running after healthcheck | PASS (`test_environment_mode_writes_environment_state`, `test_environment_mode_keeps_port_slot_allocated`) |
| Stop Environment stops services, preserves logs/state | PASS (`test_stop_kills_worker_pid`; stop writes `stopped` state, runs stop.sh, does not delete files) |
| Delete Environment removes runtime/worktree safely | PASS (`test_delete_transitions_state_to_cleaned`) |
| Validation and environment modes do not conflict | PASS (per-project lock prevents concurrent starts; modes are independent) |

---

### Regressions

None detected. All 60 tests pass including 43 pre-existing tests that cover prior functionality.

---

### Minor Observations (non-blocking)

1. **Delete button not shown for `cleaned` state in `DeployerPage`** (`line 514`): The Delete button only appears for `environment` or `stopped` states. A sandbox stuck in a partial `cleaned` state (e.g. state file written but files partially removed) can only be managed from the SandboxRunsPanel Cleanup button. This is acceptable behavior — `cleaned` means deletion succeeded.

2. **Phantom-process recovery in `sandbox_status_endpoint`** correctly excludes `environment` state from promotion to `failed` (line 1047), since environment mode workers are expected to have exited.

---

### Verdict

**VALIDATION PASSED** — All acceptance criteria are met. The implementation correctly fixes stale running state after cleanup, introduces two distinct lifecycle modes (validation and environment), exposes explicit Stop/Delete actions in the dashboard, and maintains idempotent cleanup throughout.
