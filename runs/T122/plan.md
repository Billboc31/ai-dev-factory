## Objective
Add a persistent audit trail for all dashboard ticket actions (approve-plan, request-plan-fix, approve-implementation, request-implementation-fix, run-next, commit, push, checkpoint, archive). Each event is stored in the existing `runtime_events` SQLite table, exposed via a new API endpoint, and displayed in the ticket detail page as a new "Audit" tab showing timestamp, action, status, and error details.

## Included

**Backend — `services/control_api/routes/tickets.py`**
- After each of the 9 action endpoints returns its `ActionResult`, call `append_runtime_event()` with `event_type="action:<action-name>"`, `message="<action> ok"` or `"<action> failed: <stderr>"`, and `metadata_json={"ok": bool, "returncode": int}`.
- Add `GET /tickets/{ticket_id}/audit-log` endpoint that calls `list_runtime_events(db_path, ticket_id=ticket_id)` filtered to `event_type` starting with `"action:"`, returns a list of `AuditEvent`.

**Backend — `services/control_api/models/schemas.py`**
- Add `AuditEvent` Pydantic schema: `id`, `event_type`, `message`, `metadata` (dict), `created_at` (str ISO 8601).

**Backend — `services/control_api/main.py`**
- Resolve and inject `db_path` into `app.state` at startup (via `runtime_db.get_db_path()`) so action routes can access it.

**Frontend — `apps/dashboard/src/api/tickets.js`**
- Add `getAuditLog(id)` calling `GET /tickets/{id}/audit-log`.

**Frontend — `apps/dashboard/src/components/AuditLog.jsx`** (new file)
- Table component: columns timestamp, action (derived from `event_type`), status (ok/error badge), message.
- Fetches via `getAuditLog`, renders empty state when no events exist.

**Frontend — `apps/dashboard/src/pages/TicketDetailPage.jsx`**
- Add `"audit"` tab in the existing tab list.
- Render `<AuditLog ticketId={id} />` when that tab is active.

## Excluded
- User identity / authentication (no auth system exists).
- Client IP or browser metadata capture.
- Audit events for non-dashboard actions (e.g. automated step transitions inside `run_ticket.py`).
- Filtering, pagination, or search in the audit log UI.
- Any modification to the SQLite schema (the `runtime_events` table is already correctly structured).
- Changes to `subprocess_runner.py` or `run_ticket.py`.

## Acceptance criteria
- Every invocation of an action endpoint (approve-plan, request-plan-fix, approve-implementation, request-implementation-fix, run-next, commit, push, checkpoint, archive) inserts exactly one row into `runtime_events` with `event_type` prefixed `"action:"`.
- `GET /tickets/{ticket_id}/audit-log` returns only rows for that ticket with `event_type` starting with `"action:"`, ordered by `created_at` descending.
- The dashboard ticket detail page has an "Audit" tab; it renders a table with at least the columns: timestamp, action, status.
- After triggering an action (e.g. approve-plan) from the dashboard, refreshing the Audit tab shows the new event without a page reload.
- `AuditEvent` schema validation passes (Pydantic); the endpoint returns HTTP 200 with an empty list when no audit events exist for a ticket.
