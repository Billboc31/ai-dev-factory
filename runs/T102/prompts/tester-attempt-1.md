# T102 — Test Report

**Date**: 2026-05-15
**Branch**: ticket/T102-t102-daemon-intake-synchronization-queue-policy-an
**State at test time**: IMPLEMENTATION_APPROVED

---

## Acceptance Criteria

### AC1 — Daemon synchronizes `main` before intake
**Status: PASS (functional) / BLOCKING (test isolation)**

Implementation in `tools/agent_runner/run_daemon.py:671-709` (`_sync_main_before_intake()`):
- Checks `git status --porcelain` for unknown dirty files (aborts if found)
- Runs `git checkout main` → logs `checkout main completed`
- Runs `git pull origin main` → logs `pull origin main completed`
- Returns `False` on any failure, logs reason explicitly
- Called at line 849, after capacity check (correct: only when intake will actually happen)

**Test isolation issue (BLOCKING)**: `_sync_main_before_intake` is not mocked in any `poll_github_issues` test. During the test run, it executes real `git checkout main` and `git pull origin main` against the live repository. Confirmed: after running the test suite, `git branch --show-current` returned `main` instead of the ticket branch. This must be fixed before merge.

---

### AC2 — Daemon does not launch all `ai-ready` issues simultaneously
**Status: PASS**

`poll_github_issues` (line 839) selects `candidates[0]` only. Remaining candidates are logged as queued. The max_active_tickets guard at line 834 prevents intake entirely when at capacity.

---

### AC3 — Capacity limit exists (max_active_tickets=1)
**Status: PASS**

- `_count_active_tickets(runs_dir)` (line 712): counts non-archived, non-closed tickets with a `state` field
- CLI argument `--max-active-tickets` with `default=1` (line 914)
- Guard at line 834: `if active >= max_active_tickets: log all candidates as skipped-for-capacity; return`

Verified live: T102 itself counts as the active ticket (state=IMPLEMENTATION_APPROVED, not archived). A second `ai-ready` issue would be skipped.

---

### AC4 — Non-launched issues visible as queued/skipped-for-capacity
**Status: PASS**

Logs produced at poll time:
```
issue #N ("title") skipped-for-capacity active=1 max=1
issue #N ("title") queued — capacity reserved for issue #M
```

---

### AC5 — Board API exposes main columns
**Status: PASS**

`GET /daemon/board` on port 8080 returns valid JSON. Verified live:
```
backlog         (Backlog):       0 items
queued          (Queued):        0 items
running         (Running):       1 item  → T102 (IMPLEMENTATION_APPROVED)
waiting_human   (Waiting human): 0 items
blocked         (Blocked):       0 items
pr_ready        (PR ready):      0 items
done            (Done):         24 items → T010–T101 (daemon_archived)
```

Seven columns match the spec exactly. Projection from `runs/*/state.json`, `daemon.lock`, `retry-state.json`, and `gh issue list`. No new database.

---

### AC6 — Dashboard displays board view
**Status: PASS**

- `apps/dashboard/src/pages/BoardPage.jsx`: 7 color-coded Kanban columns, `BoardCard` with ticket link
- Route `/board` in `App.jsx:31`, nav link "Board" in `App.jsx:16`
- Auto-polling every 10 seconds via `usePolling(fetchBoard, 10000)`
- `getBoardData()` in `api/daemon.js:10` calls `/api/daemon/board` through Vite proxy → `http://localhost:8080/daemon/board`

---

### AC7 — Logs explain why an issue is launched or not
**Status: PASS**

Complete decision log coverage:
```
no issues found with label='ai-ready'
issue #N already ingested as TXXX — skipping
found N candidate issue(s) active_tickets=A max_active_tickets=M
issue #N ("title") skipped-for-capacity active=A max=M
issue #N ("title") queued — capacity reserved for issue #M
issue intake aborted — git sync failed
sync-main: unknown dirty files detected — aborting intake: [...]
checkout main completed / pull origin main completed
issue #N ingested as TXXX
issue intake failed for issue #N — will retry next cycle
```

---

### AC8 — No `git add .`
**Status: PASS**

Grep across `tools/agent_runner/`, `services/`, `apps/`: no `git add .` found. `run_ticket.py` explicitly documents "never git add .".

---

## Regressions

### Test suite failures

#### FAIL — `test_poll_github_issues_multiple_issues_sequential_ids`
**Severity: blocking — T102 regression**

Test at `tests/test_daemon_issue_polling.py:343` asserts that both issue #1 and issue #2 are ingested in one poll cycle (lines 356-357: `index["1"] == "T001"`, `index["2"] == "T002"`). With T102's max_active_tickets=1 policy, only issue #1 is ingested; issue #2 is queued. `index["2"]` raises `KeyError`. The test was not updated to reflect the intentional behavior change.

**Fix required**: Update test to assert only issue #1 is ingested and issue #2 is logged as queued.

#### FAIL — `test_main_poll_issues_flag_calls_poll_before_run_once`
**Severity: blocking — T102 regression**

Test at `tests/test_daemon_issue_polling.py:400` asserts:
```python
mock_poll.assert_called_once_with(runs, "ai-ready", None)
```
Actual call:
```
poll_github_issues(runs, 'ai-ready', None, max_active_tickets=1)
```
The assertion was not updated after T102 added the `max_active_tickets` keyword argument to the `main()` → `poll_github_issues()` call.

**Fix required**: Update assertion to include `max_active_tickets=1`.

#### FAIL — test isolation: real git operations during test suite
**Severity: blocking**

All `poll_github_issues` tests that exercise the intake path (i.e., have a candidate issue) call `_sync_main_before_intake()` against the live repository. This runs `git checkout main` and `git pull origin main` on the developer's working tree. Confirmed: after the test suite, the repository was left on `main`.

Affected tests (at minimum):
- `test_poll_github_issues_ingests_new_issue`
- `test_poll_github_issues_does_not_update_index_on_intake_failure`
- `test_poll_github_issues_logs_retry_on_intake_failure`
- `test_poll_github_issues_assigns_correct_next_ticket_id`
- `test_poll_github_issues_multiple_issues_sequential_ids`
- `test_poll_github_issues_calls_commit_after_intake_on_success`
- `test_poll_github_issues_does_not_call_commit_after_intake_on_failure`

**Fix required**: All `poll_github_issues` tests that reach the intake path must add:
```python
with patch("run_daemon._sync_main_before_intake", return_value=True):
```

`_sync_main_before_intake` itself needs dedicated unit tests.

#### PRE-EXISTING FAIL — `test_commit_with_include_code_stages_all_scope_paths`
**Severity: non-blocking — pre-existing, not T102**

`tests/test_commit_push.py:254`: the test expects scope directories (`tools/`, `tests/`, etc.) to be staged when `include_code=True`, but the implementation correctly skips paths that don't exist in the filesystem. `run_ticket.py` was not modified by T102. This test was already broken before T102.

---

## Verdict

**FAIL — blocking issues require fixes before merge**

Functional implementation of all 7 acceptance criteria is correct. Three test failures must be fixed:

1. Update `test_poll_github_issues_multiple_issues_sequential_ids` to reflect max_active_tickets=1 single-intake behavior
2. Update `test_main_poll_issues_flag_calls_poll_before_run_once` assertion to include `max_active_tickets=1`
3. Add `patch("run_daemon._sync_main_before_intake", return_value=True)` to all `poll_github_issues` tests that exercise the intake path — and add dedicated unit tests for `_sync_main_before_intake` itself
