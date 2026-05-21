Now I have a clear picture of the codebase. Here is the implementation plan.

---

## Objective

Add an AI-assisted "Analyze Project" workflow to the deployer: scan the repository deterministically, build a structured prompt, invoke the environment-configured LLM runtime, generate reviewable operational files (deploy.yml, deployment.md, optional runtime-notes.md), commit them to a dedicated branch, and open a PR — with full progress visibility in the dashboard.

## Included

### Backend — new schemas

**`services/control_api/models/schemas.py`**
- `AnalysisStatus` schema: `state` (idle/running/success/failed), `started_at`, `finished_at`, `error`, `branch`, `pr_url`
- `AnalysisResult` schema: list of generated file paths, inferred tools, services, env vars

### Backend — new services

**`services/control_api/services/analysis_prompt_builder.py`** (new)
- `build_analysis_prompt(project_root, scan_result) -> str`
- Assembles: repository file tree + existing `project_scanner.py` scan output + `DeployProfile` JSON schema spec + explicit generation instructions for `deploy.yml`, `deployment.md`, and optionally `runtime-notes.md`
- No LLM dependency; pure string construction (enables isolated unit testing)

**`services/control_api/services/project_analysis_service.py`** (new)
- `start_analysis(project_id, project_root) -> None` — acquires per-project `threading.Lock` (mirrors `deployer_runner.py`), spawns background thread, raises `409` if already running
- `_run_analysis(project_root) -> None` — orchestrates: scan → prompt build → LLM invocation → parse LLM output → write generated files → git branch/commit/push → gh pr create/update
- `get_analysis_status(project_id) -> AnalysisStatus` — reads `.ai-dev-factory/analysis-state.json`
- `get_analysis_logs(project_id, lines) -> list[str]` — tails `.ai-dev-factory/analysis.log`
- LLM exec_cmd read from `EXEC_CMD` env var (same pattern as daemon's `--exec-cmd` flag; no hardcoded provider)
- State written atomically to `.ai-dev-factory/analysis-state.json` (write-to-tmp + rename, matching existing state file conventions)
- Logs written to `.ai-dev-factory/analysis.log`

**`services/control_api/services/analysis_git_service.py`** (new)
- `commit_generated_files(project_root, branch_name, file_paths) -> None` — `git checkout -b {branch}`, `git add`, `git commit`
- `push_branch(project_root, branch_name) -> None` — `git push -u origin {branch}`
- `create_or_update_pr(project_root, branch_name, project_id) -> str` — `gh pr create` or `gh pr edit` if branch already has an open PR; returns PR URL

Branch naming convention: `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}`

### Backend — new routes

**`services/control_api/routes/deployer.py`** (extend existing)
- `POST /projects/{project_id}/deployer/analyze` — triggers analysis, returns `202 Accepted` + `AnalysisStatus`
- `GET /projects/{project_id}/deployer/analysis/status` — returns `AnalysisStatus`
- `GET /projects/{project_id}/deployer/analysis/logs?lines=100` — returns log tail

### Frontend — API client

**`apps/dashboard/src/api/deployer.js`** (extend existing)
- `analyzeProject(projectId)` — `POST /projects/{id}/deployer/analyze`
- `getAnalysisStatus(projectId)` — `GET /projects/{id}/deployer/analysis/status`
- `getAnalysisLogs(projectId, lines)` — `GET /projects/{id}/deployer/analysis/logs`

### Frontend — dashboard page

**`apps/dashboard/src/pages/DeployerPage.jsx`** (extend existing)
- "Analyze Project" action button, styled and positioned alongside existing "Deploy" / "Scan" / "Restart" buttons
- Analysis status panel: state badge, branch name, clickable PR link
- Scrollable analysis log tail (mirrors existing deploy log panel)
- Polling on 5 s interval while state is `running`, idle otherwise

### Tests

**`tests/test_analysis_prompt_builder.py`** (new)
- `test_prompt_contains_file_tree` — scan result tree present in output
- `test_prompt_contains_deploy_schema` — deploy.yml schema spec present
- `test_prompt_instructs_file_generation` — generation instructions for all three target files present
- `test_prompt_is_deterministic` — same inputs produce identical output

**`tests/test_project_analysis_service.py`** (new)
- `test_analysis_transitions_to_running` — state file shows `running` immediately after trigger
- `test_analysis_locking_rejects_concurrent_run` — second trigger raises `409`
- `test_analysis_writes_generated_files` — mock LLM output → verify `deploy.yml` + `deployment.md` written to project root
- `test_generated_deploy_yml_validates_against_schema` — output parseable as `DeployProfile`
- `test_analysis_failure_writes_failed_state` — mock LLM error → assert `failed` state + error message

**`tests/test_analysis_git_workflow.py`** (new)
- `test_commit_creates_correct_branch_name` — assert `git checkout -b ai-analysis/…` called with expected branch
- `test_pr_created_on_new_branch` — mock `gh`; assert `gh pr create` called, URL stored in state
- `test_pr_updated_on_existing_branch` — mock `gh pr list` returning open PR; assert `gh pr edit` called instead

## Excluded

- Automatic deployment execution after analysis completes
- Automatic install of missing runtime dependencies detected by the analysis
- Automatic merge of the generated PR
- Secrets detection or management
- Remote or cloud deployment orchestration
- Modification of the existing daemon ticket state machine or step types
- Analysis of non-Python/non-Node stacks beyond what `project_scanner.py` already detects

## Acceptance criteria

- `POST /projects/{id}/deployer/analyze` returns `202` and sets analysis state to `running`; a concurrent call returns `409`
- `GET /projects/{id}/deployer/analysis/status` reflects correct state transitions: `idle → running → success` (or `failed`)
- On success: `.ai-dev-factory/deploy.yml` and `.ai-dev-factory/deployment.md` exist in the project root; they are non-empty and UTF-8 valid
- Generated `deploy.yml` parses without error as `DeployProfile` using the existing Pydantic schema in `schemas.py`
- Generated files are committed to a branch named `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}`
- A PR is created (or updated) targeting the project default branch; `pr_url` is non-null in `AnalysisStatus`
- Dashboard renders "Analyze Project" button; clicking it triggers the endpoint; state and PR link update without page reload
- LLM runtime is resolved exclusively from the `EXEC_CMD` environment variable; no provider name or model is hardcoded in source
- `pytest tests/test_analysis_prompt_builder.py tests/test_project_analysis_service.py tests/test_analysis_git_workflow.py` passes
- All pre-existing deployer and daemon tests continue to pass (`pytest tests/` green)
