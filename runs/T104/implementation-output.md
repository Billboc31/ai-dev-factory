Implementation is committed. Here's a summary of what was built:

---

## T104 — Implementation Summary

### New file
- **`tools/agent_runner/worktree_manager.py`** — 3 helpers: `create_ticket_worktree`, `remove_ticket_worktree`, `get_ticket_worktree_path`. Uses `git worktree add/remove`. Refuses to auto-remove a worktree with uncommitted changes.

### Modified files (8)

**`tools/agent_runner/run_daemon.py`** (major):
- `DEFAULT_WORKTREES_DIR` = `~/ai-dev-factory-worktrees` (sibling of repo)
- `--worktrees-dir` and `--max-workers` CLI flags
- `_load/save/register/unregister_worker` for `runs/workers.json` registry
- `scan_tickets()` now scans worktrees first, falls back to main repo `runs/`
- `_get_run_dir()` resolves the correct run_dir (worktree takes priority)
- `launch_ticket()` split into two paths: worktree-based (CWD=worktree, no branch check) and legacy (existing behavior)
- `_sync_ticket_branch()` accepts optional `cwd=` for worktree context
- `_checkpoint_and_push_before_pr()` accepts optional `cwd=`
- `_commit_after_intake()` now commits `.issue-intake.json` directly to current branch (no longer via `run_ticket.py` which would fail after branch switch)
- `poll_github_issues()` creates the worktree immediately after intake
- `run_once()` threads `worktrees_dir` and `worktree_cwd` through all calls

**`tools/agent_runner/run_issue_intake.py`**: Records original branch, returns to it after bootstrap commit.

**`tools/agent_runner/run_ticket.py`**: `--repo-root` flag (forward-compatible); `checkout_branch()` is a no-op if already on the correct branch.

**`services/control_api/models/schemas.py`**: `BoardItem` gains `worker_pid` and `worker_cwd`.

**`services/control_api/services/board_service.py`**: Loads `workers.json`, prefers worktree state for active workers, marks tickets as Running if in workers registry, attaches `worker_pid`/`worker_cwd` to items.

**`apps/dashboard/src/pages/BoardPage.jsx`**: Running cards show `pid:XXXXX · T104` line.

**`apps/dashboard/src/pages/DaemonPage.jsx`**: New Workers panel listing active workers with branch, cwd, and pid.
