289/289 Python tests pass. Both fixes are complete and all tests are green.

---

## Summary of changes

**Fix 1 — Logs tab continuous refresh (`TicketDetailPage.jsx`)**

Added `activeTabRef` (a ref that tracks the current tab) and a `useEffect` to keep it updated. In `fetchTicket`, added an `else if (activeTabRef.current === 'logs')` branch that deletes `tabContent.logs` on every poll cycle when the logs tab is active — regardless of whether the ticket state changed. This triggers the existing tab content `useEffect` to re-fetch logs on the next render.

**Fix 2 — Runtime state change tests (`tests/TicketDetailPage.test.jsx`)** (new file)

3 tests with a mocked `usePolling` (capturing the callback without calling it, to avoid double-fetches on re-renders):
- **invalidates tab content when ticket state changes** — verifies `getTicketState` is re-called after a state transition
- **preserves tab content when ticket state is unchanged** — verifies `getTicketState` call count doesn't increase after a same-state poll
- **re-fetches logs on each poll when logs tab is active** — verifies `getTicketLogs` is called again on every poll when the logs tab is active, even with no state change
