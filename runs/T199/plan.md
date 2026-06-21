## Objective

Introduce a human approval workflow that gates the new `ready_to_take` lifecycle state. After Ticket Readiness Evaluation flags a ticket `ready_candidate`, a human can approve execution (→ `ready_to_take`) or reject it (→ `blocked` with a visible reason). Approve and reject operations are **idempotent**: replaying the same decision returns the existing latest approval row without inserting a duplicate or raising. Contradictory transitions (approve after reject, reject after approve) return HTTP 409. All real state transitions are persisted append-only in a new `ticket_approvals` table; the API, dashboard, and board surface the approval history and the new state. Scheduler/worker behaviour is **not** changed.

## Included

### 1. Database layer — `ticket_approvals` table

- `tools/agent_runner/runtime_db.py`
  - Extend `_SCHEMA` with a new `CREATE TABLE IF NOT EXISTS ticket_approvals` block. SQLite columns (stdlib types only):
    ```
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id        TEXT NOT NULL,
    approval_type    TEXT NOT NULL,     -- 'execution' | 'plan' | 'code'  (only 'execution' used here)
    approval_status  TEXT NOT NULL,     -- 'pending' | 'approved' | 'rejected'
    approved_by      TEXT,
    approval_comment TEXT,
    approved_at      TEXT,              -- NULL while 'pending'
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
    ```
    plus `CREATE INDEX IF NOT EXISTS ix_ticket_approvals_ticket ON ticket_approvals(ticket_id, approval_type, id);`
  - New functions (mirroring the existing `upsert_ticket_*` / `get_ticket_*` style):
    - `insert_ticket_approval(db_path, ticket_id, approval_type, approval_status, approved_by, approval_comment) -> int` (returns row id; sets `approved_at` to `_now_iso()` for `approved` / `rejected`).
    - `list_ticket_approvals(db_path, ticket_id) -> list[dict]` (ORDER BY id ASC — append-only history).
    - `get_latest_ticket_approval(db_path, ticket_id, approval_type) -> dict | None`.
  - Extend the `_RUNTIME_DB_BACKEND == "postgres"` rebind block to expose the same names from `runtime_db_pg`.
- `tools/agent_runner/runtime_db_pg.py`
  - Add a matching `ticket_approvals` table (with `project_id TEXT NOT NULL`, `id BIGSERIAL`, composite uniqueness scoped by `(project_id, id)`), and Postgres equivalents of `insert_ticket_approval`, `list_ticket_approvals`, `get_latest_ticket_approval`.
- Extend `ticket_readiness.readiness_status` accepted values to include `ready_to_take` (no schema change — `readiness_status` is a free-form TEXT; only the evaluator/service writes it).

### 2. Approval service — `tools/agent_runner/ticket_approval_service.py`

New stdlib-only module (no third-party deps), import-time symmetric with `ticket_readiness_evaluator.py`:

- `request_execution_approval(db_path, ticket_id) -> dict`
  Creates a `pending` row for `approval_type='execution'`. Idempotent: if the latest execution approval is already `pending`, returns it unchanged.

- `approve_execution(db_path, ticket_id, approved_by, comment=None) -> dict`
  **Idempotent** algorithm:
  1. Load current `ticket_readiness` row.
  2. Load latest execution approval via `get_latest_ticket_approval(..., 'execution')`.
  3. If latest execution approval exists and `approval_status == 'approved'`:
     - return the existing row unchanged (no insert, no readiness write, no raise).
  4. Else if latest execution approval exists and `approval_status == 'rejected'`:
     - raise `ValueError("contradictory_transition")` — API layer maps to 409.
  5. Else (no prior decision, or latest is `pending`) and `readiness_status == 'ready_candidate'`:
     - insert a new `approved` row;
     - call `upsert_ticket_readiness(..., readiness_status='ready_to_take', evaluated_at=_now_iso())`;
     - return the new row.
  6. Otherwise (e.g. `not_started`, `blocked` not caused by rejection, unknown ticket):
     - raise `ValueError("invalid_state")` — API layer maps to 409.

- `reject_execution(db_path, ticket_id, approved_by, comment=None) -> dict`
  **Idempotent** algorithm:
  1. Load current `ticket_readiness` row.
  2. Load latest execution approval.
  3. If latest execution approval exists and `approval_status == 'rejected'`:
     - return the existing row unchanged (no insert, no readiness write, no duplicate blocking reason, no raise).
  4. Else if latest execution approval exists and `approval_status == 'approved'`:
     - raise `ValueError("contradictory_transition")` — API layer maps to 409.
  5. Else (no prior decision, or latest is `pending`) and `readiness_status == 'ready_candidate'`:
     - insert a new `rejected` row;
     - set `readiness_status='blocked'` and append `"Execution approval rejected by <approved_by>"` to `blocking_reasons_json` (de-duplicated against existing reasons);
     - return the new row.
  6. Otherwise:
     - raise `ValueError("invalid_state")` — API layer maps to 409.

