Now I have enough to write a precise plan.

## Objective

Replace the table view in `ProjectTicketsPage.jsx` with a 4-column Kanban board (Queued / Running / Waiting Human / Done), add a slide-in ticket preview drawer triggered by card click, and centralize status-to-column mapping in a dedicated utility.

## Included

**New file — `apps/dashboard/src/lib/ticketColumns.js`**
- Export a `COLUMN_DEFS` array (4 entries: queued, running, waiting_human, done) with id, label, and color tokens.
- Export a `STATE_TO_COLUMN` map assigning every known state string to one of the 4 column ids:
  - queued: `QUEUED`, `READY`, `PLANNED`, `PLAN_FIX_REQUIRED`, `IMPLEMENTATION_FIX_REQUIRED`
  - running: `RUNNING`, `IMPLEMENTING`, `TESTING`, `REVIEWING`, `PLAN_APPROVED`, `IMPLEMENTATION_APPROVED`, `CONFLICT_RESOLVING`
  - waiting_human: `PLAN_REVIEW_NEEDED`, `IMPLEMENTATION_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLVED_REVIEW_NEEDED`
  - done: `TEST_COMPLETE`, `COMPLETE`, `COMPLETED`, `MERGED`, `ARCHIVED`, `FAILED`, `CONFLICT_RESOLUTION_FAILED`
- Export a helper `columnForState(state)` that returns the column id (fallback: `queued`).

**New file — `apps/dashboard/src/components/TicketPreviewPanel.jsx`**
- Slide-in drawer fixed to the right side, toggled by a `ticket` prop (null = closed).
- Displays from the `TicketSummary` object available from the list endpoint:
  - ticket id, current state (color-coded badge), branch
  - issue number (linked to GitHub issue URL using project's GitHub repo, if available)
  - latest activity (`updated_at` formatted) and last log line (`last_log`)
  - last error: fetched from `GET /projects/:projectId/tickets/:id/timeline` when the drawer opens, showing `last_error` from `TimelineResponse`; loading spinner while fetching
  - linked PR: placeholder row "PR — see ticket detail" with link to ticket detail page (PR number not in list API; avoid a separate fetch here)
  - worktree path: not available in list API — show placeholder "Open worktree (not yet available)"
- Navigation buttons in the drawer footer:
  - "Open ticket" → `/projects/:projectId/tickets/:id`
  - "Open GitHub issue" → external link (only rendered when `issue_number` is set)
  - "Open PR" → link to ticket detail page PR tab (placeholder until PR number is in list API)
- Close button (×) and click-outside-to-close behavior.

**Modified file — `apps/dashboard/src/pages/ProjectTicketsPage.jsx`**
- Remove the HTML `<table>` rendering entirely.
- Import `COLUMN_DEFS`, `columnForState` from `ticketColumns.js`.
- After polling, bucket each ticket into its column using `columnForState(ticket.state)`.
- Render a horizontal 4-column grid (CSS flex row, each column flex-shrink-0 with a fixed width and scroll); preserve auto-polling every 5 s.
- Each ticket card shows: ticket id (non-navigating, clicking opens preview), state badge, branch, last_log truncated.
- `waiting_human` column cards get a visual highlight (ring or bold border) to surface human-gate tickets.
- Clicking any card sets `previewTicket` state → renders `<TicketPreviewPanel>`.
- Remove `ConflictDetail` table row (conflict info moves to preview drawer via the timeline fetch).
- Keep `ErrorBanner` and polling logic unchanged.

**No changes to:**
- `BoardPage.jsx` (separate global board, orthogonal scope)
- `TicketDetailPage.jsx` (detail pages remain intact)
- Any backend service, API schema, or routing

## Excluded

- Adding title field to the list API or `TicketSummary` schema (title is not in the current list endpoint; workaround uses ticket id + state).
- Surfacing the PR number in the preview without an extra API call (deferred — add to list API in a follow-up).
- Worktree path integration (placeholder UI only, wiring deferred).
- Modifying `BoardPage.jsx` or the daemon-board API path.
- Any changes to deployment, runtime, or test infrastructure.
- Dark-mode or mobile-responsive layout beyond the existing Tailwind baseline.

## Acceptance criteria

- `ProjectTicketsPage.jsx` renders exactly 4 columns: Queued, Running, Waiting Human, Done.
- Every ticket state maps to exactly one column via `columnForState`; unknown states fall into Queued.
- Tickets in the `waiting_human` column are visually distinct (highlighted border/ring) without extra user action.
- Clicking a ticket card opens the preview drawer without navigating away from the board.
- The preview drawer shows: ticket id, state badge, branch, last log, formatted timestamp, and — after the timeline fetch resolves — last error (or "none").
- "Open ticket" link in the drawer navigates to the existing `TicketDetailPage`.
- "Open GitHub issue" link is visible and correct when `issue_number` is set; absent when not.
- Closing the drawer (× button or outside click) returns to the board with no navigation.
- `TicketDetailPage` is still reachable and fully functional.
- The board polls every 5 s; the preview drawer refreshes its timeline data when reopened.
- `STATE_TO_COLUMN` and `COLUMN_DEFS` are the single source of truth — `ProjectTicketsPage` and `TicketPreviewPanel` import from `ticketColumns.js`, not from local constants.
