# Tester Report — T144 — Conflict Resolver Agent and Review UI

Generated: 2026-05-23

---

## Acceptance Criteria

### AC1 — User can launch conflict resolution from dashboard

**Status: PASS**

`ConflictResolutionPanel` in `TicketDetailPage.jsx:78-86` renders a "Resolve Conflicts" button when state is `CONFLICT_RESOLUTION_NEEDED`. Clicking it calls `api.resolveConflicts()` which hits `POST /tickets/{ticket_id}/resolve-conflicts` (`routes/tickets.py:305`). The endpoint atomically transitions to `CONFLICT_RESOLVING` and dispatches the resolver in a background thread. Returns HTTP 202.

---

### AC2 — Resolver runs in the existing ticket worktree

**Status: PASS**

`subprocess_runner.resolve_conflicts()` (`subprocess_runner.py:202`) resolves the working directory via `_resolve_action_cwd()`, which honours `worktrees_dir` and returns the ticket worktree path. `run_conflict_resolver.py` is invoked with `cwd=cwd` pointing to that worktree. All git operations and file reads/writes use worktree-relative paths.

---

### AC3 — Resolver receives full ticket and conflict context

**Status: PASS**

`conflict_context_collector.py` assembles `conflict/context.md` before the rebase begins. Sources collected:

