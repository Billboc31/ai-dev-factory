Now I have enough context to write the plan. Let me produce it.

---

## Objective

Introduce explicit lifecycle modes (validation vs. environment) for the deploy-validation sandbox pipeline, and fix stale `already running` locks that survive after cleanup or completion. Both modes share the same isolated-port / compose-project / worktree infrastructure; they differ only in what happens after the healthcheck succeeds.

## Included

### State model — `services/control_api/models/schemas.py`

- Expand `SandboxValidationState.state` from `Literal["idle","pending","running","success","failed"]` to `Literal["idle","pending","validating","validated","environment","failed","stopped","cleaned"]`.
- Add `mode: Literal["validation","environment"] = "validation"` to `SandboxValidationState` and to the start-request body.

### Stale running-lock fix — `services/supervisor/main.py`

- In `sandbox_start`: before attempting `lock.acquire(blocking=False)`, read the existing PID file; if it exists and `_pid_alive()` returns `False`, remove the PID file and release the lock (reset the per-project `_sandbox_locks` entry) so a new run can start.
- After the worker subprocess exits (inside the background thread), always remove `$RUNTIME_ROOT/runs/sandbox-{project_id}.pid`.
- In `cleanup_sandbox_run` route handler: before deleting the sandbox directory, send `SIGTERM` to the worker PID if alive, then remove the PID file and force-release the lock.

### Mode branching — `tools/agent_runner/run_sandbox.py`

- Accept a `--mode validation|environment` CLI argument (default: `validation`).
- Set state to `validating` at the start of script execution (was `running`).
- After `healthcheck.sh` succeeds:
  - **validation mode**: run `stop.sh`, undeploy (call `run_undeploy()`), cleanup (call `run_cleanup()`), release port slot, write final state `validated`. Existing `finally` block already handles port release; verify it runs even on success path.
  - **environment mode**: write state `environment`, exit worker (compose services stay up, isolated port slot remains allocated). No undeploy or cleanup at this point.
- On failure: both modes write state `failed` and release the port slot (already true for validation; extend to environment).

### Stop and delete for environment sandboxes — `services/supervisor/main.py`

- Add `POST /sandbox/{project_id}/stop`: runs `stop.sh` if present, then `run_undeploy()`, sets state to `stopped`, releases port slot. Idempotent (no-op if already stopped).
- Add `DELETE /sandbox/{project_id}` (environment delete): runs stop (if not already stopped), then `run_cleanup()`, removes worktree, removes sandbox directory, sets state to `cleaned`.

### API surface — `services/control_api/routes/sandbox.py` + `services/control_api/services/sandbox_runner.py`

- `POST /projects/{project_id}/sandbox/start`: accept `mode` query param or body field; forward it to supervisor.
- `POST /projects/{project_id}/sandbox/stop`: new endpoint, proxy to supervisor stop.
- `DELETE /projects/{project_id}/sandbox`: new endpoint, proxy to supervisor delete.
- Update `sandbox_runner.py` to pass `mode` in the start payload.

### Dashboard — `apps/dashboard/src/components/SandboxRunsPanel.jsx` + `apps/dashboard/src/api/sandbox.js`

- Replace the single "Start" / "Deploy & Test" button with two explicit actions: **Deploy & Test** (mode=validation) and **Start Environment** (mode=environment).
- For sandboxes in `environment` or `stopped` state, show **Stop Environment** and **Delete Environment** action buttons.
- Display a mode badge (`validation` / `environment`) and the full state value next to each sandbox entry.
- Add `stopSandboxEnvironment(projectId)` and `deleteSandboxEnvironment(projectId)` to `sandbox.js`.

### Tests

- `tests/test_run_sandbox_worker.py`:
  - Validation mode: assert port slot released, state=`validated`, compose is down after completion.
  - Environment mode: assert port slot still allocated, state=`environment`, compose is up after worker exits.
  - Failed run in environment mode: assert port slot released, state=`failed`.
- `tests/test_supervisor_sandbox.py`:
  - Stale PID (process dead): second `POST /sandbox/start` succeeds instead of returning 409.
  - Cleanup while running: worker is terminated, lock is released, subsequent start succeeds.
  - Stop endpoint: state transitions to `stopped`, port released.
  - Delete endpoint: state transitions to `cleaned`, directory removed.

## Excluded

- AI auto-fix loops or any autonomous retry on failure.
- Production or cloud deployment modes.
- Distributed sandbox scheduling.
- Migrating the long-lived `SandboxManager` (used for AI ticket workers) — it has its own lifecycle and is unaffected.
- Automated cleanup of old environment sandboxes (no new cron or max-age policy beyond what already exists).
- Dashboard changes to `SandboxPanel.jsx` (long-lived sandboxes panel).

## Acceptance criteria

- After a completed validation (`state=validated`), calling Deploy & Test for the same project starts a new validation without returning `already running`.
- After deleting an environment sandbox (`state=cleaned`), calling either action starts a new sandbox without returning `already running`.
- After an unexpected worker crash, the supervisor detects the stale PID on next start and recovers (no 409).
- Deploy & Test (validation mode) leaves compose services stopped and the port slot free at the end of a successful run.
- Start Environment (environment mode) leaves compose services running after the worker exits; `GET /projects/{project_id}/sandbox/status` returns `state=environment`.
- Stop Environment transitions state to `stopped` and releases the port slot; compose services are down.
- Delete Environment transitions state to `cleaned`; sandbox directory and worktree are removed.
- Dashboard exposes both actions; environment sandboxes show Stop and Delete buttons; mode and state are visible.
- All new supervisor endpoints are idempotent (repeated calls do not error).
- All seven test scenarios listed under Tests pass.
