All tests pass. Implementation is complete.

---

**Summary of changes (8 files):**

| File | Change |
|------|--------|
| `services/control_api/models/schemas.py` | +4 schemas: `WorkerInfo`, `RetryBlockedTicket`, `QueueEntry`, `RuntimeStatus` |
| `services/control_api/services/daemon_manager.py` | +5 functions: `get_workers`, `get_retry_blocked`, `get_intake_queue`, `get_last_error`, `get_runtime_status` |
| `services/control_api/routes/daemon.py` | +1 route: `GET /daemon/runtime-status` |
| `apps/dashboard/src/api/daemon.js` | +1 function: `getRuntimeStatus()` |
| `apps/dashboard/src/components/RuntimeStatusPanel.jsx` | NEW — 4-section panel (workers, retry/cooldown, intake queue, last error) polling at 5s |
| `apps/dashboard/src/pages/DaemonPage.jsx` | Integrated `RuntimeStatusPanel` |
| `tests/test_control_api_endpoints.py` | +4 pytest cases (daemon offline/online, intake queue, retry blocked) |
| `apps/dashboard/tests/DaemonPage.test.jsx` | Added `getBoardData` + `getRuntimeStatus` mocks to `beforeEach` |
| `apps/dashboard/tests/RuntimeStatusPanel.test.jsx` | NEW — 5 Vitest cases |

The new endpoint aggregates daemon online status, active workers, retry-blocked tickets, intake queue, last action timestamp, and last error from log — all served in one `GET /daemon/runtime-status` call polled every 5s by `RuntimeStatusPanel`.