| Source | Mechanism |
|---|---|
| ticket.md | file read |
| plan.md | file read |
| reviews/*.md | glob |
| fixes/*.md (non-context) | glob |
| PR diff | `gh pr diff {pr_number}` |
| merge-base diff | `git diff {merge_base}..HEAD` |
| latest main commits since conflict_detected_at | `git log origin/main --oneline --since=` |
| full content of each conflicted file | file read per path in state.json |

Metadata (pre_conflict_state, conflict_detected_at, conflict_pr_number, conflicted_files) is read from state.json populated by the daemon at detection time.

---

### AC4 — Resolved branch is pushed with force-with-lease

**Status: PASS**

`run_conflict_resolver.py:320-329` executes `git push --force-with-lease origin {branch}`. Push failure transitions to `CONFLICT_RESOLUTION_FAILED` and writes to `conflict/error.log`.

---

### AC5 — Resolver artifacts are persisted

**Status: PASS**

All artifacts written to `runs/{ticket_id}/conflict/`:

| Artifact | When written |
|---|---|
| `context.md` | Before rebase — full context for the resolver |
| `resolution.md` | After AI resolver runs (or after clean rebase) |
| `test-report.md` | After tests run |
| `error.log` | On any failure path |

Prompt snapshots are also written to `runs/{ticket_id}/prompts/conflict-resolver-attempt-N.md` for reproducibility.

---

### AC6 — Dashboard shows status, summary, changed files and tests

**Status: PARTIAL — changed files gap**

The `ConflictResolutionPanel` shows:

| Element | Shown | Notes |
|---|---|---|
| State / status | PASS | Rendered per-state with appropriate messaging |
| Conflicted files (pre-resolution) | PASS | Bulleted list from `ticket.conflicted_files` |
| Resolver logs | PASS | Available via the existing "logs" tab (runtime.log) |
| Resolution summary | PASS | `ticket.resolution_summary` from `conflict/resolution.md` |
| Test results | PASS | `ticket.conflict_test_result` from `conflict/test-report.md` |
| **Changed files (post-resolution)** | **FAIL** | No dedicated field. `conflicted_files` shows pre-resolution files only. No structured `changed_files` field derived from the resolution commit diff. |

The ticket spec explicitly lists "changed files" and "conflicted files" as distinct UI elements. The dashboard shows the latter but not the former.

---

### AC7 — Human approve/reject gate required before workflow resumes

**Status: PASS**

After successful resolution, state transitions to `CONFLICT_RESOLVED_REVIEW_NEEDED`. The daemon treats this as a `HUMAN_GATE_STATE` and skips it (`run_daemon.py:1663`). Dashboard renders Approve / Reject buttons:

- **Approve** (`run_ticket.py:881`): validates state, reads `pre_conflict_state` from state.json, transitions to that prior state. Validates that `pre_conflict_state` is a recognised `VALID_STATE`.
- **Reject** (`run_ticket.py:855`): transitions `CONFLICT_RESOLVED_REVIEW_NEEDED` → `CONFLICT_RESOLUTION_NEEDED`, allowing the resolver to be re-triggered.

No code path resumes the workflow without this gate.

---

### AC8 — Failure ends in CONFLICT_RESOLUTION_FAILED with logs

**Status: PASS**

Every failure branch in `run_conflict_resolver.py` calls `_transition_state(ticket_id, run_dir, "CONFLICT_RESOLUTION_FAILED")` and writes to both `runtime.log` (via `_log()`) and `conflict/error.log` (via `_write_error_log()`). Covered failure paths:

- Cannot read current git branch
- Running on `main` branch (safety guard)
- Branch mismatch between worktree and state.json
- `git fetch` failure
- Context collection exception
- Prompt file not found
- AI resolver non-zero exit
- `git add` failure
- `git rebase --continue` failure (non-trivial)
- `git commit` failure (non-trivial)
- `git push --force-with-lease` failure

The dashboard `CONFLICT_RESOLUTION_FAILED` panel directs the user to the "logs" tab (`TicketDetailPage.jsx:131-135`).

---

## Regressions Observed

None. The new states (`CONFLICT_RESOLVING`, `CONFLICT_RESOLVED_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_FAILED`) are correctly added to `VALID_STATES` in `run_ticket.py:62-64` and to `HUMAN_GATE_STATES` in `run_daemon.py:141-147`. Existing workflow states and transitions are not modified.

---

## Blocking Issues

### BUG-1 — `CONFLICT_RESOLVING` absent from `_CONFLICT_SKIP_STATES` (daemon race condition)

**Severity: MEDIUM**

`run_daemon.py:832-836`:

```python
_CONFLICT_SKIP_STATES = frozenset({
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
    "TEST_COMPLETE",
})
```

`CONFLICT_RESOLVING` is absent. The daemon's main loop checks this set at line 1630 before calling `detect_pr_conflict()`. If a ticket is in `CONFLICT_RESOLVING` when the daemon iterates, `detect_pr_conflict()` queries GitHub, sees the PR still CONFLICTING (push has not happened yet), and overwrites `state.json` to `CONFLICT_RESOLUTION_NEEDED` with `pre_conflict_state = "CONFLICT_RESOLVING"`. The active resolver then finishes and pushes, transitioning to `CONFLICT_RESOLVED_REVIEW_NEEDED`. If the user then approves, `apply_approve_conflict_resolution` restores `pre_conflict_state = "CONFLICT_RESOLVING"` — an invalid workflow state for normal progression.

`CONFLICT_RESOLVED_REVIEW_NEEDED` has the same exposure: if GitHub still shows the PR as CONFLICTING before the push is reflected, the daemon could re-trigger conflict detection on a ticket awaiting human review, clobbering the pending `pre_conflict_state`.

**Fix**: Add `"CONFLICT_RESOLVING"` and `"CONFLICT_RESOLVED_REVIEW_NEEDED"` to `_CONFLICT_SKIP_STATES` in `run_daemon.py`.

---

## Non-Blocking Observations

### OBS-1 — No structured `changed_files` field after resolution

As noted in AC6, the API schema (`schemas.py:56-69`) exposes `conflicted_files` (pre-resolution) but no post-resolution changed-files list. If explicit traceability of resolver edits is required, a `resolution_changed_files` field could be populated from `git diff-tree --no-commit-id -r --name-only {sha}` of the resolution commit.

### OBS-2 — Conflicted file content in `context.md` captured before rebase

`collect_context()` is called at `run_conflict_resolver.py:188`, before `git rebase origin/main` at line 198. At that point the files do not yet contain conflict markers. The "Conflicted Files" section in `context.md` therefore shows ticket-branch content without `<<<<<<<`/`=======`/`>>>>>>>` markers. The AI resolver will see the actual markers when it opens files in the worktree during resolution, so functional correctness is not affected — but the context snapshot is misleading as a debugging artefact.

---

## Validation Summary

| Acceptance Criterion | Status |
|---|---|
| Launch from dashboard | PASS |
| Runs in ticket worktree | PASS |
| Full ticket + conflict context | PASS |
| Push with force-with-lease | PASS |
| Artifacts persisted | PASS |
| Dashboard: status / summary / changed files / tests | PARTIAL (changed files missing) |
| Human approve/reject gate | PASS |
| Failure → CONFLICT_RESOLUTION_FAILED with logs | PASS |

**Result: 7/8 acceptance criteria fully met. 1 partial. 1 blocking bug (daemon race condition). 2 non-blocking observations.**
