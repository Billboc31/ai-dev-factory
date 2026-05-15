Clean. Here's a summary of everything implemented:

---

## Changes made

### `tools/agent_runner/run_daemon.py`

**Bug 1 — `_checkpoint_and_push_before_pr` (line 553–566)**
Removed the `else: skip push` branch. The push now runs unconditionally after a `rc=0` or `rc=1` commit, so any unpushed prior commits are always flushed before PR creation.

**Bug 2 — branch guard in `launch_ticket` (lines 670–678)**
Added `_get_current_branch()` helper and a guard inside `launch_ticket()` (after `_acquire_lock`, inside the `try` block): if `current_branch != expected_branch`, the ticket is skipped with an explicit log. No automatic checkout.

**Bug 3 — `_CODE_SCOPE_PREFIXES` vs `COMMIT_SCOPE`**
Verified visually: the only difference is `runs/`, which is intentional (the daemon classifies `runs/` as `workflow_artifacts` separately). No code change needed.

**Bug 4 — git untrack `apps/dashboard/node_modules/`**
Ran `git rm -r --cached apps/dashboard/node_modules/`. The `.gitignore` entry was already correct; this removes the files from the index so they're no longer tracked.

**New — checkpoint before `PLAN_REVIEW_NEEDED` (lines 938–944)**
In `run_once()`, when `state == "PLAN_REVIEW_NEEDED"`, calls `_checkpoint_and_push_before_pr()` before logging the human-gate skip, so planner artifacts are visible on GitHub.

**New — `_sync_ticket_branch()` called from `launch_ticket` (lines 618–636, 677–679)**
New function does `git pull --ff-only origin <branch>`. Returns `True` if already up-to-date or remote branch doesn't exist yet; returns `False` (skip with log) on divergence. Called after the branch guard and before `_ensure_clean_working_tree`.
