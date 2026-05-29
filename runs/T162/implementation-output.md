Implementation complete. Here's a summary of all changes made:

---

## Changes — T162

### `tools/agent_runner/run_daemon.py`

**1. `handle_test_complete()` — primary bug fix (line 879–888)**

When `auto_merge_pr()` returns `False`, the function now immediately calls `detect_pr_conflict()`. If the PR is conflicting, it transitions the ticket to `CONFLICT_RESOLUTION_NEEDED` in `state.json` within the same daemon handler call. Previously this never happened because `TEST_COMPLETE` is in `_CONFLICT_SKIP_STATES` and the generic conflict-detection loop was therefore never reached.

**2. `create_or_update_pr()` — branch rename fallback (line 654–672)**

Added a second PR lookup when the branch-name lookup returns nothing. Lists all open PRs and filters locally for any whose `headRefName` starts with `ticket/{ticket_id}-`. This recovers `pr_number` into `state.json` even when the branch was renamed after PR creation, fixing the "branch rename mismatch" scenario.

**3. `run_once()` — observability log (line 1730)**

Added an explicit log line `Ticket {ticket_id} already in CONFLICT_RESOLUTION_NEEDED, skipping re-detection` when the ticket re-enters the HUMAN_GATE_STATES handler in `CONFLICT_RESOLUTION_NEEDED` state.

### `tests/test_daemon_pr_lifecycle.py`

- Updated 3 existing `create_or_update_pr` tests to supply a third mock for the new fallback subprocess call.
- Added 4 new tests covering: conflict detection invocation on failed merge, no `check_and_close_issue` when conflict detected, no detection without `pr_number`, and the branch-prefix fallback.

**All 35 PR lifecycle tests pass. Pre-existing failures in `test_daemon_checkpoint.py`/`test_run_daemon.py` are environment-related (singleton lock) and unrelated to this change.**
