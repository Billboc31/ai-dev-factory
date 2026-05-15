All tests pass. Here's a summary of what was implemented:

---

## Files created/modified

### Backend
| File | Change |
|---|---|
| `services/control_api/models/schemas.py` | Added `last_heartbeat`, `current_ticket` to `DaemonStatus`; added `DaemonActivity` model |
| `services/control_api/services/daemon_manager.py` | Redirects daemon stdout to `runs/daemon.log`; adds `get_activity()`; enriches `get_status()` with `last_heartbeat` (from log mtime) and `current_ticket` (scanned from runs/) |
| `services/control_api/routes/daemon.py` | Added `GET /daemon/activity?lines=N` endpoint |

### Frontend
| File | Change |
|---|---|
| `apps/dashboard/src/hooks/usePolling.js` | **New** — `setInterval`/`clearInterval` hook; calls immediately on mount; restarts on key change; no zombie leaks |
| `apps/dashboard/src/api/daemon.js` | Added `getDaemonActivity(lines)` |
| `apps/dashboard/src/components/DaemonActivityFeed.jsx` | **New** — polls `GET /daemon/activity` every 5s; renders log lines with terminal-style styling |
| `apps/dashboard/src/pages/TicketsPage.jsx` | Replaced manual `useEffect` with `usePolling(5s)`; shows "Updated at HH:MM:SS" indicator |
| `apps/dashboard/src/pages/TicketDetailPage.jsx` | Polls ticket state every 5s; invalidates tab cache on state change; restarts polling on ticket navigation |
| `apps/dashboard/src/pages/DaemonPage.jsx` | Reduced polling from 30s → 5s via `usePolling`; added `DaemonActivityFeed`; displays `current_ticket` and `last_heartbeat` |

### Tests
| File | Change |
|---|---|
| `apps/dashboard/tests/usePolling.test.js` | **New** — 7 tests covering lifecycle, cleanup, key-restart, no-zombie |
| `apps/dashboard/tests/DaemonActivityFeed.test.jsx` | **New** — 4 tests covering rendering, empty state, error handling |
| `apps/dashboard/tests/DaemonPage.test.jsx` | Added `getDaemonActivity` mock to existing `beforeEach` |
| `tests/test_control_api_endpoints.py` | 3 new tests for `GET /daemon/activity` |
| `tests/test_control_api_subprocess.py` | 5 new tests for `get_activity()` and enriched `get_status()` |

**Results: 34/34 Python tests pass, 49/49 JS tests pass.**
