Clean. Here's what was fixed:

**Blocking bug — `run_issue_intake.py:commit_bootstrap`**
`state.json` is now staged alongside `ticket.md` in the bootstrap commit. This ensures the worktree created by `git worktree add` has `state.json` present, so `run_ticket.py --auto` no longer fails with "state not found" in a fresh ticket.

**Significant issue (same root cause)**
Before this fix, `state.json` was left as an untracked file after `git checkout main` (only `ticket.md` was committed, so only it was removed by the branch switch). That orphaned file caused the main repo scan to find `state=INIT` and re-queue the ticket indefinitely after a worktree deletion. Committing `state.json` means `git checkout main` now removes it cleanly.

**Minor — `run_daemon.py:_cleanup_stale_workers`**
New function called at daemon startup that removes dead-PID entries from `workers.json`, keeping the board accurate after a crash.

**Minor — `run_daemon.py:run_once` max_workers enforcement**
`run_once` now accepts `max_workers` and reads the live `workers.json` count before launching each auto-runnable ticket, skipping launches when the limit is reached. The `--max-workers` flag is now actually enforced.
