## Objective

Extend the T133 sandbox infrastructure to give every deploy validation job its own isolated git worktree, Docker Compose project, port range, and env file, with automatic lifecycle management and dashboard visibility, so concurrent deploy jobs never interfere with each other or with the main runtime.

## Included

**`services/control_api/models/sandbox.py`**
- Add `worktree_path: str | None`, `job_type: str | None`, `completed_at: str | None` to `SandboxState`

**`services/control_api/services/sandbox_manager.py`**
- `create_with_worktree(ticket_id, project_root, branch, job_type)` — calls `create()` then runs `git worktree add <sandbox_dir>/worktree <branch>`; stores path in state
- Update `destroy()` to run `git worktree remove --force <worktree_path>` before deleting the sandbox directory
- `mark_completed(sandbox_id)` — sets `completed_at` and transitions status to `stopped`
- `cleanup_completed(max_age_minutes=30)` — destroys sandboxes past the age threshold

**`services/control_api/services/deployer_runner.py`**
- At job start: `sandbox_manager.create_with_worktree(...)` — use `sandbox.worktree_path` as `cwd`, `sandbox.compose_project` as `-p`, `sandbox.env_file` as `--env-file`
- Write state/logs to `<sandbox_dir>/state.json` and `<sandbox_dir>/logs/deploy.log`
- On completion/failure: `mark_completed()` then `cleanup_completed()`

**`services/supervisor/main.py`**
- Before spawning scripts/analysis subprocess: `create_with_worktree()`, inject `SANDBOX_ID` and `SANDBOX_WORKTREE` env vars
- After subprocess exits: `sandbox_manager.destroy(sandbox_id)`

**`tools/agent_runner/run_scripts.py`** and **`run_analysis.py`**
- Use `SANDBOX_WORKTREE` as working directory for file writes and git operations when the env var is set; fall back to existing behaviour otherwise

**`apps/dashboard/src/components/SandboxPanel.jsx`**
- Add `Job Type` column from `sandbox.job_type`; show `worktree_path` in detail row

**`tests/test_sandbox_isolation.py`** (new) — concurrent sandbox creation produces unique ports/compose names; `cleanup_completed()` destroys completed sandboxes

**`tests/test_sandbox_worktree.py`** (new) — `create_with_worktree()` sets `worktree_path`; `destroy()` removes the worktree; `mark_completed()` sets `completed_at`

## Excluded

- Deploy/test/fix retry loop (separate ticket)
- Tester agent, production/remote/cloud deployment, Kubernetes
- Docker Compose isolation for scripts/analysis jobs (filesystem worktree isolation is sufficient for them)
- Any changes to analysis/runtime workflows beyond accepting the `SANDBOX_WORKTREE` env var

## Acceptance criteria

- A deploy validation job creates a sandbox with unique compose project, port range, env file, and git worktree; never touches the main runtime worktree
- Two concurrent deploy jobs for the same project use different compose projects and port ranges
- `destroy()` removes both the git worktree and the sandbox directory
- `cleanup_completed(max_age_minutes=0)` destroys all sandboxes with a `completed_at` value
- `run_scripts.py` / `run_analysis.py` use `SANDBOX_WORKTREE` when set, fall back gracefully when absent
- Dashboard `SandboxPanel` shows a `Job Type` column with correct values
- `pytest tests/test_sandbox_isolation.py tests/test_sandbox_worktree.py` passes
- All existing sandbox manager, supervisor, and runner tests continue to pass

The plan has been saved to `runs/T136/plan.md`.
