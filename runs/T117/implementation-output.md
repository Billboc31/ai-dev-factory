All 6 fixes are in place. Here's a summary:

---

## Changes made

### Files modified

**`services/control_api/services/daemon_manager.py`**
- `start()`: added `--auto-commit`, `--auto-push`, `--worktrees-dir <project_root>/worktrees` to the daemon Popen command — enables automatic checkpoint/push after each workflow step when launched from the dashboard.

**`tools/agent_runner/worktree_manager.py`**
- `ensure_intake_worktree()`: when the `_intake` worktree already exists, forces `git checkout -f main` before returning — prevents lingering ticket branches from blocking intake.

**`tools/agent_runner/run_issue_intake.py`**
- `_cleanup_ignorable_runtime_paths()`: added `git ls-files --error-unmatch` check before `git checkout HEAD` — skips untracked files (e.g. a fresh `runtime.log`) that would otherwise cause a non-zero exit and abort intake.

**`tools/agent_runner/run_daemon.py`**
- `launch_ticket()`: when `worktrees_dir` is set but the worktree is absent, attempts on-demand creation via `create_ticket_worktree()`; if that fails, skips the ticket with a clear log message — no silent legacy fallback.
- `_sync_ticket_branch()`: changed `--ff-only` to `--rebase` — handles non-fast-forward remote commits (from human plan approvals) without aborting the sync.

### File created

**`docs/daemon-lifecycle.md`** — documents the complete daemon lifecycle: startup flags, per-cycle loop, intake flow, worktree execution, checkpoint mechanics, the single human gate (`PLAN_REVIEW_NEEDED`), and failure/retry policies.
