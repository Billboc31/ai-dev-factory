The plan is written to `runs/T123/plan.md`. Here's a summary:

---

## Objective

Add a `GET /daemon/runtime-status` aggregated endpoint + a `RuntimeStatusPanel` React component that polls it every 5s to display daemon state, active workers, retry-blocked tickets, intake queue, and last error — all without a page reload.

## Key design decisions

**Why a new endpoint instead of extending `/daemon/status`?**  
`/daemon/status` has existing callers; breaking its schema would require coordinated frontend changes. A new endpoint is additive and leaves existing routes untouched.

**Why stay with polling (no SSE)?**  
The ticket explicitly excludes "full websocket/event-bus architecture rewrite". The existing `usePolling` hook at 5s already matches the stated "near real-time" goal. SSE would be future T-work.

**Files affected (8 total):**

| File | Change |
|------|--------|
| `services/control_api/models/schemas.py` | +4 schemas: WorkerInfo, RetryBlockedTicket, QueueEntry, RuntimeStatus |
| `services/control_api/services/daemon_manager.py` | +5 functions: get_workers, get_retry_blocked, get_intake_queue, get_last_error, get_runtime_status |
| `services/control_api/routes/daemon.py` | +1 route: GET /daemon/runtime-status |
| `apps/dashboard/src/api/daemon.js` | +1 function: getRuntimeStatus() |
| `apps/dashboard/src/components/RuntimeStatusPanel.jsx` | NEW — 4-section status panel |
| `apps/dashboard/src/pages/DaemonPage.jsx` | Integrate RuntimeStatusPanel + new usePolling call |
| `tests/test_control_api_endpoints.py` | +4 pytest cases |
| `apps/dashboard/tests/RuntimeStatusPanel.test.jsx` | NEW — 5 Vitest cases |
