All done. Here's a summary of what was implemented:

---

## Changes implemented

### `services/control_api/models/schemas.py`
- Added `healthcheck_status` and `smoke_status` fields (`Literal["skipped","success","failed"]`, default `"skipped"`) to `SandboxValidationState` and `SandboxValidationStatus`
- Added `smoke_status` to `DeployState` and `DeployerStatus`

### `services/control_api/services/deployer_runner.py`
- Added `_run_smoke_tests(cwd, log_path)` — runs `.ai-dev-factory/scripts/smoke.sh` if present, skips otherwise
- Wired it into `_do_deploy()` after healthcheck passes; state writes now carry `smoke_status`
- `get_deploy_state()` reads `smoke_status` from persisted state

### `services/control_api/routes/deployer.py`
- `get_deployer_status` passes `smoke_status` through to `DeployerStatus`

### `tools/agent_runner/run_sandbox.py`
- Added `_SMOKE_SCRIPT = "smoke.sh"` constant
- Added `_run_smoke_tests()` — same pattern as required scripts, injects proxy URLs via `extra_env`
- Added `_write_validation_json()` — writes `{sandbox_runtime_root}/validation.json` with full result after every run
- Added `_call_fix_proposer()` — pipes context to `AI_DEV_FACTORY_EXEC_CMD` and writes `fix-proposal.md` when smoke fails; no SDK hardcoded
- `_do_sandbox()` now: derives `healthcheck_status` from steps, runs smoke tests (validation mode only), writes `validation.json` always, calls fix proposer on smoke failure, persists both status fields in state

### `ai/roles/deployer-fixer.md` (new)
- Defines the AI role for fix-proposal generation: inputs, output format, constraints

### Tests (58 pass, 0 regressions in our files)
- **`test_run_sandbox_worker.py`**: 10 new cases — absent/pass/fail smoke, proxy URL injection, `validation.json` content on success/failure, `fix-proposal.md` with/without `exec_cmd`, smoke not invoked on required-script failure, `healthcheck_status` on HC failure
- **`test_deployer_execution.py`**: 3 new cases — smoke pass/fail/absent recorded correctly in deployer state
