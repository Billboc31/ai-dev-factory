## Objective

Expose the per-ticket retry state (`failure_class`, `retry_count`, `cooldown_until`) and the last runtime error through the control API and the dashboard, so operators can see why a ticket is blocked and when it will be retried.

## Included

**Backend — `services/control_api/`**

- `models/schemas.py`: add `RetryInfo` Pydantic model (`failure_class: str | None`, `retry_count: int`, `cooldown_until: str | None`); extend `TicketSummary` with `retry_info: RetryInfo | None`; extend `TimelineResponse` with `retry_info: RetryInfo | None` and `last_error: str | None`.
- `services/artifact_reader.py`: add `read_retry_state(ticket_id)` function that reads `runs/{ticket_id}/retry-state.json` and returns a `RetryInfo` (or `None` if file absent); add `read_last_error(ticket_id)` that extracts the last `ERROR` line from `runs/{ticket_id}/runtime.log` (returns `str | None`).
- `routes/tickets.py`: populate the new fields in `GET /tickets/{id}` and `GET /tickets/{id}/timeline` by calling the two new reader functions.

**Frontend — `apps/dashboard/src/`**

- `pages/TicketDetailPage.jsx`: in the **overview** tab, add a "Retry status" section that renders `retry_count`, `failure_class`, and `cooldown_until` when `retry_info` is present; add a "Last error" line when `last_error` is present.
- `components/WorkflowTimeline.jsx`: when a step has status `failed` and `retry_info` is available, show a short inline annotation (e.g. `"attempt 3 — planner_invalid"`).

## Excluded

- Creating a new dedicated retry-info API endpoint (the data is added to existing endpoints).
- Persisting or modifying retry-state.json (read-only exposure).
- Adding error history / audit log beyond the last error line.
- Any changes to how retry state is written by the runtime agents.
- Changes to `BoardPage`, `DaemonPage`, or `ProjectMapPage`.
- UI changes to anything outside `TicketDetailPage` and `WorkflowTimeline`.

## Acceptance criteria

- `GET /api/tickets/{id}` response includes a `retry_info` object (`failure_class`, `retry_count`, `cooldown_until`) when `runs/{id}/retry-state.json` exists, and `null` otherwise.
- `GET /api/tickets/{id}/timeline` response includes the same `retry_info` and a `last_error` string (last ERROR-level log line from `runtime.log`, or `null` if none).
- The dashboard **overview** tab of a ticket in a blocked/retrying state shows retry count, failure class, and cooldown time.
- The dashboard **overview** tab shows the last error message when one exists.
- `WorkflowTimeline` annotates failed steps with the retry attempt number and failure class when `retry_info` is present.
- Existing API contract is unchanged for tickets without a `retry-state.json` (all new fields are nullable/optional).
- No new top-level API routes are introduced.
