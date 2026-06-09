All 7 sidebar tests pass individually. The OOM error only appears when running all test files together — it's a pre-existing infrastructure constraint, not caused by the new tests.

Here's a summary of what was done:

---

**Fix 1 — React Fragment key (`ProjectTicketsPage.jsx`)**
- Added `import React` at the top
- Replaced `<>` / `</>` in the `tickets.map()` with `<React.Fragment key={t.ticket_id}>` / `</React.Fragment>`
- Removed the now-redundant `key` prop from the inner `<tr>` and `<ConflictDetail>`

**Fix 2 — New tests (3 files created)**

| File | Tests | What it covers |
|---|---|---|
| `tests/ProjectDashboardPage.test.jsx` | 9 | Project heading, daemon running/stopped status, Start/Stop/Restart buttons, `startDaemon`/`stopDaemon` called with `projectId`, host command banner, error banner, stack badge, active ticket count |
| `tests/ProjectSidebar.test.jsx` | 7 | Project list renders, `onSelect` called, per-project nav present when `activeProject` set, absent when not, nav link hrefs correct, global nav, import link |
| `tests/ProjectRouting.test.jsx` | 5 | Smoke test for `/projects/:projectId/{dashboard,tickets,worktrees,logs}`, `projectId` from URL params not hardcoded |

All 21 new tests pass. The pre-existing 5 failures (`DaemonActivityFeed` + 4 `RuntimeDashboardPage` label mismatches) are unchanged.
