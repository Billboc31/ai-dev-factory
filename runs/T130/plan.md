Now I have a clear picture of the architecture. Let me write the plan.

## Objective

Add an AI-assisted "Analyze Project" workflow where the dashboard triggers analysis via the control API, which delegates to the host supervisor; the supervisor spawns a host-side analysis worker that runs the LLM, creates a git branch, commits generated operational files, and opens a PR — with status and logs visible in the dashboard.

## Included

### Host supervisor — new endpoints

**`services/supervisor/main.py`** (extend existing)
- `POST /analysis/start` — accepts `{project_root: str, project_id: str, exec_cmd: str}`; acquires per-project lock; spawns `tools/agent_runner/run_analysis.py` as background `subprocess.Popen`; writes PID to `runs/analysis-{project_id}.pid`; returns `{ok: bool}` or `{error: "locked"}` (HTTP 409)
- `GET /analysis/{project_id}/status` — reads `runs/T*/analysis-state.json` (or `state/analysis-{project_id}.json`) and returns it; returns `{state: "idle"}` if file absent
- `GET /analysis/{project_id}/logs` — tails `logs/analysis-{project_id}.log`; query param `lines=100`
- `POST /analysis/{project_id}/stop` — `SIGTERM` to analysis PID if running

### Host analysis worker — new script

**`tools/agent_runner/run_analysis.py`** (new)
- Entry point for host-side execution; receives `--project-root`, `--project-id`, `--exec-cmd` CLI args
- Orchestrates sequentially:
  1. Write `state=running` to state file
  2. Call `project_scanner.scan_project(project_root)` (import shared service)
  3. Build file tree string (walk `project_root`, filter `.git`/`__pycache__`/`node_modules`, max depth 4)
  4. Call `analysis_prompt_builder.build_analysis_prompt(project_root, scan_result, file_tree)`
  5. Invoke LLM via `exec_cmd` (subprocess with prompt on stdin or `--message` flag matching daemon pattern)
  6. Parse LLM output → extract `deploy.yml` and `deployment.md` blocks; optionally `runtime-notes.md`
  7. Write files to `project_root/.ai-dev-factory/`
  8. Call `analysis_git_service.commit_and_push(project_root, project_id)` → returns branch name + PR URL
  9. Write `state=success` + `branch`, `pr_url` to state file
- On any exception: write `state=failed` + `error` message to state file
- All stdout/stderr redirected to `logs/analysis-{project_id}.log`

### Host analysis support modules

**`tools/agent_runner/analysis_prompt_builder.py`** (new)
- `build_analysis_prompt(project_root, scan_result, file_tree) -> str`
- Assembles: file tree string + `ScanResult` as JSON + `DeployProfile` JSON schema spec + explicit generation instructions for all three target files
- Pure string construction; no I/O; no LLM dependency

**`tools/agent_runner/analysis_git_service.py`** (new)
- `commit_and_push(project_root: Path, project_id: str) -> tuple[str, str]` — returns `(branch_name, pr_url)`
- Branch naming: `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}`
- Steps: `git checkout -b {branch}`, `git add .ai-dev-factory/`, `git commit -m "chore: AI-generated operational files"`, `git push -u origin {branch}`, `gh pr create` (or detect existing open PR with `gh pr list` and call `gh pr edit`)
- Uses `subprocess.run()` with `cwd=project_root`

### Analysis state file

Written by `run_analysis.py` to `{runtime_root}/state/analysis-{project_id}.json` (respects `AI_DEV_FACTORY_RUNTIME_ROOT`, mirrors `deploy-state.json` pattern):
```json
{"state": "running|success|failed|idle", "started_at": "...", "finished_at": "...", "error": null, "branch": null, "pr_url": null}
```

### Control API — new schemas

**`services/control_api/models/schemas.py`** (extend)
- `AnalysisStatus`: `state`, `started_at`, `finished_at`, `error`, `branch`, `pr_url`

### Control API — new service

**`services/control_api/services/analysis_manager.py`** (new)
- `start_analysis(project_id, project_root, exec_cmd, supervisor_url) -> ActionResult` — HTTP POST to supervisor `/analysis/start`; if supervisor unreachable returns `error="supervisor_unreachable"`; if not configured returns `error="no_supervisor_url"`
- `get_analysis_status(project_id, supervisor_url) -> AnalysisStatus` — HTTP GET to supervisor `/analysis/{project_id}/status`
- `get_analysis_logs(project_id, supervisor_url, lines) -> list[str]` — HTTP GET to supervisor `/analysis/{project_id}/logs`

