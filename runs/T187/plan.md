I have enough context to write the plan.

---

## Objective

Rework `ProjectTicketsPage` into a 4-column board (Queued / Running / Waiting human / Done) derived from ticket state, and add a lightweight side-panel preview that opens when a ticket card is clicked, exposing metadata and navigation links.

## Included

**Frontend — new file**
- `apps/dashboard/src/constants/ticketColumns.js`: single source of truth mapping every known ticket state to one of four column IDs (`queued`, `running`, `waiting_human`, `done`). Unknown states fall back to `queued`. Exports the four column definitions (id, label, color tokens).

**Frontend — new component**
- `apps/dashboard/src/components/TicketPreviewPanel.jsx`: slide-over / fixed right-panel showing:
  - ticket_id, state badge
  - branch (mono)
  - worktree path (placeholder label if absent from data)
  - last_log (latest activity line)
  - last error (from `retry_info` or `conflict_status`)
  - GitHub issue link if `issue_number` is set
  - PR link if `pr_number` is available (see backend below)
  - "Open ticket page" internal link
  - Close button (Escape key + click-outside also close)

**Frontend — modify `ProjectTicketsPage.jsx`**
- Replace the flat table with a horizontal 4-column board layout (flex row, overflow-x scroll).
- Each column renders a header (label + item count) and a vertical stack of ticket cards.
- Ticket card shows: ticket_id, state badge, branch, last_log truncated. Cards that are in `waiting_human` get an `ACTION NEEDED` ring.
- Clicking any card opens `TicketPreviewPanel` for that ticket (no navigation change).
- Existing `ConflictDetail` expansion is removed from the table; conflict info moves into the preview panel.
- Polling interval and error handling remain unchanged (5 s, `usePolling`).

**Backend — `services/control_api/models/schemas.py`**
- Add `title: str | None = None` and `pr_number: int | None = None` to `TicketSummary`.

**Backend — ticket list endpoint**
- Populate `title` from ticket storage if available (e.g., stored issue title or derived from ticket metadata). If the storage does not carry a title, leave `null`; the frontend falls back to `ticket_id`.
- Populate `pr_number` from ticket state (PR number field, if stored). Leave `null` if absent; the frontend omits the PR link.

**State-to-column mapping (implemented in `ticketColumns.js`)**

| Column | States |
|--------|--------|
| `queued` | `INIT`, `PLAN_APPROVED`, `IMPLEMENTATION_APPROVED`, `PLAN_FIX_REQUIRED`, `IMPLEMENTATION_FIX_REQUIRED`, and any unrecognized state |
| `running` | `RUNNING`, `CONFLICT_RESOLVING` |
| `waiting_human` | `PLAN_REVIEW_NEEDED`, `IMPLEMENTATION_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLVED_REVIEW_NEEDED` |
| `done` | `TEST_COMPLETE`, `COMPLETE`, `FAILED`, `CONFLICT_RESOLUTION_FAILED` |

## Excluded

- Changes to `BoardPage.jsx` (daemon board) — that page and its backend service remain untouched.
- Changes to `TicketDetailPage.jsx` — full detail pages continue to work as-is.
- Changes to the global `TicketsPage.jsx` (non-project-scoped view).
- Redesign of workspace, multi-project, or deployment/runtime UI.
- Worktree path integration beyond a static placeholder in the preview panel.
- Adding review-action buttons (approve/reject) inside the preview panel.
- Any new backend field beyond `title` and `pr_number` on `TicketSummary`.

## Acceptance criteria

- `ProjectTicketsPage` renders exactly four columns: Queued, Running, Waiting human, Done.
- Every ticket appears in exactly one column determined by `ticketColumns.js`.
- Tickets in `waiting_human` column are visually distinct (ring or accent color).
- Clicking a ticket card opens `TicketPreviewPanel` without navigating away from the board.
- Preview panel shows: ticket_id, state, branch, last activity, last error, GitHub issue link (when `issue_number` present), PR link (when `pr_number` present), and an "Open ticket page" link.
- Pressing Escape or clicking outside the panel closes it.
- Existing routes `/projects/:projectId/tickets/:id` still load `TicketDetailPage` correctly.
- Multi-project navigation (switching projects) still works; board refreshes for the new project.
- No regression on the daemon board (`/board` or `/projects/:id/daemon`).
