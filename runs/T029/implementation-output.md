All 37 tests pass. Here's a summary of the changes made:

**`apps/dashboard/src/pages/TicketDetailPage.jsx`**
- Added `'artifacts'` to the `TABS` array
- Added `artifacts: (id) => api.getTicketArtifacts(id)` to `TAB_FETCHERS`
- Added `renderContent()` helper that JSON-stringifies non-string content (handles the array/object artifact response correctly)
- `refreshTicket()` now clears `tabContent` so tabs re-fetch after a workflow action (fixes the cache staleness issue)

**`apps/dashboard/src/pages/TicketsPage.jsx`**
- Added "Last Log" column header
- Added `t.last_log` cell in each row (truncated with `title` tooltip for long entries)
- Updated empty-state `colSpan` from 4 → 5

**`apps/dashboard/tests/TicketDetail.test.jsx`**
- Added test verifying the artifacts tab fetches and renders artifact content

**`apps/dashboard/tests/TicketList.test.jsx`**
- Updated mock data to include `last_log`
- Added test verifying the "Last Log" column header and content are rendered
