Everything looks correct. Here's a summary of all changes made:

---

## Changes made

**Backend — 3 files modified**

- `services/control_api/models/schemas.py` — Added `AuditEvent` Pydantic model (`id`, `event_type`, `message`, `metadata`, `created_at`).

- `services/control_api/main.py` — Added `tools/agent_runner` to sys.path and imported `runtime_db`, then stored `app.state.db_path = _runtime_db.get_db_path()` in `create_app()`.

- `services/control_api/routes/tickets.py` — Added `runtime_db` import (same sys.path pattern), `_db_path()` / `_log_action()` helpers, audit logging on all 9 action endpoints, and `GET /tickets/{ticket_id}/audit-log` endpoint filtering events by `event_type` prefix `"action:"`.

**Frontend — 3 files modified/created**

- `apps/dashboard/src/api/tickets.js` — Added `getAuditLog(id)` calling `GET /tickets/{id}/audit-log`.

- `apps/dashboard/src/components/AuditLog.jsx` *(new)* — Self-fetching table component with timestamp, action (stripped of `action:` prefix), ok/error badge, and message columns. Renders an empty state when no events exist.

- `apps/dashboard/src/pages/TicketDetailPage.jsx` — Added `'audit'` to `TABS`, imported `AuditLog`, and renders `<AuditLog ticketId={id} />` when that tab is active (outside the tabLoading/TAB_FETCHERS flow, so it manages its own fetch lifecycle).
