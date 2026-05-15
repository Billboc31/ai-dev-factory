The pre-existing failure confirmed. All 343 other Python tests pass, all 52 frontend tests pass.

---

## Summary

Implementation complete. Files created/modified:

**Backend (3 files modified):**
- `services/control_api/models/schemas.py` — added `TimelineStep` and `TimelineResponse` Pydantic models
- `services/control_api/services/artifact_reader.py` — added `get_ticket_timeline()` with a state→step mapping table; pure projection from `state.json` + optional `retry-state.json`, no second state machine
- `services/control_api/routes/tickets.py` — added `GET /tickets/{ticket_id}/timeline`

**Frontend (3 files modified, 1 created):**
- `apps/dashboard/src/api/tickets.js` — added `getTicketTimeline(id)`
- `apps/dashboard/src/components/WorkflowTimeline.jsx` — new stepper component (7 fixed steps, status icons, agent label, human gate banner, last event)
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — `timeline` tab added as default; live-refresh on every poll (like logs)

**Tests (1 created, 2 updated):**
- `tests/test_ticket_timeline.py` — 9 cases: 404, INIT, PLAN_REVIEW_NEEDED, PLAN_APPROVED, IMPLEMENTATION_REVIEW_NEEDED, IMPLEMENTATION_FIX_REQUIRED, TEST_COMPLETE (no retry / with retry), last_event
- `apps/dashboard/tests/TicketDetail.test.jsx` — added `getTicketTimeline` mock, updated overview tab test to click the tab first
- `apps/dashboard/tests/TicketDetailPage.test.jsx` — added mock, updated polling tests to track the now-default timeline tab
