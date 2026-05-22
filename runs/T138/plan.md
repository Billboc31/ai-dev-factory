The plan is written. Here it is:

---

## Objective

Implement a safe, read-only AI auto-fix proposal workflow: on sandbox validation failure, collect generic failure context, call the configured AI runtime, validate proposed patch paths, persist the proposal to disk, and surface it in the dashboard — without automatically applying any file changes or triggering sandbox reruns.

## Included

**Models** — `services/control_api/models/auto_fix.py`
- `ProposalStatus` enum: `idle`, `pending`, `ready`, `rejected`, `error`
- `PatchProposal`: relative_path, content, valid
- `AutoFixProposal`: proposal_id, project_id, sandbox_id, failing_step, status, reasoning, patches, context_snapshot, created_at, error

**Supervisor proposer** — `services/supervisor/auto_fix_proposer.py`
- `collect_failure_context(sandbox_id, project_root)` — reads deploy.yml, sandbox state, logs, scripts generically (no hardcoded service names or ports)
- `call_ai_runtime(context)` — reads `AI_DEV_FACTORY_MODEL` + `ANTHROPIC_API_KEY` from env (errors if unset); sends generic prompt; parses JSON array response
- `validate_patches(patches, project_root)` — rejects path traversal and anything outside `.ai-dev-factory/scripts/`
- `persist_proposal` / `load_proposal` / `list_proposals` — disk I/O under `${RUNTIME_ROOT}/auto-fix-proposals/{project_id}/{proposal_id}/state.json`

**Supervisor endpoints** (3 new, in `services/supervisor/main.py`):
- `POST /auto-fix/{project_id}/propose`
- `GET /auto-fix/{project_id}/proposal/{proposal_id}`
- `GET /auto-fix/{project_id}/proposals`

**Control API** — `services/control_api/services/auto_fix_runner.py` + `routes/auto_fix.py` (proxy pattern, mirrors `sandbox_runner.py`); registered in `main.py`

**Dashboard** — `apps/dashboard/src/api/autoFix.js` + `components/AutoFixPanel.jsx`; shown on failed sandbox; read-only patch preview, no apply button; registered in `App.jsx`

**Tests** — `tests/test_auto_fix_proposer.py` (8 cases) + `tests/test_auto_fix_routes.py` (3 cases)

## Excluded

Automatic patch application, sandbox reruns, retry loops, convergence logic, async orchestration, multi-project concurrency, auto-triggering.

## Acceptance criteria

- Proposal endpoint returns `proposal_id`; status/patches readable via GET
- Malformed AI output → `status = error`, no crash
- Out-of-scope paths → `valid = false`, proposal persisted as `rejected`
- State survives process restart (written to disk)
- Dashboard shows read-only patch previews; no file is modified, no sandbox is rerun
- No ai-dev-factory-specific assumptions in orchestrator or models
- `pytest tests/test_auto_fix_proposer.py tests/test_auto_fix_routes.py` passes
