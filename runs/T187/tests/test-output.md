# T187 — Tester Report

## Summary

**Verdict: PASS with minor gaps noted**

22/22 T187 acceptance tests pass. One regression in the test suite was found and fixed. Two minor implementation gaps relative to the ticket's preview spec are documented below (non-blocking).

---

## Acceptance Criteria Results

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Tickets displayed in Queued / Running / Waiting human / Done columns | **PASS** | Four columns rendered; status mapping centralized in `ticketColumns.js` |
| 2 | Human-gate tickets immediately visible | **PASS** | `ring-2 ring-orange-400` highlight applied to `waiting_human` cards |
| 3 | Clicking a ticket opens a preview panel | **PASS** | Right-side drawer opens on card click; closes on backdrop click or × |
| 4 | Preview contains ticket metadata and navigation links | **PARTIAL PASS** | All fields except title and direct PR URL (see gaps below) |
| 5 | Existing ticket pages still work | **PASS** | `/projects/:projectId/tickets/:id` routes to `TicketDetailPage` unchanged |
| 6 | Workspace and multi-project features remain functional | **PASS** | `ProjectSidebar` and project switching intact |

---

## Implementation Gaps (non-blocking)

### Gap 1 — Title not shown in preview panel

The spec lists **title** as a required preview field. `TicketSummary` (the API schema for `listTickets`) does not include a `title` field. Neither the ticket card nor the preview panel renders a title.

- Impact: Minor — the ticket ID is shown; the linked issue title is one click away.
- Recommendation: Add `title: str | None` to `TicketSummary` in `schemas.py` and surface it in the preview header and card.

### Gap 2 — Linked PR is indirect

The preview shows "Pull request" → "See ticket detail" (an internal route) instead of a direct PR URL. The action button reads "Open PR (see ticket detail)". `TicketSummary` has no `pr_url` field.

- Impact: Minor — requires one extra click through the detail page to reach the PR.
- Recommendation: Add `pr_url: str | None` to `TicketSummary` and link directly when present.

---

## Regression Fixed

**File**: `tests/ProjectRouting.test.jsx`

**Test**: `/projects/:projectId/tickets renders the tickets page heading`

**Root cause**: The second coder iteration added a `getProject(projectId)` call to `ProjectTicketsPage`. The test's `vi.mock('../src/api/projects')` auto-mocked the module, leaving `getProject` returning `undefined`. Calling `.then()` on `undefined` crashed the component with `TypeError: Cannot read properties of undefined (reading 'then')`.

**Fix applied**: Added `projectsApi.getProject.mockResolvedValue({ data: {} })` to the test's `beforeEach`.

---

## Pre-existing Failures (not caused by T187)

These failures existed on `main` before T187 — none of these source files were modified by this branch:

| Test file | Failures | Cause |
|-----------|----------|-------|
| `RuntimeDashboardPage.test.jsx` | 4/9 | Tests reference removed UI elements (`Sandbox Runs` section, `Open Logs` button) |
| `DaemonActivityFeed.test.jsx` | 1/4 | Test asserts a `lines` query param the component no longer sends |

---

## Commands Executed

```bash
# Full suite baseline (pre-fix, pre T187 test file)
npx vitest run
# Result: 5 failed (pre-existing), 81 passed; OOM errors on RuntimeDashboardPage worker

# T187 acceptance tests
npx vitest run tests/T187TicketBoard.test.jsx
# Result: 22/22 pass (166ms)

# T187 + routing regression fix + all ticket-related tests
npx vitest run tests/T187TicketBoard.test.jsx tests/ProjectRouting.test.jsx \
              tests/ProjectSidebar.test.jsx tests/TicketDetailPage.test.jsx \
              tests/TicketDetail.test.jsx tests/TicketList.test.jsx
# Result: 52/52 pass
```

---

## Artefacts Produced

| File | Description |
|------|-------------|
| `apps/dashboard/tests/T187TicketBoard.test.jsx` | 22 new acceptance tests (AC1–AC5 + status mapping) |
| `apps/dashboard/tests/ProjectRouting.test.jsx` | Regression fix: added missing `getProject` mock |
| `runs/T187/tests/test-output.md` | This report |
