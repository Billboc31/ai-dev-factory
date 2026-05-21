All 5 changed files are within scope (`runs/T120/runtime.log` is the live log file that was already modified, not something I changed). Implementation is complete.

---

**Summary of changes:**

**Backend — `services/control_api/`**

- `models/schemas.py`: Added `RetryInfo` model (`failure_class`, `retry_count`, `cooldown_until`); extended `TicketSummary` with `retry_info: RetryInfo | None`; extended `TimelineResponse` with `retry_info: RetryInfo | None` and `last_error: str | None`.

- `services/artifact_reader.py`: Added `_read_retry_state(run_dir)` (reads `retry-state.json`, returns `RetryInfo | None`) and `_read_last_error(run_dir)` (scans `runtime.log` in reverse for last `ERROR` line). Updated `get_ticket()` and `get_ticket_timeline()` to call both helpers.

**Frontend — `apps/dashboard/src/`**

- `pages/TicketDetailPage.jsx`: Added `OverviewTab` component rendering a "Retry status" card (`retry_count`, `failure_class`, `cooldown_until`) and a "Last error" card from `TimelineResponse`. The overview tab now fetches from the timeline endpoint. Overview is also included in the polling auto-refresh list alongside `timeline` and `logs`.

- `components/WorkflowTimeline.jsx`: Failed steps annotated with `attempt N — failure_class` when `retry_info` is present on the timeline.
