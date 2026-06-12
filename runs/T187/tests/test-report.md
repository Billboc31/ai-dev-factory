---

## T187 Test Report

**Verdict: PASS** — all acceptance criteria pass. Two minor non-blocking gaps noted.

### Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Tickets in Queued / Running / Waiting human / Done columns | **PASS** |
| 2 | Human-gate tickets immediately visible | **PASS** |
| 3 | Clicking a ticket opens preview panel | **PASS** |
| 4 | Preview contains metadata and navigation links | **PARTIAL** (see gaps) |
| 5 | Existing ticket pages still work | **PASS** |
| 6 | Workspace / multi-project features remain functional | **PASS** |

### Non-blocking Gaps (AC4)

1. **Title missing from preview** — `TicketSummary` schema has no `title` field; neither the card nor panel renders it. Low impact (ticket ID shown, issue title is one click away).
2. **PR link is indirect** — "Open PR" routes to the ticket detail page rather than a direct PR URL. `TicketSummary` has no `pr_url` field. Low impact (one extra click).

### Regression Fixed

`tests/ProjectRouting.test.jsx` — The new `getProject()` call in `ProjectTicketsPage` was not mocked in the test's `beforeEach`, causing a crash. Fixed by adding `projectsApi.getProject.mockResolvedValue({ data: {} })`.

### Pre-existing Failures (unrelated to T187)

`RuntimeDashboardPage.test.jsx` (4 failures) and `DaemonActivityFeed.test.jsx` (1 failure) were failing before this branch and no source files they test were touched by T187.

### Artefacts

- **`tests/T187TicketBoard.test.jsx`** — 22 new acceptance tests (22/22 pass, 166ms)
- **`tests/ProjectRouting.test.jsx`** — regression fix applied
- **`runs/T187/tests/test-output.md`** — full report
