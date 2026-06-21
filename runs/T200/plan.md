## Objective

Introduce a manual human-approval workflow that gates a ticket's transition from `READY_CANDIDATE` (Readiness Evaluator verdict) to a new `READY_TO_TAKE` state, persisted in two new tables (`ticket_approval` + `ticket_approval_history`), exposed through three new API endpoints, and surfaced as a "Ticket Approval" panel on the ticket detail page. Scheduler, dispatcher and execution pipeline are not modified — approval is informational/decisional only.

## Included

### Database — SQLite schema (`tools/agent_runner/runtime_db.py`)

- Extend `_SCHEMA` with two new tables:
  - `ticket_approval` (one active row per ticket): `ticket_id TEXT PRIMARY KEY`, `approval_status TEXT NOT NULL DEFAULT 'not_requested'`, `approved_by TEXT`, `approved_at TEXT`, `revoked_by TEXT`, `revoked_at TEXT`, `approval_reason TEXT`, `created_at TEXT NOT NULL`, `updated_at TEXT NOT NULL`.
  - `ticket_approval_history`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `ticket_id TEXT NOT NULL`, `action TEXT NOT NULL`, `actor TEXT`, `reason TEXT`, `created_at TEXT NOT NULL`. Index `(ticket_id, created_at)`.
- Add helpers next to the existing readiness helpers:
  - `upsert_ticket_approval(db_path, ticket_id, **fields)` — same insert-or-update shape as `upsert_ticket_readiness`, default `approval_status="not_requested"`.
  - `get_ticket_approval(db_path, ticket_id) -> dict | None`.
  - `insert_ticket_approval_history(db_path, ticket_id, action, actor=None, reason=None)`.
  - `list_ticket_approval_history(db_path, ticket_id, limit: int = 50) -> list[dict]` (ordered by `created_at DESC`).
- Allowed statuses (validated at the service layer, not in SQL): `not_requested | ready_candidate | ready_to_take | revoked`.
- Allowed history actions: `approved | revoked | reapproved`.

### Database — Postgres schema (`tools/agent_runner/runtime_db_pg.py`)

- Mirror the two tables with the existing `(project_id, ticket_id)` partition key convention.
- Add Postgres versions of the four helpers above so the `runtime_db` rebinding block (`upsert_ticket_approval`, `get_ticket_approval`, `insert_ticket_approval_history`, `list_ticket_approval_history`) keeps the same public names.
- Append the new helper names to the rebind block at the bottom of `runtime_db.py`.

### Approval service (`tools/agent_runner/ticket_approval_service.py`, new module)

A thin, side-effect-free helper layer used by the API routes. Pure DB + readiness-row lookups, no HTTP:

- `approve(db_path, ticket_id, actor: str | None, reason: str | None) -> dict`
  - Reads `runtime_db.get_ticket_readiness`. If `readiness_status != "ready_candidate"`, return `{"ok": False, "code": "not_ready_candidate"}` so the route can map to 409.
  - If current approval row already has `approval_status == "ready_to_take"`, return the existing row unchanged (idempotent — no new history entry).
  - Otherwise upsert `approval_status="ready_to_take"`, set `approved_by`, `approved_at=_now_iso()`, clear `revoked_by`/`revoked_at`, store `approval_reason`. Insert history row with `action="approved"` (or `"reapproved"` if a prior `ready_to_take`→`revoked` cycle exists).
- `revoke(db_path, ticket_id, actor: str | None, reason: str | None) -> dict`
  - If current `approval_status != "ready_to_take"`, return the existing row unchanged (idempotent — no new history entry).
  - Otherwise upsert `approval_status="revoked"`, set `revoked_by`, `revoked_at=_now_iso()`, keep `approval_reason` from the request. Insert history row with `action="revoked"`.
- `get(db_path, ticket_id) -> dict | None` — convenience wrapper returning the row plus a flattened `history` list.

### Pydantic schemas (`services/control_api/models/schemas.py`)

Add:

- `TicketApprovalHistoryEntry`: `id`, `ticket_id`, `action`, `actor: str | None`, `reason: str | None`, `created_at`.
- `TicketApproval`: `ticket_id`, `approval_status`, `approved_by: str | None`, `approved_at: str | None`, `revoked_by: str | None`, `revoked_at: str | None`, `approval_reason: str | None`, `created_at: str | None`, `updated_at: str | None`, `history: list[TicketApprovalHistoryEntry] = []`.
- `TicketApprovalRequest`: `actor: str | None = None`, `reason: str | None = None`.

### API routes (`services/control_api/routes/approval.py`, new file)

Following the structure of `routes/readiness.py`:

- `GET /tickets/{ticket_id}/approval` → 200 with `TicketApproval` (auto-create a `not_requested` row on first read so the panel always renders), 404 only if the ticket itself does not exist.
- `POST /tickets/{ticket_id}/approve` (body `TicketApprovalRequest`) → 200 with `TicketApproval`; returns 409 with detail `"ticket is not ready_candidate"` when the service returns `not_ready_candidate`; 404 if ticket unknown; 503 if DB unavailable.
- `POST /tickets/{ticket_id}/revoke-approval` (body `TicketApprovalRequest`) → 200 with `TicketApproval`; idempotent (no error when already revoked); 404 / 503 as above.
- Mirror the `project_router` GET/POST prefix variants used by `readiness.py`.
- Register both routers in `services/control_api/main.py` next to the readiness router include block, with a comment `# T200: /tickets/{id}/approval — human approval workflow.`.

### Frontend — API client (`apps/dashboard/src/api/tickets.js`)

Add three exports:

