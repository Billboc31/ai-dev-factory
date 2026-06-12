Clean build. Implementation is complete.

---

**Summary of changes:**

**New: `apps/dashboard/src/lib/ticketColumns.js`**
- `COLUMN_DEFS` — 4-column definitions with id, label, and Tailwind color tokens
- `STATE_TO_COLUMN` — maps every known state string to one of 4 column ids (unknown states fall back to `queued`)
- `columnForState(state)` — single-call helper
- `STATE_BADGE_COLORS` + `stateBadgeClass(state)` — centralized badge color logic (moved from the old page local constant)

**New: `apps/dashboard/src/components/TicketPreviewPanel.jsx`**
- Slide-in drawer (fixed right, `z-50`) with backdrop
- Shows: ticket id, state badge, branch, issue number, last activity timestamp, last log, last error (fetched via `getTicketTimeline` on open)
- Navigation footer: "Open ticket" (Link), "Open GitHub issue" (rendered only when `issue_number` + optional `githubRepo` prop are both set), "Open PR (see ticket detail)"
- Close via `×` button or click-outside

**Modified: `apps/dashboard/src/pages/ProjectTicketsPage.jsx`**
- Table replaced with 4-column flex-row Kanban board
- Each ticket is a clickable `TicketCard` button — no direct navigation, opens `TicketPreviewPanel` instead
- `waiting_human` column cards have `ring-2 ring-orange-400` highlight
- Preserves 5 s polling, `ErrorBanner`, and `usePolling` logic unchanged
- All local `STATE_COLORS` / `stateBadgeClass` constants removed; imported from `ticketColumns.js`
