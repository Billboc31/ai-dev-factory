Now I have enough context to write the plan. Here it is:

---

## Objective

Add a generic smoke-test lifecycle after healthcheck in the sandbox validation pipeline, persist distinct health/smoke results as observable artifacts, and optionally generate an AI fix proposal on failure — without applying any patch automatically.

## Included

### `tools/agent_runner/run_sandbox.py`
- After the existing `_run_healthcheck()` call, add a `_run_smoke_tests()` function that:
  - checks whether `.ai-dev-factory/scripts/smoke.sh` exists in the worktree
  - if absent, sets `smoke_status = "skipped"` and continues
  - if present, executes it inside the sandbox environment with proxy URLs injected as env vars (`SANDBOX_WEB_URL`, `SANDBOX_API_URL`) when available, falling back to direct port env vars
  - captures stdout/stderr to the sandbox run log
  - maps exit 0 → `"success"`, non-zero → `"failed"`
- After smoke tests, write a `validation.json` artifact to `${SANDBOX_RUNTIME_ROOT}/validation.json` containing: `sandbox_id`, `healthcheck_status`, `smoke_status`, `failing_step`, `proxy_urls`, `ports`, `timestamps`, and a log path reference
- If smoke tests fail and `AI_DEV_FACTORY_EXEC_CMD` is set, invoke the AI runtime via `exec_cmd` to generate a fix proposal (read-only): pipe context (validation.json + relevant logs + deploy artifacts list) to the command and write the output to `${SANDBOX_RUNTIME_ROOT}/fix-proposal.md`; do not parse or apply the output

### `services/control_api/models/schemas.py`
- Add `"skipped"` to the allowed values of `SandboxValidationStep.status`
- Add `smoke_status: Literal["skipped", "success", "failed"] = "skipped"` field to `SandboxValidationState`
- Add `healthcheck_status: Literal["skipped", "success", "failed"] = "skipped"` field to `SandboxValidationState` (currently implicit from `steps`)

### `services/control_api/services/deployer_runner.py`
- After `_run_healthcheck()` succeeds, call a new `_run_smoke_tests()` function following the same pattern as run_sandbox.py
- Update `DeployState` or its equivalent state JSON to record `smoke_status` alongside the existing health fields

### `ai/roles/deployer-fixer.md` (new file)
- Defines the AI role for fix-proposal generation: inputs (validation.json, logs, deploy artifact list), output format (unified diff or shell patch with explanation), constraints (only deployment artifacts, no application source)

### Tests
- `tests/test_run_sandbox_worker.py`: add cases for smoke.sh present/absent, exit 0/non-zero, proxy URL injection, validation.json content, fix-proposal.md creation when exec_cmd is set
- `tests/test_deployer_execution.py`: add case for smoke step being recorded in state

## Excluded

- Automatic patch application (deferred to follow-up ticket)
- Redeploy loop / retry orchestration
- Progress detection and stagnation guard
- Failure classifier
- Automatic smoke test generation
- Iteration history JSON (`iteration-{N}.json`, `summary.json`)
- `AutoFixCfg` schema and `allowed_fix_paths` policy enforcement
- New REST endpoints (`/deploy-with-autofix`, `/deploy-iterations`)
- Cloud or production deployment
- Automatic merge
- Tester-agent / UAT flows
- Modifying arbitrary application source files

## Acceptance criteria

- `run_sandbox.py` executes `smoke.sh` after healthcheck when the file exists in the worktree; skips it without error when absent
- Smoke test receives proxy URLs (`SANDBOX_WEB_URL`, `SANDBOX_API_URL`) as env vars when a proxy route is registered, direct port vars otherwise
- `SandboxValidationState` exposes distinct `healthcheck_status` and `smoke_status` fields (not collapsed into a single boolean)
- `validation.json` is written to `${SANDBOX_RUNTIME_ROOT}/validation.json` after the validation pipeline regardless of outcome
- When `AI_DEV_FACTORY_EXEC_CMD` is set and smoke tests fail, `fix-proposal.md` is written; no file outside `${SANDBOX_RUNTIME_ROOT}` is modified
- No hardcoded AI provider SDK is introduced; only `exec_cmd` shell invocation is used
- Cleanup/undeploy still executes automatically after validation (success or failure)
- All new schema fields pass existing Pydantic validation; `"skipped"` is accepted where previously only `"success"`/`"failed"` were valid
- New test cases in `test_run_sandbox_worker.py` and `test_deployer_execution.py` pass
