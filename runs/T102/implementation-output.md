The fix is applied correctly. `_sync_main_before_intake()` now runs only when there's an actual candidate to intake and capacity is available — not on every polling cycle.

**Change made** (`tools/agent_runner/run_daemon.py`): moved `_sync_main_before_intake()` from the top of `poll_github_issues` (where it ran unconditionally every 30s) to just before `call_issue_intake`, after all early-exit checks (no issues, all ingested, capacity full). Git sync now only happens when the daemon is about to actually intake an issue.
