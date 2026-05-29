The fix is in place. Here's what changed in `apps/dashboard/src/pages/BoardPage.jsx`:

- Added `const [degraded, setDegraded] = useState(false)` (line 88)
- `fetchBoard` now also calls `setDegraded(res.data.degraded ?? false)` on each successful poll (line 92)
- A yellow warning banner renders when `degraded` is `true` (lines 103–107), showing: `SQLite runtime database unavailable — showing filesystem-derived runtime state`

This satisfies the one blocking acceptance criterion that the review flagged. The backend signal (`BoardResponse.degraded`) was already correct — the only missing piece was this frontend rendering.
