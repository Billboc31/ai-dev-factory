Here is the updated plan:

---

## Objective

Implement a safe, read-only AI auto-fix proposal workflow: on sandbox validation failure, collect generic failure context, call the configured AI runtime via the platform's `exec_cmd` subprocess abstraction, validate proposed patch paths, persist the proposal to disk, and surface it in the dashboard — without automatically applying any file changes or triggering sandbox reruns.

## Included

**Models** — `services/control_api/models/auto_fix.py`
- `ProposalStatus` enum: `idle`, `pending`, `ready`, `rejected`, `error`
- `PatchProposal`: relative_path, content, valid
- `AutoFixProposal`: proposal_id, project_id, sandbox_id, failing_step, status, reasoning, patches, context_snapshot, created_at, error

**Supervisor proposer** — `services/supervisor/auto_fix_proposer.py`
- `collect_failure_context(sandbox_id, project_root)` — reads deploy.yml, sandbox state, logs, scripts generically (no hardcoded service names, ports, or framework assumptions)
- `call_ai_runtime(context, exec_cmd, project_root)` — invokes the configured runtime via `shlex.split(exec_cmd) + ["--print"]` as subprocess (same pattern as `run_scripts.py:_invoke_llm`); parses JSON array response; raises on non-zero exit or malformed output
- `validate_patches(patches, project_root)` — rejects path traversal and anything outside `.ai-dev-factory/scripts/`
- `persist_proposal` / `load_proposal` / `list_proposals` — disk I/O under `${RUNTIME_ROOT}/auto-fix-proposals/{project_id}/{proposal_id}/state.json`

**Supervisor endpoints** (3 new, in `services/supervisor/main.py`):
- `POST /auto-fix/{project_id}/propose` — accepts `exec_cmd`, `sandbox_id`, `failing_step`; spawns proposer; returns `proposal_id`
- `GET /auto-fix/{project_id}/proposal/{proposal_id}`
- `GET /auto-fix/{project_id}/proposals`

**Control API** — `services/control_api/services/auto_fix_runner.py` + `routes/auto_fix.py` (proxy, mirrors `sandbox_runner.py`); registered in `main.py`

**Dashboard** — `apps/dashboard/src/api/autoFix.js` + `components/AutoFixPanel.jsx`; read-only patch preview on failed sandbox; registered in `App.jsx`

**Tests** — 8 proposer cases + 3 route cases (see plan file for full list)

## Excluded

Hardcoded provider env vars (`ANTHROPIC_API_KEY`, `AI_DEV_FACTORY_MODEL`), any provider SDK import, automatic patch application, sandbox reruns, retry/convergence loops, async orchestration, auto-triggering.

## Acceptance criteria

- `call_ai_runtime` uses only `exec_cmd` subprocess invocation — no provider SDK import in `auto_fix_proposer.py`
- Swapping AI provider requires only changing the `exec_cmd` value — no orchestrator code changes
- Malformed AI output → `status = error`, no crash
- Out-of-scope paths → `valid = false`, status `rejected`
- State survives process restart
- Dashboard shows read-only patch previews; no file modified, no sandbox rerun
- No hardcoded service/port/framework assumptions in context collector
- `pytest tests/test_auto_fix_proposer.py tests/test_auto_fix_routes.py` passes

---

The key fix from the review: `call_ai_runtime` now mirrors the `_invoke_llm` pattern from `run_scripts.py` — provider-agnostic subprocess invocation via a caller-supplied `exec_cmd` string. No SDK, no hardcoded env vars. The plan file has been written to `runs/T138/plan.md`.
