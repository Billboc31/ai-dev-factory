Now I have a complete picture of the codebase. Let me write the plan.

## Objective

Add a generic smoke test step to the sandbox/deployer validation pipeline, then build a bounded AI auto-fix deployment loop that collects failure context, calls the configured AI runtime (provider-agnostic), applies patches constrained to allowed deployment artifacts, and repeats until success or retry limit — recording every iteration for observability.

## Included

### 1. Smoke test step — `tools/agent_runner/run_sandbox.py`

- After the `healthcheck` step, check for `.ai-dev-factory/scripts/smoke.sh`
- If present: execute it with the same env vars already in scope (`SANDBOX_ID`, `API_PORT`, `WEB_PORT`, proxy URLs); capture exit code, stdout, stderr
- If absent: record step status as `skipped` (never fail the pipeline for a missing smoke script)
- Extend `state.json` `steps` dict with a `smoke` entry matching the existing step schema: `status`, `exit_code`, `started_at`, `finished_at`
- `smoke.sh` is **not** added to `_REQUIRED_SCRIPTS`; it remains optional

### 2. Smoke test step — `services/control_api/services/deployer_runner.py`

- Add `_run_smoke_tests(project_root: Path, env: dict) -> ActionResult`; runs `smoke.sh` if present, skips otherwise
- Call it immediately after `_run_healthcheck()` succeeds inside `_do_deploy()`
- Extend `DeployProfile` (Pydantic model) with an optional `smoke` block:
  ```yaml
  smoke:
    script: .ai-dev-factory/scripts/smoke.sh   # optional override
    timeout: 60
  ```
- Extend deploy state JSON with `healthcheck_status` and `smoke_status` fields (values: `skipped | success | failed`)
- No change to existing `healthcheck` logic or state fields

### 3. Bounded AI auto-fix loop — `services/control_api/services/deployer_runner.py`

New function:
```python
run_deploy_with_autofix(
    project_id: str,
    project_root: Path,
    exec_cmd: str,
    max_retries: int = 3,
    sandbox_manager=None,
    sandbox=None,
) -> ActionResult
```

Inner loop (up to `max_retries`):
1. Call `_do_deploy()` (or sandboxed variant)
2. If success: cleanup and return
3. On failure:
   a. `_collect_deploy_failure_context(project_root, iteration)` → dict with: failing step, error message, last N lines of `deploy.log`, current deploy state JSON
   b. Read `allowed_fix_paths` from `deploy.yml` (new optional field; defaults to `[".ai-dev-factory/scripts/*", "docker-compose*.yml", ".env*", "deploy.yml"]`)
   c. Compose deployer-fixer prompt from `ai/roles/deployer-fixer.md` + failure context + allowed paths
   d. Call `execute_external_command(exec_cmd, prompt)` — no provider SDK
   e. Parse AI stdout for file patches (unified diff blocks fenced as ` ```diff `)
   f. `_apply_patches(patches, project_root, allowed_fix_paths)` — skip any patch targeting a path outside the allowlist, log skipped paths
   g. If no allowed patches applied → stagnation → break loop early
   h. If same error as previous iteration (identical `error` field) → stagnation → break loop early
   i. Persist iteration record (see §4)

### 4. Iteration history persistence

- Path: `.ai-dev-factory/deploy-iterations/iteration-{N}.json` (project mode) or `$RUNTIME_ROOT/state/deploy-iterations/iteration-{N}.json` (runtime mode); follows same path-resolution pattern as `deploy-state.json`
- Each record:
  ```json
  {
    "iteration": 1,
    "started_at": "...",
    "finished_at": "...",
    "failure_reason": "...",
    "failing_step": "smoke",
    "changed_files": ["..."],
    "patch_summary": "...",
    "health_status": "success|failed|skipped",
    "smoke_status": "success|failed|skipped",
    "log_tail": "..."
  }
  ```
- On terminal failure (all retries exhausted): write `deploy-iterations/summary.json` with outcome, total iterations, final error, artifact paths; do NOT delete intermediate records
- On success: write summary, call `run_undeploy()` + `run_cleanup()`

### 5. Deployer-fixer role file — `ai/roles/deployer-fixer.md`

New file defining:
- Input contract: receives failure context (step, logs, error, allowed paths)
- Output contract: responds with zero or more unified diff blocks (` ```diff `) targeting only files in `allowed_fix_paths`
- Explicit constraints: never modify application source; never propose merge or push operations; produce one patch per file maximum

### 6. `DeployProfile` schema extension — `services/control_api/services/deployer_runner.py`

Add two optional fields to the Pydantic model:
```python
class SmokeCfg(BaseModel):
    script: str = ".ai-dev-factory/scripts/smoke.sh"
    timeout: int = 60

class AutoFixCfg(BaseModel):
    max_retries: int = 3
    allowed_paths: list[str] = [".ai-dev-factory/scripts/*", "docker-compose*.yml", ".env*", "deploy.yml"]

class DeployProfile(BaseModel):
    ...
    smoke: SmokeCfg | None = None
    auto_fix: AutoFixCfg | None = None
```

### 7. REST API exposure — `services/control_api/routes/deployer.py`

- New endpoint: `POST /deployer/deploy-with-autofix`
- Body: `project_id`, `exec_cmd`, `max_retries` (optional, default from config)
- Returns: same `ActionResult` shape as existing `/deployer/deploy`
- New endpoint: `GET /deployer/deploy-iterations` — lists iteration JSON files for the current project

## Excluded

- Production or cloud deployment targets
- Automatic merge to main or any branch after successful loop
- Modifying arbitrary application source files (outside `allowed_fix_paths`)
- Full business/UAT tester-agent tests (tracked separately)
- Persistent environment management beyond the current sandbox lifetime
- Support for patch formats other than unified diff in AI output
- UI changes beyond what is needed to surface the new state fields

## Acceptance criteria

- `run_sandbox.py` executes `smoke.sh` when present; records a `smoke` step in `state.json` with `status`, `exit_code`, `started_at`, `finished_at`; step is absent (not failed) when script is missing
- `deployer_runner.py` deploys → healthcheck → smoke tests in sequence; deploy state JSON exposes `healthcheck_status` and `smoke_status` as distinct fields
- `run_deploy_with_autofix()` invokes `execute_external_command(exec_cmd, prompt)` with no import of any AI provider SDK
- AI patches that target paths outside `allowed_fix_paths` are silently skipped; at least one skipped-path warning is logged
- Loop halts before `max_retries` if the same `error` string repeats across consecutive iterations (stagnation guard)
- Each iteration produces a valid `iteration-{N}.json` under the iterations directory before the next iteration begins
- Successful loop: `run_undeploy()` is called, `summary.json` records `outcome: success`
- Failed loop (retries exhausted): all `iteration-{N}.json` files are preserved, `summary.json` records `outcome: failed` with final error
- `ai/roles/deployer-fixer.md` exists and defines the input/output contract
- `POST /deployer/deploy-with-autofix` endpoint accepts `exec_cmd` and `max_retries` and returns an `ActionResult`
- `GET /deployer/deploy-iterations` returns the list of iteration records for the active project