### Control API — new routes

**`services/control_api/routes/deployer.py`** (extend)
- `POST /projects/{project_id}/deployer/analyze` — calls `analysis_manager.start_analysis()`; returns `202` + `AnalysisStatus` on success; `409` if locked; `503` if supervisor unreachable
- `GET /projects/{project_id}/deployer/analysis/status` — proxies to supervisor; returns `AnalysisStatus`
- `GET /projects/{project_id}/deployer/analysis/logs` — proxies to supervisor; returns log lines

### Frontend — API client

**`apps/dashboard/src/api/deployer.js`** (extend)
- `analyzeProject(projectId)` — `POST /projects/{id}/deployer/analyze`
- `getAnalysisStatus(projectId)` — `GET /projects/{id}/deployer/analysis/status`
- `getAnalysisLogs(projectId, lines)` — `GET /projects/{id}/deployer/analysis/logs`

### Frontend — dashboard page

**`apps/dashboard/src/pages/DeployerPage.jsx`** (extend)
- "Analyze Project" button alongside existing Deploy/Scan/Restart buttons
- Analysis status panel: state badge, branch name, clickable PR link
- Scrollable analysis log panel (mirrors deploy log panel)
- Poll on 5 s interval while `state === "running"`, stop otherwise

### Tests

**`tests/test_analysis_prompt_builder.py`** (new)
- `test_prompt_contains_file_tree` — file tree present in output
- `test_prompt_contains_deploy_schema` — DeployProfile schema spec present
- `test_prompt_instructs_file_generation` — instructions for all three target files present
- `test_prompt_is_deterministic` — same inputs produce identical output

**`tests/test_analysis_manager.py`** (new)
- `test_start_analysis_delegates_to_supervisor` — verify HTTP POST to correct supervisor URL
- `test_start_analysis_supervisor_unreachable` — `httpx.ConnectError` → `error="supervisor_unreachable"`
- `test_start_analysis_returns_409_when_locked` — supervisor returns 409 → propagated
- `test_get_status_proxies_supervisor_response` — verify response mapping to `AnalysisStatus`

**`tests/test_analysis_git_service.py`** (new)
- `test_branch_name_format` — assert branch matches `ai-analysis/{project_id}-\d{8}-\d{6}`
- `test_pr_created_on_new_branch` — mock `gh pr list` empty → assert `gh pr create` called
- `test_pr_updated_on_existing_branch` — mock `gh pr list` returning open PR → assert `gh pr edit` called

## Excluded

- LLM execution inside Docker / control API
- Git branch creation or PR creation from Docker
- Automatic merge of the generated PR
- Automatic deployment execution after analysis
- Secrets detection or management
- Remote/cloud deployment orchestration
- Modification of the existing daemon ticket state machine
- Analysis of non-Python/non-Node stacks beyond what `project_scanner.py` already detects
- Supervisor authentication (localhost-trusted, consistent with existing supervisor design)

## Acceptance criteria

- `POST /projects/{id}/deployer/analyze` returns `202` and the supervisor log shows a new analysis process started; a concurrent call while `state=running` returns `409`
- `GET /projects/{id}/deployer/analysis/status` reflects `idle → running → success` (or `failed`) as the worker progresses
- On success: `.ai-dev-factory/deploy.yml` and `.ai-dev-factory/deployment.md` exist in the project root, are non-empty, and are UTF-8 valid
- Generated `deploy.yml` parses without error as `DeployProfile` using the existing Pydantic schema
- Generated files are committed to a branch named `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}`; `pr_url` is non-null in the returned `AnalysisStatus`
- Analysis worker process runs on the host (not inside Docker); LLM is invoked via the `exec_cmd` passed from the control API environment variable `AI_DEV_FACTORY_DAEMON_EXEC_CMD` (no provider hardcoded)
- Dashboard renders "Analyze Project" button; clicking it triggers the endpoint; state badge and PR link update without page reload
- `pytest tests/test_analysis_prompt_builder.py tests/test_analysis_manager.py tests/test_analysis_git_service.py` passes
- All pre-existing deployer, daemon, and supervisor tests continue to pass