- `get_ticket_approvals(db_path, ticket_id) -> list[dict]` — returns full append-only history (real transitions only; idempotent retries never appended).

- `compute_execution_eligibility(db_path, ticket_id) -> str` — pure read helper returning one of `not_started | ready_candidate | ready_to_take | blocked | …` by combining the latest execution approval with the current readiness row. Used by both the API and by the readiness evaluator on re-run to preserve `ready_to_take` instead of demoting it back to `ready_candidate`.

- Hook `compute_execution_eligibility` into `ticket_readiness_evaluator.run_evaluation`: after computing base candidacy, if base says `ready_candidate` and the latest execution approval is `approved`, persist `ready_to_take` instead.

### 3. API — `services/control_api/routes/approvals.py`

New router, mirroring `routes/readiness.py` structure (both `/tickets/...` and `/projects/{project_id}/tickets/...` mounts):

- `GET  /tickets/{ticket_id}/approvals` → `TicketApprovalHistory` (list of `TicketApproval` items).
- `POST /tickets/{ticket_id}/approve-execution` (body: `ApprovalDecision { approved_by: str, comment: str | None }`) → `TicketApproval`.
  - 200 on success **and** on idempotent replay (same latest `approved` row returned).
  - 409 when the service raises `ValueError("contradictory_transition")` (latest is `rejected`) or `ValueError("invalid_state")` (readiness is not `ready_candidate` and there is no existing `approved` decision to replay).
  - 404 when the ticket is unknown.
- `POST /tickets/{ticket_id}/reject-execution` (same body) → `TicketApproval`, symmetrical semantics:
  - 200 on success **and** on idempotent replay (same latest `rejected` row returned).
  - 409 on contradictory transition (latest is `approved`) or invalid state.
  - 404 when the ticket is unknown.

Models added to `services/control_api/models/schemas.py`:
- `TicketApproval`, `TicketApprovalHistory`, `ApprovalDecision`.

Wiring in `services/control_api/main.py`:
- `from .routes import approvals` and `app.include_router(approvals.router); app.include_router(approvals.project_router)`.

### 4. Frontend dashboard

- `apps/dashboard/src/api/tickets.js`
  Add: `getTicketApprovals`, `approveExecution(id, projectId, payload)`, `rejectExecution(id, projectId, payload)`.
- `apps/dashboard/src/components/HumanApprovalPanel.jsx` (new)
  - Subscribes to readiness + approvals (small poll, same hook pattern as `TicketReadinessPanel`).
  - Shows: current effective status badge (`READY CANDIDATE` / `READY TO TAKE` / `BLOCKED`), latest approver/date/comment, append-only history list.
  - Two buttons: **Approve for execution** and **Reject execution**, with a textarea for the comment.
  - Buttons are enabled when `readiness_status === 'ready_candidate'`, **or** when the corresponding decision is already the latest one (so a user retry stays a no-op 200, matching backend idempotency); disabled otherwise with a tooltip explaining the reason.
- `apps/dashboard/src/pages/TicketDetailPage.jsx`
  - Render `<HumanApprovalPanel ticketId={id} projectId={projectId} />` directly under `<TicketReadinessPanel />`.
- `apps/dashboard/src/pages/BoardPage.jsx`
  - Show `READY CANDIDATE`, `READY TO TAKE`, `BLOCKED` badges on `BoardCard` based on the ticket's `readiness_status` (fetched alongside board items — extend the existing board response or fetch readiness per ticket; see Excluded).
  - Add a top-of-page filter `<select>` (`all | ready_candidate | ready_to_take | blocked`) that filters cards client-side.

### 5. Tests

- `tests/test_ticket_approval_db.py` — schema creation, insert/list/latest helpers, append-only ordering.
- `tests/test_ticket_approval_service.py`
  - `approve_execution` when `ready_candidate` → state becomes `ready_to_take`, row inserted.
  - `reject_execution` when `ready_candidate` → state becomes `blocked`, reason appended.
  - **Idempotency**:
    - `approve_execution` called twice in a row returns the same row object both times; `list_ticket_approvals` reports exactly one `approved` row.
    - `reject_execution` called twice in a row returns the same row object both times; `list_ticket_approvals` reports exactly one `rejected` row; `blocking_reasons_json` still contains the rejection reason exactly once.
  - **Contradictions**:
    - `reject_execution` after a prior `approved` raises `ValueError("contradictory_transition")`.
    - `approve_execution` after a prior `rejected` raises `ValueError("contradictory_transition")`.
  - **Invalid state** (no prior decision and readiness is not `ready_candidate`, e.g. `not_started`): raises `ValueError("invalid_state")`.
  - Re-running `ticket_readiness_evaluator.run_evaluation` after an `approved` execution approval preserves `ready_to_take` (does not demote to `ready_candidate`).
