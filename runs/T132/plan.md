## Objective

Add a "generate scripts" action to the deployer workflow that uses the configured AI runtime to produce six operational shell scripts and a `deployment.md` for a managed project, commits them to a dedicated branch, and opens a PR for human review — mirroring the existing analysis flow end-to-end.

## Included

### New files

- **`tools/agent_runner/scripts_prompt_builder.py`** — `build_scripts_prompt(project_root, scan_result, deploy_profile_yaml, file_tree) -> str` — assembles the LLM prompt requesting exactly seven FILE blocks (6 scripts + deployment.md).

- **`tools/agent_runner/run_scripts.py`** — CLI entrypoint (`--project-root`, `--project-id`, `--exec-cmd`); mirrors `run_analysis.py`: load deploy.yml → build prompt → invoke LLM → extract FILE blocks → write `scripts/*.sh` with `chmod 0o755` + `deployment.md` → call git service → write `state/scripts-{project_id}.json`.

- **`tools/agent_runner/scripts_git_service.py`** — `commit_and_push(project_root, project_id) -> (branch, pr_url)`: creates branch `ai-scripts/{project_id}-YYYYMMDD-HHMMSS`, stages `.ai-dev-factory/scripts/` and `.ai-dev-factory/deployment.md`, commits, pushes, creates/updates PR via `gh`.

- **`services/control_api/services/scripts_manager.py`** — `start_scripts_generation()`, `get_scripts_status()`, `get_scripts_logs()` — mirrors `analysis_manager.py`; calls supervisor at `/scripts/*`.

- **`tests/test_scripts_generation.py`** — unit tests for `scripts_prompt_builder` (expected FILE block list present in prompt), `run_scripts.py` (mocked LLM subprocess + git/gh calls; success path, missing FILE block error, partial output error), `scripts_git_service` (mocked `subprocess.run`; branch naming, `gh pr create` invocation).

### Modified files

- **`services/supervisor/main.py`** — add `_scripts_pid_path()`, `_scripts_log_path()`, `_scripts_state_path()`, `_scripts_locks` dict, `_get_scripts_lock()`, and four endpoints: `POST /scripts/start`, `GET /scripts/{project_id}/status`, `GET /scripts/{project_id}/logs`, `POST /scripts/{project_id}/stop` — mirrors the `/analysis/*` block.

- **`services/control_api/routes/deployer.py`** — add three endpoints: `POST /projects/{project_id}/deployer/generate-scripts`, `GET /projects/{project_id}/deployer/scripts/status`, `GET /projects/{project_id}/deployer/scripts/logs`.

- **`services/control_api/models/schemas.py`** — add `ScriptsStatus(BaseModel)` with fields `state`, `started_at`, `finished_at`, `branch`, `pr_url`, `error` (mirrors `AnalysisStatus`).

- **`apps/dashboard/src/api/deployer.js`** — add `generateScripts(projectId)`, `getScriptsStatus(projectId)`, `getScriptsLogs(projectId, lines)`.

- **`apps/dashboard/src/pages/DeployerPage.jsx`** — add "Generate Scripts" button; scripts status panel (state badge, branch, PR link, error); scripts log panel polling every 5 s when `state === "running"`.

### Generated artefacts (in managed project, not in factory repo)

`.ai-dev-factory/scripts/bootstrap.sh`, `build.sh`, `start.sh`, `stop.sh`, `restart.sh`, `healthcheck.sh` (all `chmod 0o755`) and `.ai-dev-factory/deployment.md`.

## Excluded

- Executing any generated script.
- Sandbox or staging deployment triggered by the factory.
- Healthcheck polling loop in the factory runtime.
- Tester agent or automated test generation for the managed project.
- Auto-merging the generated scripts PR.
- Modifying the existing deploy/restart/analyze flows.
- Any change to the daemon or planner/coder/reviewer agents.

## Acceptance criteria

- `POST /projects/{id}/deployer/generate-scripts` returns `{"ok": true}` and triggers a supervisor subprocess.
- `GET /projects/{id}/deployer/scripts/status` returns `state: "success"`, a non-empty `branch`, and a non-empty `pr_url` after a successful generation run.
- All six `scripts/*.sh` files exist in the managed project, are readable, and have execute permission (`0o755`).
- `.ai-dev-factory/deployment.md` exists and contains content.
- A branch named `ai-scripts/{project_id}-*` is pushed and a PR is created or updated in the managed project's repository.
- `GET /projects/{id}/deployer/scripts/status` returns `state: "failed"` with a non-empty `error` when the LLM output is missing one or more FILE blocks.
- Dashboard "Generate Scripts" button is visible; the status panel updates without page reload; the PR link is rendered when `state === "success"`.
- `pytest tests/test_scripts_generation.py` passes with all AI/Git/PR calls mocked.
- Existing deployer tests (`test_deployer_routes.py`, `test_deployer_execution.py`) still pass without modification.