- `getTicketApproval(id, projectId)` → `GET .../approval`.
- `approveTicket(id, projectId, { actor, reason })` → `POST .../approve`.
- `revokeTicketApproval(id, projectId, { actor, reason })` → `POST .../revoke-approval`.

### Frontend — Approval panel (`apps/dashboard/src/components/TicketApprovalPanel.jsx`, new component)

Mirrors `TicketReadinessPanel.jsx`:

- Props: `ticketId`, `projectId`, plus optional `readinessStatus` (passed from `TicketDetailPage` so the panel can disable the approve button when readiness ≠ `ready_candidate`).
- Renders:
  - Heading "Ticket Approval".
  - `READY TO TAKE` badge (emerald) when `approval_status === "ready_to_take"`; greyed "NOT REQUESTED" / "REVOKED" badges for the other states.
  - Fields: current status, approver (`approved_by`), approval date (`approved_at`), revoker, revoke date, reason.
  - "Approve For Execution" button — disabled when readiness is not `ready_candidate` or when already `ready_to_take`. Optional inline `actor` and `reason` text inputs in a small form.
  - "Revoke Approval" button — visible only when status is `ready_to_take`.
  - History list (most recent first) with action badge (approved/revoked/reapproved), actor, reason, timestamp.
- Show 409 errors inline as a banner ("Ticket must be READY_CANDIDATE to be approved").

### Frontend — Ticket detail page wiring (`apps/dashboard/src/pages/TicketDetailPage.jsx`)

- Import `TicketApprovalPanel`.
- Render `<TicketApprovalPanel ticketId={id} projectId={projectId} readinessStatus={readinessStatus} />` immediately below `<TicketReadinessPanel />`.
- Lift readiness status (or refetch via `getTicketReadiness`) so the approval panel can be aware of `ready_candidate`. If duplicating the call is the smaller change, call `getTicketReadiness` from inside the approval panel itself rather than restructuring state.

### Tests (Python — `tests/`)

- `test_ticket_approval_db.py` — SQLite: tables exist after `init_runtime_db`; upsert + get round-trip; history insert + list ordering; status enum stored as string.
- `test_ticket_approval_service.py` — `approve` returns `not_ready_candidate` when readiness is missing or `blocked`; happy path moves status to `ready_to_take` and appends `approved` history; second `approve` is idempotent (no extra history row); `revoke` after `ready_to_take` flips to `revoked` and writes `revoked` history; `revoke` when already `revoked` is idempotent; `approve` after a `revoked` cycle writes `reapproved`.
- `test_ticket_approval_api.py` — FastAPI `TestClient` against `create_app`: 404 for unknown ticket; `GET` auto-creates `not_requested`; `POST /approve` returns 409 when readiness is not `ready_candidate`; `POST /approve` happy path returns 200 + `ready_to_take` + history; idempotent re-approve; revoke flow + idempotent re-revoke.

### Tests (Frontend)

- `apps/dashboard/tests` — add a panel test mirroring the existing readiness panel test if one exists (skip if there is no existing dashboard test scaffold; document the omission in the PR description).

## Excluded

- Any change to `daemon_manager`, `run_daemon.py`, `worktree_manager.py`, the scheduler, or any execution dispatch logic — no ticket starts automatically because of approval.
- Reservation / locking semantics (the `READY_TO_TAKE` state is purely informational for this ticket).
- Stale-context invalidation: revocation does not automatically happen if `main` advances after approval.
- Automatic, policy-based, or risk-score-based approvals (explicitly deferred per "Human workflow" / "Non-goals").
- Authentication or RBAC on the approval endpoints — `actor` is a free-form string supplied by the client.
- Modifications to `ticket_readiness_evaluator.py` (readiness logic stays unchanged).
- Changes to the project map / board / dispatcher views — only the ticket detail page is updated.
- Backfill or migration of approval rows for existing tickets (rows are created on first read/write).

## Acceptance criteria

- Running the API once initialises `ticket_approval` and `ticket_approval_history` in both the SQLite and Postgres backends (`init_runtime_db` / Postgres schema bootstrap).
- `GET /tickets/{id}/approval` returns 200 with `approval_status="not_requested"` for a known ticket that was never approved.
- `POST /tickets/{id}/approve` returns 409 when the ticket has no readiness row or its `readiness_status` is not `ready_candidate`.
- `POST /tickets/{id}/approve` on a `ready_candidate` ticket flips `approval_status` to `ready_to_take`, sets `approved_by`/`approved_at`, and writes a single `approved` history row.
- Calling `POST /tickets/{id}/approve` twice in a row yields the same final row and exactly one new history entry.
- `POST /tickets/{id}/revoke-approval` on a `ready_to_take` ticket sets `approval_status="revoked"`, populates `revoked_by`/`revoked_at`, and writes a `revoked` history row.
- Calling `POST /tickets/{id}/revoke-approval` twice in a row yields the same final row and exactly one new history entry.
- A subsequent `POST /tickets/{id}/approve` after a `revoked` cycle writes a `reapproved` history row and returns `approval_status="ready_to_take"`.
- The ticket detail page renders a "Ticket Approval" panel below the readiness panel, displaying status, approver, approval date, reason and full history; the "Approve For Execution" button is disabled when readiness is not `ready_candidate`.
- A `READY TO TAKE` badge is visible on the panel exactly when `approval_status === "ready_to_take"`.
- The existing test suite (`pytest tests/`) continues to pass, and the three new test files pass.
- `grep` for the scheduler / daemon entry points (`run_daemon.py`, `daemon_manager.py`) shows no diff lines from this ticket — execution pipeline is untouched.
