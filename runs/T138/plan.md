Here is the implementation plan for T138:

---

## Objective

Add a generic AI-driven sandbox auto-fix loop that, on validation failure, captures sandbox state and operational scripts, calls the configured AI runtime, applies patches restricted to allowed operational files, reruns validation, and repeats until success or a configurable retry limit is reached — without any ai-dev-factory-specific assumptions.

## Included

### Models — `services/control_api/models/auto_fix.py`
- `AutoFixStatus` enum: `idle`, `running`, `success`, `failed`, `error`
- `AutoFixIteration`: per-iteration record — iteration number, status, failing step, changed files list, log excerpt, sandbox run ID
- `AutoFixState`: top-level state — project_id, auto_fix_id, status, current_iteration, max_retries, iterations list, started_at, finished_at, final_sandbox_id

### Supervisor orchestrator — `services/supervisor/auto_fix_orchestrator.py`
- `AutoFixOrchestrator` class, async
- `run(project_id, max_retries)`: acquires per-project lock; loop: trigger sandbox run → if success → done; if failed → collect context → call AI → validate patches → apply patches → persist iteration state → repeat; exits with `failed` when max_retries reached
- State written after every iteration to `${RUNTIME_ROOT}/auto-fix/{project_id}/{auto_fix_id}/state.json`
- `_collect_context(sandbox_state, logs, scripts_dir)` → generic dict (deploy.yml content, component list, failing step, logs, scripts, iteration number); no hardcoded service names or ports
- `_call_ai(context)` → list of `{relative_path, content}` patch objects using Claude Messages API (claude-sonnet-4-6)
- `_validate_patches(patches, allowed_files)` → rejects any path outside allowed set
- `_apply_patches(project_root, patches)` → writes files atomically, returns changed paths
- `_allowed_files(project_root)` → restricted to `.ai-dev-factory/scripts/*.sh` only

### Supervisor endpoints added to `services/supervisor/main.py`
- `POST /auto-fix/{project_id}` — `{max_retries: int}`; spawns async task; returns `{auto_fix_id}`
- `GET /auto-fix/{project_id}` — returns current `AutoFixState`
- `GET /auto-fix/{project_id}/history` — list of all past `AutoFixState` records
- `DELETE /auto-fix/{project_id}/{auto_fix_id}` — removes state directory

### Control API — `services/control_api/services/auto_fix_runner.py` + `routes/auto_fix.py`
- HTTP-proxy client (`AutoFixRunner`) mirroring the `SandboxRunner` pattern
- Routes: `POST/GET /api/projects/{project_id}/auto-fix`, `GET /api/projects/{project_id}/auto-fix/history`
- Registered in `services/control_api/main.py`

### Dashboard — `apps/dashboard/src/components/AutoFixPanel.jsx` + `src/api/autoFix.js`
- Trigger button with max_retries input (default 5)
- Status badge, progress bar (current_iteration / max_retries)
- Iterations accordion: status, failing step, changed files, log excerpt per iteration
- Final outcome section; polls GET every 3 s while `running`
- Registered in `apps/dashboard/src/App.jsx`

### Tests
- `tests/test_auto_fix_orchestrator.py`: successful convergence, retry limit exhausted, malformed AI output rejected, disallowed file path rejected, patch I/O failure handled, generic deploy.yml (no hardcoded services), iteration state persisted mid-loop
- `tests/test_auto_fix_routes.py`: trigger returns auto_fix_id, status returns AutoFixState, history returns list

## Excluded
- Automatic merge to main after successful auto-fix
- Production/cloud deployment support
- Modifying files outside `.ai-dev-factory/scripts/*.sh`
- Tester-agent business-level tests
- Self-modifying core runtime outside allowed sandbox artifacts
- UI display of raw AI prompts/full response payloads
- Multi-project concurrent auto-fix coordination
- Auto-triggering on sandbox failure (manual trigger only in this ticket)

## Acceptance criteria
- `POST /api/projects/{project_id}/auto-fix` triggers the loop and returns an `auto_fix_id`; `GET` reflects live state while running
- Loop terminates at most after `max_retries` iterations; `AutoFixState.status` is `failed` with full iteration history at the limit
- Malformed or out-of-scope AI output is rejected without crashing the orchestrator; affected iteration recorded as `error`
- Iteration state written to disk after every iteration, readable independently of the running process
- Each iteration reruns sandbox validation and captures new logs and state
- Successful fix sets `AutoFixState.status = success` with `final_sandbox_id` populated
- Dashboard renders current_iteration/max_retries progress, per-iteration details, and final outcome
- No ai-dev-factory-specific service names, fixed ports, or project paths hardcoded in orchestrator or models
- `pytest tests/test_auto_fix_orchestrator.py tests/test_auto_fix_routes.py` passes

---

The plan is saved to `runs/T138/plan.md`. The core architectural choice is to place the AI call and orchestration loop in the supervisor (host-side), which already owns path mapping, per-project locking, and subprocess management — the control API and dashboard simply proxy through it as they do for existing sandbox features.
