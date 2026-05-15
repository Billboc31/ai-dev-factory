All 217 tests pass. Here's a summary of what was implemented:

**Files modified:**

- `tools/agent_runner/run_issue_intake.py` — `write_state_json()` now accepts `issue_number` and writes it to `state.json` so the daemon can link PR → issue.

- `tools/agent_runner/run_ticket.py` — `auto_run()` gains an `include_code` parameter that's forwarded to `commit_ticket()`; new `--auto-include-code` CLI flag wires it up.

- `tools/agent_runner/run_daemon.py` — the main additions:
  - `_load_state_json()` / `_save_state_json()` — atomic read/write of state.json
  - `create_or_update_pr()` — finds or creates a PR via `gh pr list/create/edit`, stores `pr_number` in state
  - `check_and_close_issue()` — detects merged PR via `gh pr view`, closes issue and removes `ai-ready` label
  - `handle_test_complete()` — orchestrator called from `run_once()` for `TEST_COMPLETE` state
  - `launch_ticket()` — now accepts `auto_commit`, `auto_push`, `auto_include_code` and passes them to `run_ticket.py`
  - `run_once()` — handles `TEST_COMPLETE` separately (PR lifecycle) before the human-gate fallthrough; new flags forwarded to `launch_ticket()`
  - CLI: three new daemon flags `--auto-commit`, `--auto-push`, `--auto-include-code`

- `tests/test_run_daemon.py` — fixed `test_run_once_calls_launch_for_auto_runnable_state` to match the new `launch_ticket` kwargs.

**New test files:**
- `tests/test_daemon_checkpoint.py` — 5 tests covering the auto-commit/push/include-code flags
- `tests/test_daemon_pr_lifecycle.py` — 10 tests covering `_load/save_state_json`, `create_or_update_pr`, `check_and_close_issue`, `handle_test_complete`
