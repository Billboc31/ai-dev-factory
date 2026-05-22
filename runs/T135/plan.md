Now I have enough context to write the implementation plan.

## Objective

Introduce per-job isolated git worktrees and runtime environments for analysis and deploy workflows so that no analysis or deploy job touches the main runtime worktree, and so that the supervisor always operates on valid host filesystem paths rather than Docker-internal paths.

## Included

### Path mapping — Docker container paths → host paths

- **`services/supervisor/path_mapper.py`** *(new)* — `ContainerToHostMapper` class that reads two env vars (`CONTAINER_RUNTIME_ROOT`, `HOST_RUNTIME_ROOT`) and translates any container-side path to its host equivalent. Used by supervisor before spawning subprocesses.
- **`services/supervisor/main.py`** — import and apply `ContainerToHostMapper` to `project_root` received in `POST /analysis/start` and `POST /scripts/start` before passing paths to subprocesses. Expose current mapper config in `GET /supervisor/status`.
- **`deploy/.env.example`** — add `HOST_RUNTIME_ROOT` and `CONTAINER_RUNTIME_ROOT` vars with documentation.
- **`deploy/start_supervisor.sh`** — forward `HOST_RUNTIME_ROOT` env var to the supervisor process.

### Isolated analysis/deploy worktrees

- **`tools/agent_runner/run_analysis.py`** — at startup, create a dedicated git worktree at `RUNTIME_ROOT/worktrees/analysis-{job_id}/` (using existing `worktree_manager.create_ticket_worktree()` with a synthetic branch name `analysis/{job_id}`); run all scanning, LLM call, file writes and `git commit/push` inside that worktree; write the worktree path into the job state JSON; remove the worktree on exit (both success and failure paths).
- **`tools/agent_runner/run_scripts.py`** — same pattern: isolated worktree `scripts/{job_id}`, lifecycle identical to run_analysis.py.

### Isolated runtime roots per job

- **`services/control_api/services/runtime_resolver.py`** — add `analysis_job_dir(job_id)` and `scripts_job_dir(job_id)` helpers that return `RUNTIME_ROOT/jobs/analysis-{job_id}/` and `.../scripts-{job_id}/` respectively (subdirectories with their own `state.json`, `logs/`).
- **`tools/agent_runner/run_analysis.py`** and **`run_scripts.py`** — write state/log output to the job-specific directory rather than the shared `state/` directory. Keep a symlink or forwarding entry in `state/analysis-{project_id}.json` pointing to the latest job for backwards compatibility with existing API polling routes.

### Isolated compose project names, env files and ports (deploy validation)

- **`services/control_api/services/sandbox_manager.py`** — add `create_deploy_sandbox(job_id, project_root, worktree_path)` that reuses existing slot/port allocation and produces a compose env file inside the job worktree (`RUNTIME_ROOT/jobs/scripts-{job_id}/.env`), setting a unique `COMPOSE_PROJECT_NAME=ai_devfactory_deploy_{job_id}`. Wire this into the deploy validation step in `run_scripts.py`.

### Cleanup

- **`tools/agent_runner/run_analysis.py`** and **`run_scripts.py`** — unconditional `try/finally` cleanup: `remove_ticket_worktree(worktree_path, force=True)` after job exits.
- **`services/supervisor/main.py`** — on `POST /analysis/stop` and `POST /scripts/stop`, issue cleanup signal to running job (SIGTERM); log worktree cleanup confirmation.
- **`services/control_api/routes/deployer.py`** — add `POST /projects/{project_id}/deployer/analysis/cleanup` endpoint that triggers supervisor cleanup for a named job.

### Dashboard visibility

- **`services/control_api/routes/deployer.py`** — extend `GET /projects/{project_id}/deployer/analysis/status` response to include `worktree_path`, `job_runtime_dir`, `compose_project` (if applicable).
- **`apps/dashboard/src/api/deployer.ts`** *(or equivalent API client file)* — add `worktreePath`, `jobRuntimeDir` fields to the analysis status type.
- **`apps/dashboard/src/components/`** — add a small `WorktreeInfo` component displayed within the existing analysis status card, showing worktree path, isolation status (isolated / main), and compose project name when relevant.

### Tests

- **`tests/test_analysis_worktree_isolation.py`** *(new)* — verifies that `run_analysis.py` creates an isolated worktree, never touches the main project root, and cleans up the worktree on both success and failure paths. Uses `tmp_path` and mocked LLM subprocess.
- **`tests/test_host_path_mapping.py`** *(new)* — unit-tests `ContainerToHostMapper`: correct translation, identity when env vars not set, path-within-subdir preservation, no mutation of unrelated paths.
- **`tests/test_scripts_worktree_isolation.py`** *(new)* — same pattern as analysis test but for `run_scripts.py` and deploy sandbox creation.

## Excluded

- Deploy/test/fix retry loop and tester agent (separate ticket).
- Production and remote/cloud deployment.
- Distributed multi-daemon coordination.
- Migrating existing historical state files to the new job-scoped layout.
- Rollback / revert of deployed sandboxes.
- Audit logging, rate limiting, backpressure.

## Acceptance criteria

- Running `run_analysis.py` creates a new directory under `RUNTIME_ROOT/worktrees/analysis-*/` and writes no files directly into `project_root` (verified by test mocking `worktree_manager` and asserting call args).
- `ContainerToHostMapper.map("/runtime/ai-dev-factory/runs/T100")` returns `"/Users/pierre/runtime/ai-dev-factory/runs/T100"` when `CONTAINER_RUNTIME_ROOT=/runtime/ai-dev-factory` and `HOST_RUNTIME_ROOT=/Users/pierre/runtime/ai-dev-factory`.
- After a simulated analysis job exits (success or error), `RUNTIME_ROOT/worktrees/analysis-{job_id}/` no longer exists.
- Two concurrent analysis jobs allocate different ports and different `COMPOSE_PROJECT_NAME` values; stopping one does not affect the other.
- `GET /projects/{project_id}/deployer/analysis/status` response includes a non-null `worktree_path` field while a job is running.
- The dashboard analysis status card displays the worktree path field.
- All existing tests (`pytest tests/`) continue to pass without modification.
