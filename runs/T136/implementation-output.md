All tasks complete. Here is a summary of the changes made:

---

## Changes summary

### Files modified

**`services/control_api/models/sandbox.py`**
- Added `worktree_path: str | None = None`, `job_type: str | None = None`, `completed_at: str | None = None` to `SandboxState`.

**`services/control_api/services/sandbox_manager.py`**
- `create_with_worktree(ticket_id, project_root, branch=None, job_type="deploy")` — calls `create()` then runs `git worktree add --detach` (or with a specific branch); stores path in state. Rolls back sandbox on git failure.
- `mark_completed(sandbox_id)` — sets `completed_at` and transitions status to `stopped`.
- `cleanup_completed(max_age_minutes=30)` — destroys completed sandboxes past the age threshold.
- `destroy()` — now calls `git worktree remove --force <worktree_path>` before deleting the sandbox directory when a worktree is present.

**`services/control_api/services/deployer_runner.py`**
- `_do_deploy()` accepts an optional `sandbox: SandboxState | None = None`; when set it uses the sandbox dir for state/logs, the worktree as `cwd`, and injects `-p compose_project --env-file env_file` into docker compose commands.
- New `run_deploy_sandboxed(project_id, project_root, sandbox_manager, branch=None, job_type="deploy")` — creates a sandbox, runs deploy inside it, then marks it completed and triggers `cleanup_completed()`.

**`services/supervisor/main.py`**
- Imports `SandboxManager` at startup (gracefully disabled on `ImportError`).
- `analysis_start` and `scripts_start` create a worktree sandbox before spawning, inject `SANDBOX_ID` / `SANDBOX_WORKTREE` env vars, and launch a daemon thread to destroy the sandbox after the subprocess exits.

**`tools/agent_runner/run_analysis.py`** and **`tools/agent_runner/run_scripts.py`**
- Reads `SANDBOX_WORKTREE` env var; uses it as `effective_root` for all file writes, git operations, and LLM invocation. Falls back to the original `project_root` when not set.

**`apps/dashboard/src/components/SandboxPanel.jsx`**
- `SandboxRow` shows a `job_type` badge when present and a `worktree_path` line in the detail row.

### Files created

**`tests/test_sandbox_isolation.py`** — 8 tests covering concurrent port/compose-name uniqueness, env-file isolation, and `cleanup_completed` behaviour.

**`tests/test_sandbox_worktree.py`** — 12 tests covering `create_with_worktree`, `mark_completed`, and worktree removal in `destroy`.

**Result: 20/20 new tests pass; 58/59 existing tests pass (the 1 failure is pre-existing, confirmed unrelated to this change).**