- `tests/test_ticket_approval_api.py` — FastAPI client tests:
  - Happy paths for approve and reject on a `ready_candidate` ticket.
  - **Idempotent replay** returns 200 and history length stays at 1.
  - **Contradictory transitions** return 409.
  - **Invalid state** (e.g. ticket is `not_started`, no prior decision) returns 409.
  - Unknown ticket returns 404.
  - History shape matches `TicketApprovalHistory`.
- Existing tests under `tests/test_ticket_readiness_*.py`, `tests/test_human_approval.py`, `tests/test_control_api_endpoints.py` continue to pass unchanged.

## Excluded

- No change to `run_daemon.py`, the supervisor, the scheduler, worker dispatch, or any execution gating. `ready_to_take` is purely informational for this ticket.
- No change to the legacy `apply_human_approval` / `runs/<ticket>/state.json` plan/implementation approvals (`tests/test_human_approval.py` semantics are untouched).
- `approval_type='plan'` and `approval_type='code'` are reserved by the schema but not exposed via API or service helpers in this ticket.
- No bulk/auto approval, no email/Slack notification, no role/permission system — `approved_by` is a free-form string taken from the request body.
- No migration of existing `runs/<ticket>/plan-approved.md` markers into the new table.
- **No reapproval, revoke, or reopen workflow.** Once the latest execution decision is `approved` or `rejected`, the only same-action retry that is accepted is the identical idempotent replay; the opposite action returns 409. Switching decisions is out of scope for this ticket.
- No board-server-side filter: filtering is client-side; we won't extend `board_service.py`'s SQL beyond, at most, joining the existing `ticket_readiness` row so `readiness_status` reaches the UI. If joining proves intrusive, the Board falls back to a per-card `GET /tickets/{id}/readiness` call (already public).
- No change to the project-map / parallel-safe logic.

## Acceptance criteria

- `ticket_approvals` table exists on both SQLite and Postgres backends after API startup; `init_runtime_db` is idempotent.
- `POST /tickets/{id}/approve-execution` on a `ready_candidate` ticket:
  - returns 200 with a `TicketApproval` whose `approval_status='approved'`;
  - `GET /tickets/{id}/readiness` then reports `readiness_status='ready_to_take'`;
  - `GET /tickets/{id}/approvals` includes the new row.
- `POST /tickets/{id}/reject-execution` on a `ready_candidate` ticket:
  - returns 200 with `approval_status='rejected'`;
  - `GET /tickets/{id}/readiness` then reports `readiness_status='blocked'` with `"Execution approval rejected by <approver>"` in `blocking_reasons`.
- **Idempotent approve**: a second `POST /tickets/{id}/approve-execution` after the ticket is already `approved` / `ready_to_take` returns **200** with the same latest approval row; `GET /tickets/{id}/approvals` still reports exactly one `approved` row; readiness remains `ready_to_take`.
- **Idempotent reject**: a second `POST /tickets/{id}/reject-execution` after the ticket is already `rejected` / `blocked` returns **200** with the same latest rejection row; `GET /tickets/{id}/approvals` still reports exactly one `rejected` row; `blocking_reasons` still contains the rejection reason exactly once.
- **Contradictory transitions return 409**:
  - `POST /tickets/{id}/reject-execution` when latest is `approved` returns 409.
  - `POST /tickets/{id}/approve-execution` when latest is `rejected` returns 409.
- **Invalid state returns 409**: an approve or reject request on a ticket that is not `ready_candidate` and has no prior decision to replay returns 409.
- **404** is returned for an unknown ticket id on all three endpoints.
- Approval history is **append-only for real state transitions**: each successful new decision appends a row; idempotent retries never append a row.
- Re-running `POST /tickets/{id}/evaluate-readiness` on an already-approved ticket leaves `readiness_status='ready_to_take'` (does not demote).
- The Ticket Detail page renders the Human Approval section, with buttons enabled when `readiness_status === 'ready_candidate'` or when the corresponding decision is already the latest one (idempotent retry), and lists prior approvals (approver, date, comment).
- The Board page renders `READY CANDIDATE`, `READY TO TAKE`, and `BLOCKED` badges and supports client-side filtering on these states.
- `pytest` for the existing suite (in particular `tests/test_ticket_readiness_*.py`, `tests/test_human_approval.py`, `tests/test_control_api_endpoints.py`) still passes; the new `tests/test_ticket_approval_*.py` files pass.
- Scheduler/daemon/worker behaviour is unchanged: no new code path in `run_daemon.py`, `services/supervisor/`, or `tools/agent_runner/run_ticket.py` consults `ready_to_take` to start, queue, or block execution.
