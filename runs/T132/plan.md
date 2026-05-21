I now have a complete picture of the architecture. Let me produce the plan.

---

## Objective

Add a "Generate Scripts" async action to the deployer that uses the AI runtime (via the existing supervisor subprocess pattern) to produce six reviewable shell scripts and an updated `deployment.md`, commits them to a dedicated branch, and creates or updates a PR — mirroring the existing analysis flow end-to-end.

## Included

### `tools/agent_runner/scripts_prompt_builder.py` (new)
- `build_scripts_prompt(project_root, scan_result, file_tree, deploy_profile_text)` — constructs the LLM prompt requesting FILE blocks for `bootstrap.sh`, `build.sh`, `start.sh`, `stop.sh`, `restart.sh`, `healthcheck.sh`, and `deployment.md` under `.ai-dev-factory/scripts/` and `.ai-dev-factory/` respectively.

### `tools/agent_runner/scripts_git_service.py` (new)
- `commit_and_push(project_root, project_id)` — mirrors `analysis_git_service.py`: branch `ai-scripts/{project_id}-{timestamp}`, stages `.ai-dev-factory/scripts/` and `.ai-dev-factory/deployment.md`, creates or updates PR via `gh`.

### `tools/agent_runner/run_scripts.py` (new)
- CLI entrypoint `--project-root`, `--project-id`, `--exec-cmd` — mirrors `run_analysis.py` structure:
  1. Write `state=running` to `state/scripts-{project_id}.json`
  2. Read `deploy.yml` from project root (if present) to include in prompt context
  3. Build prompt via `scripts_prompt_builder`
  4. Invoke LLM subprocess, parse FILE blocks
  5. Validate all 7 required paths are present; reject any path escaping project root
  6. Write files; `chmod` scripts to `0o755`
  7. Commit and push via `scripts_git_service`
  8. Write `state=success` with branch and PR URL; on exception write `state=failed`

### `services/supervisor/main.py` (modify)
- Add `_run_scripts_path()` helper pointing to `run_scripts.py`
- Add `_scripts_pid_path(project_id)`, `_scripts_log_path(project_id)`, `_scripts_state_path(project_id)`, `_read_scripts_state(project_id)`, `_scripts_current_pid(project_id)` — exact mirrors of the `_analysis_*` helpers
- Add `_scripts_locks` dict + `_get_scripts_lock(project_id)` mutex
- Add `POST /scripts/start` endpoint (body: `ScriptsStartRequest` with `project_root`, `project_id`, `exec_cmd`)
- Add `GET /scripts/{project_id}/status`, `GET /scripts/{project_id}/logs`, `POST /scripts/{project_id}/stop` endpoints — exact mirrors of the `/analysis/` routes

### `services/control_api/services/scripts_manager.py` (new)
- `start_scripts_generation(project_id, project_root, exec_cmd, supervisor_url)` → `ActionResult`
- `get_scripts_status(project_id, supervisor_url)` → `ScriptsStatus`
- `get_scripts_logs(project_id, supervisor_url, lines)` → `list[str]`
- All three mirror `analysis_manager.py` but target `/scripts/*` supervisor endpoints.

### `services/control_api/models/schemas.py` (modify)
- Add `ScriptsStatus(BaseModel)` — same fields as `AnalysisStatus` (`state`, `branch`, `pr_url`, `error`, `started_at`, `finished_at`)

### `services/control_api/routes/deployer.py` (modify)
- Add `POST /projects/{project_id}/deployer/generate-scripts` — calls `scripts_manager.start_scripts_generation()`
- Add `GET /projects/{project_id}/deployer/scripts/status` — calls `scripts_manager.get_scripts_status()`
- Add `GET /projects/{project_id}/deployer/scripts/logs` — calls `scripts_manager.get_scripts_logs()`

### `apps/dashboard/src/api/deployer.js` (modify)
- Add `generateScripts(projectId)`, `getScriptsStatus(projectId)`, `getScriptsLogs(projectId, lines)` functions.

### `apps/dashboard/src/pages/DeployerPage.jsx` (modify)
- Add "Generate Scripts" button that calls `generateScripts()`
- Add scripts status panel: state badge, branch name, PR URL as clickable link, error message
- Add scripts log panel polling `getScriptsLogs()` every 5 s when state is `running`

### `tests/test_scripts_generation.py` (new)
- Unit tests for `scripts_prompt_builder` — verify all 7 output file paths appear in the prompt
- Unit tests for `run_scripts.py` `main()` with mocked `subprocess.run` (LLM call) and mocked `commit_and_push` — verify: state written as success with branch/PR, scripts written with `0o755` mode, path-escape check raises, missing required file block raises
- Unit tests for `scripts_git_service.commit_and_push` with mocked `subprocess.run` — verify branch name pattern `^ai-scripts/proj1-\d{8}-\d{6}$`, PR create vs update logic

## Excluded

- Executing the generated scripts
- Sandbox or staging deployment
- Healthcheck polling loop
- Tester agent and auto-merge
- Modifying existing deploy, analysis, or daemon workflows
- Changes to `analysis_manager.py`, `analysis_git_service.py`, `run_analysis.py`, or their tests

## Acceptance criteria

- `POST /projects/{id}/deployer/generate-scripts` returns `{"ok": true}` and starts the async subprocess via the supervisor
- Supervisor logs show `run_scripts.py` spawned and the 7 FILE blocks written
- State file `state/scripts-{id}.json` transitions `idle → running → success` with `branch` and `pr_url` populated
- All 6 generated scripts in `.ai-dev-factory/scripts/` have execute permission (`0o755`)
- `deployment.md` explains the purpose and usage of each script
- `GET /projects/{id}/deployer/scripts/status` returns the correct state, branch, and PR URL
- A PR exists on branch `ai-scripts/{project_id}-*` in the target repo
- Dashboard renders a scripts status panel with state badge, branch, PR link, and live logs
- `pytest tests/test_scripts_generation.py` passes with all AI/git/gh calls mocked
- All pre-existing deployer and analysis tests continue to pass
