All 388 tests pass. Here is a summary of what was implemented:

---

## Changes summary

### New files
- **`services/control_api/services/runtime_resolver.py`** — shared resolver with `resolve_ticket_run_dir()` and `resolve_ticket_cwd()`, priority: active workers.json → worktrees_dir scan → legacy fallback.
- **`tests/test_runtime_resolver.py`** — 10 tests covering all resolver resolution cases.
- **`tests/test_ihm_worktree_cwd.py`** — 9 tests reproducing the "current branch main does not match state branch" bug and verifying all action functions use the correct worktree cwd.

### Modified files
| File | Change |
|---|---|
| `services/control_api/services/subprocess_runner.py` | All action functions now call `_resolve_action_cwd()` — returns the worktree cwd if present, or refuses with an actionable message if on `main` but state expects a ticket branch |
| `services/control_api/main.py` | Added `worktrees_dir` to `create_app()` and `app.state`; CLI gets `--worktrees-dir` flag |
| `services/control_api/routes/tickets.py` | All read and action routes pass `worktrees_dir` from app state |
| `services/control_api/services/artifact_reader.py` | All single-ticket reads use `resolve_ticket_run_dir()`; `list_tickets` also scans worktrees_dir |
| `services/control_api/services/board_service.py` | `get_board()` accepts `worktrees_dir` and scans it for non-running worktree tickets |
| `services/control_api/routes/daemon.py` | Board route passes `worktrees_dir` from app state |
| `tools/agent_runner/run_daemon.py` | Added `auto_merge_pr()` with all safety guards (OPEN, not CONFLICTING, gh merge --squash --delete-branch); updated `handle_test_complete()` to call it |
| `tests/test_daemon_pr_lifecycle.py` | Fixed `handle_test_complete` mock assertions; added 9 `auto_merge_pr` tests; fixed incorrect push behavior test |
| Several other test files | Fixed pre-existing assertions broken by T104's `worktrees_dir` parameter additions |
