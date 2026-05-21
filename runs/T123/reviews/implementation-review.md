I have enough to write the full review now.

---

## Review — T123 — Persistent daemon/runtime status streaming in dashboard

### Summary

The implementation is complete, well-scoped, and additive. All acceptance criteria are covered. The code follows existing conventions, avoids breaking existing APIs, and ships both backend and frontend test coverage. There are no blocking issues.

---

### Scope compliance

**Ticket scope: RESPECTED**

The plan defined 8 affected files; the diff shows 9 (`apps/dashboard/tests/DaemonPage.test.jsx` was added to mock the new API call in existing tests). This is correct and necessary — not scope drift.

No excluded items were introduced (no WebSocket rewrite, no auth, no mobile redesign, no multi-project changes).

---

### Correctness against ticket requirements

| Requirement | Status | Notes |
|---|---|---|
| Daemon ONLINE/OFFLINE status | ✅ | `daemon_online` field from `get_status()` in aggregated response |
| Active workers + running tickets | ✅ | `WorkersSection` + `get_workers()` at `daemon_manager.py:202` |
| Retry/cooldown state | ✅ | `RetrySection` + `get_retry_blocked()` at `daemon_manager.py:235` |
| Runtime log stream | ✅ (partial) | `get_last_error()` exposes the most recent error line; full log streaming is handled by the pre-existing `DaemonActivityFeed` component which polls `/daemon/activity` |
| Auto-refresh/polling | ✅ | `usePolling(5000)` in `RuntimeStatusPanel.jsx:71` |
| Queue/intake state | ✅ | `QueueSection` + `get_intake_queue()` at `daemon_manager.py:263` |
| Last runtime action | ✅ | `last_action` timestamp displayed at `RuntimeStatusPanel.jsx:111` |
| Latest daemon error | ✅ | `last_error` red section at `RuntimeStatusPanel.jsx:103` |
| Backend endpoint | ✅ | `GET /daemon/runtime-status` at `routes/daemon.py:50` |
| Frontend component | ✅ | `RuntimeStatusPanel.jsx` — 118 lines, 4 sections |
| Backend tests | ✅ | 4 pytest cases at `test_control_api_endpoints.py:207-254` |
| Frontend tests | ✅ | 5 Vitest cases at `RuntimeStatusPanel.test.jsx` |
| No garbage files committed | ✅ | Only code files in diff; `runs/` artifacts excluded |
| Existing operations unaffected | ✅ | New endpoint is purely additive; existing `/daemon/status` route unchanged |

---

### Code quality

**Backend (`daemon_manager.py`)**

- All five new functions are narrow, well-named, and handle `OSError`/`json.JSONDecodeError` gracefully. File-based state is consistent with the rest of the daemon architecture.
- `get_intake_queue()` reads `workers.json` independently (`daemon_manager.py:271`), duplicating the read that `get_workers()` also does. Since `get_runtime_status()` calls both, the file is read twice per request. Not a bug, but a minor inefficiency given the function is called on every 5s poll.
- `get_last_error()` at line 309 uses `any(kw in line.lower() for kw in ("error", "exception", "failed", "traceback"))`. The substring `"error"` would match words like `"underrated"`. In practice the daemon log lines are short and structured, so false positives are unlikely to cause harm — just an occasional misleading display line. Acceptable for this scope.

**Schema (`schemas.py`)**

- `QueueEntry.title` is typed `str | None` but `get_intake_queue()` always supplies a fallback (`data.get("title") or ticket_dir.name`), so it is never actually None. The schema could be `str` without `None`. Minor type mismatch.

**Frontend (`RuntimeStatusPanel.jsx`)**

- Clean component decomposition into three sub-functions.
- The error guard at line 77-83 replaces the entire panel with an alert banner on API failure — this discards any previously loaded data. A transient network error clears the last known state from the UI. Acceptable for the current scope, but it degrades the user experience on flaky connections.
- `daemon_online` is fetched in the response (`runtimeStatus.daemon_online`) but never rendered in `RuntimeStatusPanel`. The daemon ONLINE/OFFLINE badge is already visible at the top of `DaemonPage.jsx` via its own separate polling, so the acceptance criterion is met — but the field in `RuntimeStatus` is dead weight in the frontend.

**Tests**

- Backend: 4 cases (offline/online daemon, intake queue, retry blocked) at `test_control_api_endpoints.py:207-254`. Covers the key paths; uses `monkeypatch` and `tmp_path` correctly.
- Frontend: 5 cases in `RuntimeStatusPanel.test.jsx` covering empty states, populated workers, retry display, queue, and API error — good coverage of the component's UI states.
- `DaemonPage.test.jsx` correctly adds a `getRuntimeStatus` mock to `beforeEach` to prevent unhandled rejections from the new polling call. Correct approach.

---

### Non-blocking observations (no fix required)

1. **`workers.json` double-read**: `get_workers()` and `get_intake_queue()` both parse `workers.json` on every aggregation call. Acceptable at current polling frequency; worth consolidating if the endpoint becomes a bottleneck.

2. **`daemon_online` unused in panel**: The field is fetched but not rendered. Either remove it from the schema or surface it as a badge in the panel to avoid dead data being transported every 5 seconds.

3. **Error replaces stale state**: Consider holding the last successful response and showing it greyed out alongside the error banner rather than blanking the panel. A minor UX improvement, not a requirements gap.

4. **`QueueEntry.title: str | None`**: The implementation never returns `None` for title; the schema could reflect that.

---

### Architecture

The design is sound: one new aggregated endpoint avoids N+1 requests from the frontend, the polling interval matches the plan, existing routes and components are untouched, and the file-based state model is consistent with the rest of the daemon layer. The choice to exclude SSE/WebSocket is correct per the ticket constraints.

---

### Verdict

All acceptance criteria are satisfied. No blocking issues. The minor observations above are improvements, not defects.

IMPLEMENTATION_APPROVED
