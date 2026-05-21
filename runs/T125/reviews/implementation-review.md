I have a complete picture of the implementation after the fix. Let me write the review.

---

# Review — T125: Project-scoped runtime APIs and daemon isolation (retry)

## Summary

The previous blocking issue has been correctly resolved. All three non-blocking observations were also addressed. The implementation is complete and consistent throughout.

---

## Blocking issue resolution

### `TicketDetailPage` project scoping — FIXED

`App.jsx:12` exports `ActiveProjectContext` and wraps `<Routes>` with `<ActiveProjectContext.Provider value={activeProject}>` at line 51. `TicketDetailPage.jsx:4,62` imports and consumes it via `useContext`. Every API call in the detail page — tab fetchers, `fetchTicket`, `refreshTicket`, all workflow action buttons, all git/runtime buttons, and `<AuditLog>` — now receives `projectId`. This fully closes the correctness gap.

---

## Non-blocking fixes — all applied

**`getDaemonActivity` parameter order** — corrected to `(projectId, lines = 50)` at `api/daemon.js:8`, consistent with all other functions. `DaemonActivityFeed.jsx:10` updated to match.

**`_project_worktrees_dir` wrapper** — removed. All 18 usages in `routes/tickets.py` now call `resolve_worktrees_dir(project_root)` directly.

---

## Acceptance criteria assessment

| Criterion | Status |
|---|---|
| 404 for unknown `project_id` | PASS — `dependencies.py:16` |
| Independent daemon status per project | PASS — isolated PID files, confirmed by tests |
| Tickets scoped to project root | PASS — `artifact_reader.list_tickets(project_root)` |
| Project-map scoped per project | PASS |
| Legacy routes still work | PASS — legacy routers preserved at `app.state.project_root` |
| Switching project refreshes state | PASS — `usePolling(cb, delay, projectId)` restarts interval on key change |
| Tests validate isolation with two roots | PASS — `test_project_scoped_routes.py`, `test_project_isolation.py` |
| Runtime artifacts not duplicated | PASS — all paths derived from passed `project_root` |
| Existing single-project workflows | PASS — `null` projectId falls back to legacy routes |

---

## Code quality

No regressions introduced. The fix is minimal: `createContext` + one provider wrap + one `useContext` call. The `ProjectRegistry.from_single_root` fallback and `_pfx(null)` short-circuit preserve backward compatibility cleanly. The test suite structure is solid — two isolated `tmp_path` fixtures, real filesystem reads, no mock leakage.

---

## Acknowledged gap (out of scope)

The audit log reads from `app.state.db_path`, a single shared SQLite database. `/{project_id}/tickets/{ticket_id}/audit-log` filters only by `ticket_id`, not by project. This was documented in the previous review and remains out of scope per the ticket definition.

---

IMPLEMENTATION_APPROVED
