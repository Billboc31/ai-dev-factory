Pre-existing failure — not caused by my changes. 357/358 tests pass, the one failure was already present before this fix.

**Summary of changes:**

- `tools/agent_runner/run_daemon.py`: `_checkpoint_and_push_before_pr` now returns `bool` (`False` on commit failure or push failure, `True` otherwise). `handle_test_complete` gates `create_or_update_pr` and `check_and_close_issue` on that return value — if push failed, logs the skip and returns early.

- `tests/test_daemon_pr_lifecycle.py`: Fixed `test_handle_test_complete_checkpoints_before_pr` (its lambda returned `None`, now returns `True`). Added `test_handle_test_complete_skips_pr_when_push_fails` to cover the push-failed → PR not created path.

21/21 PR lifecycle tests pass; the single pre-existing failure in `test_commit_push.py` is unrelated to this ticket.
