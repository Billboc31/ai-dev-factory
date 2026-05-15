All 220 tests pass (217 original + 3 new). Here's a summary of the changes:

---

**Files modified:**

- `tools/agent_runner/run_daemon.py`:
  - `_pr_body()` — P2 fix: `PLAN_APPROVED` and `IMPLEMENTATION_APPROVED` are now pre-checked (`[x]`) since both gates are validated before `TEST_COMPLETE`; `MEMORY_APPROVED` stays unchecked
  - `check_and_close_issue()` — P1 fix: reads `issue_closed` from `state.json` at the start and returns immediately if set; after closing the issue and removing the label, writes `issue_closed: True` back to `state.json`
  - `create_or_update_pr()` — P1 improvement: skips `gh pr edit` entirely if `pr_number` is already set and `pr_synced: True` is in state; writes `pr_synced: True` after a successful create or edit

- `tests/test_daemon_pr_lifecycle.py`:
  - Added `_pr_body` to imports
  - `test_create_or_update_pr_updates_existing_pr` — added assertion that `pr_synced: True` is saved
  - `test_create_or_update_pr_skips_when_pr_synced` — new: verifies no gh call when already synced
  - `test_check_and_close_issue_closes_merged_pr` — added assertion that `issue_closed: True` is saved
  - `test_check_and_close_issue_skips_when_already_closed` — new: verifies no gh call when already closed
  - `test_pr_body_has_approved_gates_checked` — new: verifies the two gates are pre-checked and `Closes #N` is present
