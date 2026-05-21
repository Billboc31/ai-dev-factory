## Objective

Add an automated deploy/test/fix loop inside sandbox deployments: when deployment or healthcheck fails, capture logs, send them to the AI runtime for script correction, apply fixes to the repo branch, and retry — up to a configurable limit — with each iteration visible in the dashboard.

## Included

**`services/control_api/services/deployer_runner.py`**
- Add `fixing` state to the deployment state machine (between `failed` and retry)
- Add `fix_iteration` counter and `max_fix_retries` field to deployment state
- Expose `failed_logs` (combined deploy + healthcheck stderr) as a structured field in state

**`services/control_api/services/fix_loop_manager.py`** *(new)*
- `start_fix_loop(project_id, deploy_yml_path, max_retries)` — orchestrates the full loop
- Reads failure logs from deployer_runner state
- Calls AI runtime (via existing supervisor/analysis_manager pattern) with: failed scripts, deploy config, and captured logs
- Receives and applies AI-returned file patches to the working branch
- Commits and pushes fixes to the PR branch (`git commit + git push`)
- Triggers re-deploy via deployer_runner
- Stops at `max_retries` and sets final state to `failed` with iteration history

**`services/control_api/routes/fix_loop.py`** *(new)*
- `POST /fix-loop/{project_id}/start` — body: `{max_retries: int}` — initiates loop in background thread
- `GET /fix-loop/{project_id}/status` — returns `{state, fix_iteration, max_fix_retries, history: [{iteration, result, log_excerpt}]}`

**`services/control_api/main.py`**
- Register new fix_loop router

**`apps/dashboard/src/api/deployer.js`**
- Add `startFixLoop(projectId, maxRetries)` and `getFixLoopStatus(projectId)` API calls

**`apps/dashboard/src/pages/DeployerPage.jsx`**
- Add "Fix Loop" section: shows current iteration / max, per-iteration result badges (fixing / retrying / success / failed), and a log excerpt per iteration
- "Start Fix Loop" button visible when deploy state is `failed`

**`tests/test_fix_loop.py`** *(new)*
- Test: failed deploy triggers fix loop entry
- Test: AI runtime receives correct payload (logs + scripts)
- Test: applied fix causes re-deploy and success
- Test: retry limit stops the loop and sets state to `failed`
- Test: successful healthcheck after fix marks state `healthy`/`success`

**`.ai-dev-factory/deploy.yml`**
- Add optional `fix_loop.max_retries` field (default: 3) to deploy profile schema

## Excluded

- Tester agent integration
- Production or remote/cloud deployment
- Auto-merge to main after successful fix loop
- Full end-to-end business logic testing
- Changes to the supervisor daemon's own retry policies (`_RETRY_POLICIES` in `run_daemon.py`)
- AI prompt engineering beyond passing logs + scripts as context

## Acceptance criteria

- A sandbox with a deliberately broken deploy script triggers the fix loop automatically after deploy or healthcheck failure
- Each fix iteration is recorded with its outcome and visible in the dashboard under the deploy entry
- The AI runtime receives the captured failure logs and the current script content in each fix request
- The PR branch is updated (commit + push) after each AI-generated fix
- When healthcheck passes after a fix, the deployment state is `success` and the loop stops
- When `max_fix_retries` is reached without success, the state is permanently `failed` with the full iteration history
- `tests/test_fix_loop.py` passes with all five test cases
- The main runtime process is unaffected by sandbox fix-loop failures (loop runs in an isolated thread per project)
