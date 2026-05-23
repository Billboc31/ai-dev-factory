Now I have enough context to write a well-grounded plan.

## Objective

Add safe conflict detection and dashboard visibility for ticket PR branches: when a ticket PR is detected as conflicting with main, the ticket transitions to `CONFLICT_RESOLUTION_NEEDED`, the pre-conflict state is preserved, and conflict metadata (conflicted files, detection timestamp, PR info) is surfaced through the API and dashboard — with no automatic branch rewriting or AI resolution in this iteration.

## Included

### 1. New workflow states — `tools/agent_runner/run_ticket.py` (lines 52–85)

- Add to `VALID_STATES`: `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLUTION_FAILED`.
- Add to `AUTO_RUNNABLE_STATES` in `run_daemon.py` (lines 132–139): neither new state is auto-runnable (both require human action).
- Add to `HUMAN_GATE_STATES`: `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLUTION_FAILED`.
- `CONFLICT_RESOLUTION_FAILED` is terminal (no transition out).
- No new `TRANSITIONS` entry for these states (no automated step triggers them).

### 2. Conflict detection — `tools/agent_runner/run_daemon.py` (polling loop, lines 829–869 and main loop lines 1742–1757)

- New function `detect_pr_conflict(ticket_id, pr_number)`: runs `gh pr view <pr_number> --json mergeable`, returns `True` if value is `"CONFLICTING"`. Returns `False` if no PR number, or on `gh` command failure (fail-safe).
- In the daemon polling loop, for each active ticket that has a `pr_number` and is not already in a conflict state or terminal state: call `detect_pr_conflict`.
- On conflict detected:
  - Write `pre_conflict_state` (current state string) to `state.json`.
  - Write `conflict_detected_at` (ISO timestamp), `conflict_pr_number`, `conflicted_files` (from `gh pr view --json files` filtered to conflicting) to `state.json`.
  - Transition state to `CONFLICT_RESOLUTION_NEEDED` via existing `checkpoint_transition` logic.
- Detection only runs for states outside `{CONFLICT_RESOLUTION_NEEDED, CONFLICT_RESOLUTION_FAILED, TEST_COMPLETE}` to avoid double-detection.

### 3. Schema extension — `services/control_api/models/schemas.py` (lines 56–64)

Add to `TicketSummary`:
- `conflict_status: str | None = None` — the current conflict state name or `None`.
- `conflicted_files: list[str] | None = None` — list of conflicting file paths.
- `conflict_detected_at: str | None = None` — ISO timestamp of detection.
- `pre_conflict_state: str | None = None` — the state the ticket was in before conflict.

### 4. Artifact reader — `services/control_api/services/artifact_reader.py`

- In `get_ticket()`: populate the four new `TicketSummary` fields from `state.json` (fields `conflict_status`, `conflicted_files`, `conflict_detected_at`, `pre_conflict_state`).

### 5. New API endpoint — `services/control_api/routes/tickets.py`

- `POST /{ticket_id}/mark-conflict-failed`: transitions state to `CONFLICT_RESOLUTION_FAILED` via `checkpoint_transition`. Returns 409 if ticket is not in `CONFLICT_RESOLUTION_NEEDED`.
- Mirror in the project-scoped router.

### 6. Dashboard — `apps/dashboard/src/`

- `TicketsPage.jsx`: add a conflict badge (e.g. red `CONFLICT` label) on ticket rows whose state is `CONFLICT_RESOLUTION_NEEDED` or `CONFLICT_RESOLUTION_FAILED`.
- Conflict detail inline section (collapsible, below the ticket row or in ticket detail view):
  - Show `conflict_detected_at`, `pre_conflict_state`, `conflicted_files` list.
  - Show a "Mark as Failed" button wired to `POST /mark-conflict-failed`.
  - Show a static note: "Manual resolution required before workflow can resume."
- `WorkflowTimeline.jsx`: map `CONFLICT_RESOLUTION_NEEDED` → `waiting_human`, `CONFLICT_RESOLUTION_FAILED` → `failed`.

### 7. Tests — `tests/test_conflict_resolver.py` (new file)

- `CONFLICT_RESOLUTION_NEEDED` and `CONFLICT_RESOLUTION_FAILED` present in `VALID_STATES`.
- Neither new state present in `AUTO_RUNNABLE_STATES`.
- `detect_pr_conflict` returns `True` when `gh` output contains `"CONFLICTING"`, `False` otherwise (mock `gh`).
- On conflict detection: `state.json` contains `pre_conflict_state`, `conflict_detected_at`, `conflict_pr_number`, `conflicted_files`.
- State transitions to `CONFLICT_RESOLUTION_NEEDED` after detection.
- `TicketSummary` serialises the four new fields correctly.
- `POST /mark-conflict-failed` transitions `CONFLICT_RESOLUTION_NEEDED` → `CONFLICT_RESOLUTION_FAILED`.
- `POST /mark-conflict-failed` returns 409 if ticket is not in `CONFLICT_RESOLUTION_NEEDED`.
- `CONFLICT_RESOLUTION_FAILED` has no outgoing transition (terminal).

## Excluded

- AI conflict resolver agent and associated prompt/role files.
- Automatic rebase or branch rewriting of any kind.
- `git push --force-with-lease` or any push during this ticket.
- `approve-conflict-resolution` endpoint (no automated resume path).
- Conflict detection for branches without a PR number (rebase-only detection deferred).
- Automatic test execution after conflict detection.
- Memory update or new memory workflow states.
- `CONFLICT_RESOLVING` and `CONFLICT_RESOLVED_REVIEW_NEEDED` states (resolver ticket scope).
- Multi-branch or semantic dependency graph logic.

## Acceptance criteria

1. `VALID_STATES` in `run_ticket.py` contains `CONFLICT_RESOLUTION_NEEDED` and `CONFLICT_RESOLUTION_FAILED`.
2. Neither new state appears in `AUTO_RUNNABLE_STATES`; both appear in `HUMAN_GATE_STATES`.
3. `CONFLICT_RESOLUTION_FAILED` has no entry in `TRANSITIONS` (confirmed terminal).
4. When `gh pr view` returns `"CONFLICTING"` for a ticket's PR, the daemon writes `pre_conflict_state`, `conflict_detected_at`, `conflict_pr_number`, and `conflicted_files` to `state.json` and transitions to `CONFLICT_RESOLUTION_NEEDED`.
5. No git rebase, reset, or push is executed during conflict detection.
6. `GET /tickets/{ticket_id}` response includes `conflict_status`, `conflicted_files`, `conflict_detected_at`, `pre_conflict_state` (all nullable).
7. `POST /tickets/{ticket_id}/mark-conflict-failed` succeeds from `CONFLICT_RESOLUTION_NEEDED` and returns 409 from any other state.
8. Dashboard ticket rows display a conflict badge for the two new states.
9. Dashboard conflict detail section shows `conflicted_files` and `pre_conflict_state` with a "Mark as Failed" button.
10. `tests/test_conflict_resolver.py` passes with no regressions in the existing test suite.
