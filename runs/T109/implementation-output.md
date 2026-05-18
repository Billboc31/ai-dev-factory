All 395 tests pass. Here's a summary of what was implemented:

---

**Files created:**
- `tools/agent_runner/runtime_checkpoint.py` — the new atomic checkpoint primitive with `resolve_ticket_cwd()`, `collect_runtime_artifacts()`, `verify_clean_tree()`, `checkpoint_transition()`, plus `CheckpointError` / `DirtyTreeError` exceptions
- `tests/test_runtime_checkpoint.py` — 7 test cases (success, push failure, dirty tree remaining, cwd resolution ×2, git add -f, concurrent isolation)

**Files modified:**
- `tools/agent_runner/run_ticket.py` — `run_command()` now accepts `cwd=`; `push_branch()` now blocks with `DIRTY_RUNTIME_CHECKPOINT` instead of warning on dirty tree
- `tools/agent_runner/run_daemon.py` — imports `checkpoint_transition`/`CheckpointError`/`DirtyTreeError` via importlib; `_commit_after_intake()` and `_checkpoint_and_push_before_pr()` now delegate to `checkpoint_transition()`, removing the double-subprocess pattern
- `tools/agent_runner/run_issue_intake.py` — `commit_bootstrap()` now delegates to `checkpoint_transition()` instead of 3 ad-hoc git calls; imports via `sys.path` for consistent class identity
- `tests/test_commit_push.py` — updated `test_push_blocked_on_dirty_working_tree` to assert the new blocking behavior
- `tests/test_daemon_pr_lifecycle.py` — replaced 3 subprocess-inspection tests with `checkpoint_transition`-mock-based tests
- `tests/test_intake_checkpoint.py` — rewrote all `commit_bootstrap` tests to target the new `_checkpoint_transition` delegate
