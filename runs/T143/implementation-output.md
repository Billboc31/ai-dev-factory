Implementation complete. Here's a summary of all changes made:

---

## Files modified

**`tools/agent_runner/run_ticket.py`**
- Added `CONFLICT_RESOLUTION_NEEDED` and `CONFLICT_RESOLUTION_FAILED` to `VALID_STATES`. Neither has a `TRANSITIONS` entry — both are human-gate/terminal.

**`tools/agent_runner/run_daemon.py`**
- Added both new states to `HUMAN_GATE_STATES`
- Added `_CONFLICT_SKIP_STATES` constant (the states where detection is suppressed)
- Added `detect_pr_conflict(ticket_id, pr_number, run_dir, repo)` — calls `gh pr view --json mergeable`, and on `CONFLICTING` writes `pre_conflict_state`, `conflict_detected_at`, `conflict_pr_number`, `conflicted_files` to `state.json` and transitions to `CONFLICT_RESOLUTION_NEEDED`
- In `run_once()`, before the existing state dispatch, calls `detect_pr_conflict` for any ticket that has a `pr_number` and is not already in a conflict/terminal state

**`services/control_api/models/schemas.py`**
- Added 4 nullable fields to `TicketSummary`: `conflict_status`, `conflicted_files`, `conflict_detected_at`, `pre_conflict_state`

**`services/control_api/services/artifact_reader.py`**
- Added `_conflict_fields(data)` helper that extracts conflict metadata from a `state.json` dict
- Updated both `TicketSummary(...)` constructors in `list_tickets()` and `get_ticket()` to pass `**_conflict_fields(data)`
- Added `CONFLICT_RESOLUTION_NEEDED` and `CONFLICT_RESOLUTION_FAILED` to `_STATUS_MAP` (mapped to `waiting_human`/`failed` statuses respectively — `WorkflowTimeline.jsx` renders these correctly with no change needed)

**`services/control_api/routes/tickets.py`**
- Added `_mark_conflict_failed(project_root, ticket_id, worktrees_dir)` helper — validates state is `CONFLICT_RESOLUTION_NEEDED`, writes `CONFLICT_RESOLUTION_FAILED` directly to `state.json`, returns 409 `ActionResult` on wrong state
- Added `POST /{ticket_id}/mark-conflict-failed` endpoint (raises HTTP 409 from the helper's flag)
- Mirrored as `POST /{project_id}/tickets/{ticket_id}/mark-conflict-failed` in `project_router`

**`apps/dashboard/src/api/tickets.js`**
- Added `markConflictFailed` export

**`apps/dashboard/src/pages/TicketsPage.jsx`**
- Added `CONFLICT_STATES` set and conflict-specific `STATE_COLORS` entries
- Added `ConflictDetail` inline component (shows detection time, pre-conflict state, file list, "Manual resolution required" note, and "Mark as Failed" button wired to the API)
- Each conflicting ticket row now renders a `CONFLICT` badge and expands to show `ConflictDetail`

**`tests/test_conflict_resolver.py`** *(new)*
- 25 tests covering all acceptance criteria: state membership, no auto-run, conflict detection (mocked `gh`), metadata written to state.json, `TicketSummary` serialisation, `GET /tickets/{id}` conflict fields, `POST /mark-conflict-failed` transitions and 409/404 cases, terminal state invariant
