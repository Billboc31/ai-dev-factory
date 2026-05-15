101/101 tests pass. All five bugs are implemented. Here's a summary:

---

## Summary

**7 files modified:**

### Bug 1 — Timeline mapping (`artifact_reader.py`, `test_ticket_timeline.py`)
- `IMPLEMENTATION_REVIEW_NEEDED`: `human_gate=True→False`, status `"waiting_human"→"running"`, `_STEP_AGENTS[4]=None→"reviewer"`
- `TEST_COMPLETE`: `human_gate=False→True` (merge is human)
- Updated 2 test assertions accordingly

### Bug 2 — Ticket ID edge cases (`test_daemon_issue_polling.py`)
- Added 7 new tests: T034→T035, T099→T100, lexicographic trap (T1/T10/T100→T101), gaps, reserved set

### Bug 3 — Dirty tree 3-tuple (`run_daemon.py`, `test_daemon_checkpoint.py`)
- Added `_CODE_SCOPE_PREFIXES` constant (mirrors `COMMIT_SCOPE` from `run_ticket.py`)
- `_classify_dirty_files()` now returns `(workflow_artifacts, code_scope_files, unknown_files)`
- `_ensure_clean_working_tree()` treats code-scope files as auto-checkpointable, not blocking
- Updated all 8 affected tests + added 2 new tests

### Bug 4 — Checkpoint before PR (`run_daemon.py`, `test_daemon_pr_lifecycle.py`)
- Added `_checkpoint_and_push_before_pr()` — commits with `--include-code`, pushes if something committed, non-blocking
- `handle_test_complete()` calls it before `create_or_update_pr()`
- Added 4 new tests (including call-order verification)

### Bug 5 — `.gitignore`
- Added: `runs/*/state.json.tmp`, `runs/*/retry-state.json`, `runs/*/retry-state.json.tmp`, `runs/.issue-intake.json.tmp`
- Removed: duplicate `apps/dashboard/node_modules/` and redundant `.vite/` entry
