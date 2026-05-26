Implementation complete. Here's a summary of all changes made:

---

## T149 — Implementation Summary

### Files modified

**Backend — State model**
- `services/control_api/models/schemas.py`: Expanded `SandboxValidationState` and `SandboxValidationStatus` state literals to include `validating`, `validated`, `environment`, `stopped`, `cleaned`; added `mode: Literal["validation","environment"]` field to both.

**Backend — Worker**
- `tools/agent_runner/run_sandbox.py`: Added `--mode validation|environment` CLI arg; initial state now writes `validating` instead of `running`; after healthcheck success, validation mode writes `validated` and runs teardown, environment mode writes `environment` and skips teardown (compose + supervisor + port slot stay up); failure in either mode releases the port slot.

**Backend — Supervisor**
- `services/supervisor/main.py`: Added `_sandbox_release_stale_lock()` called before `lock.acquire()` to clear dead PID files and reset stuck locks; `SandboxStartRequest` now accepts `mode`; worker is spawned with `--mode`; added background thread to remove PID file when worker exits; `sandbox_status_endpoint` now handles `validating` (not just `running`) for phantom detection; replaced simple `sandbox_stop` with full `_do_sandbox_stop()` that kills the worker, runs `stop.sh`, releases port slot, and sets state=`stopped`; added `DELETE /sandbox/{project_id}` endpoint that stops then removes worktree + sandbox dir and sets state=`cleaned`.

**Backend — API layer**
- `services/control_api/services/sandbox_runner.py`: `start_sandbox_validation` now accepts and passes `mode`; added `stop_sandbox_environment()` and `delete_sandbox_environment()` client functions; `_state_from_payload` parses `mode` field.
- `services/control_api/routes/sandbox.py`: `start_project_sandbox` accepts `mode` query param; added `POST /{project_id}/sandbox/stop` and `DELETE /{project_id}/sandbox` routes; `get_project_sandbox_status` and `_raw_to_status` pass through `mode`.

**Frontend**
- `apps/dashboard/src/api/deployer.js`: Added `startSandboxEnvironment`, `stopSandboxEnvironment`, `deleteSandboxEnvironment` exports.
- `apps/dashboard/src/pages/DeployerPage.jsx`: Split single button into "Deploy & Test" + "Start Environment"; added Stop/Delete Environment buttons for `environment`/`stopped` states; expanded `STATE_COLORS`; fixed `isSandboxActive` to include `validating`.
- `apps/dashboard/src/components/SandboxRunsPanel.jsx`: Added Mode column; expanded state colors; replaced single Cleanup button with Stop (for `environment`), Delete (for `environment`/`stopped`), Cleanup (for completed runs).

**Tests**
- `tests/test_supervisor_sandbox.py`: Updated stop tests for new idempotent behavior; added `test_stop_is_idempotent_when_already_stopped`, `test_stale_pid_cleared_before_new_start`, `test_delete_transitions_state_to_cleaned`.
- `tests/test_run_sandbox_worker.py`: Updated `test_worker_full_success` and `test_scripts_executed_with_worktree_as_cwd` for `validated` state; added 6 new mode tests covering validation/environment success/failure/port behavior.
- `tests/test_sandbox_runner.py`: Updated expected start payload to include `mode`.
