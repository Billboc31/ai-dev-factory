Everything looks correct. Here's a summary of all changes made:

**Backend fixes (blocking):**

- `models/schemas.py`: Added `last_log: str | None = None` to `TicketSummary`
- `services/artifact_reader.py`: Added `_last_log_line()` helper (reads last non-empty line of `runtime.log`), wired it into `list_tickets()`, and added `get_ticket_state()` returning raw `state.json` dict
- `routes/tickets.py`: Added `GET /tickets/{id}/state` endpoint

**Frontend fixes (blocking + minor):**

- `src/api/tickets.js`: Added `getTicketState` export
- `src/pages/TicketDetailPage.jsx`:
  - Overview tab now fetches full `state.json` via `getTicketState` (same lazy-load pattern as other tabs)
  - `setTabContent({})` added to `[id]` effect — fixes stale tab cache on navigation
  - `refreshTicket()` now propagates errors via `setError` instead of swallowing them
  - Commit and Push buttons now have `onSuccess={refreshTicket}`
- `src/pages/DaemonPage.jsx`: Added `formatUptime()` — shows duration (e.g., "3h 42m") instead of absolute timestamp

**Tests:** 38 tests pass (added 1 new test verifying overview tab calls `getTicketState` and renders `state.json` fields).
