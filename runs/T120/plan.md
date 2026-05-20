The plan is written. Here's a summary of what it covers:

---

**T120 — Implementation Plan**

**Problem**: The backend already tracks retry state (`retry-state.json`) and last error (`state.json`), but neither is exposed in the dashboard or API.

**3 files, 4 steps:**

| File | Change |
|------|--------|
| `services/control_api/models/schemas.py` | Add `RetryStatus` model; extend `TimelineResponse` with `retry_status` and `last_error` |
| `services/control_api/services/artifact_reader.py` | Add `_read_retry_state()` with cooldown computation; wire into `get_ticket_timeline()` |
| `apps/dashboard/src/components/WorkflowTimeline.jsx` | Render retry banner (stopped/cooldown/failed) and `last_error` block |

**Key decisions:**
- Extending the existing `/timeline` endpoint rather than adding a new one — avoids an extra polling call
- All new API fields are optional with `None` defaults — fully backwards-compatible
- No new routes, no DB changes, no daemon changes

**Out of scope**: retry history, reset action, board view, daemon changes.
