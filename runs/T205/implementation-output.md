## Summary

Implemented T205 strictly per the approved plan.

### Files modified
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx` — refactor only.
- `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` — adjusted existing assertions for the new layout, added new tests, added `COMPLETED_INTELLIGENCE_WITH_SIGNALS` fixture.

### Changes (completed-state branch only)
- Added a local `Disclosure` helper backed by a native `<details>`/`<summary>` (no new deps).
- Replaced the single grid with: a 10-field compact grid (Difficulty, Risk, Estimated cost, Recommended model, Plan review, Code review, Dependencies, Parallel safe, Autonomous execution, Last analyzed), a clamped `analysis_summary` paragraph with `title` for hover.
- Verbose data moved into `Show detailed analysis` (collapsed by default): model/plan/code review reasons, cost estimate details, queue rank + reason, complexity factors, dependency hints (full), full analysis summary.
- `Show raw intelligence data` (collapsed) renders only when `computed_signals_json` is present, showing pretty-printed JSON in a styled `<pre>`.
- Warning border: container gets `border-orange-300` when `risk_score >= 7` or either human review flag is true.
- All non-`completed` branches, header/advisory badge, polling, error handling, button states, and API calls are unchanged.

### Verifications
- `npm test -- TicketIntelligencePanel`: 25/25 pass (was 17 before; +8 new).
- Full dashboard suite: 16 failing tests across `TicketDetail.test.jsx`, `TicketDetailPage.test.jsx`, `RuntimeDashboardPage.test.jsx`, `DaemonActivityFeed.test.jsx` are **pre-existing** — confirmed by re-running the same files against the stashed baseline (same 16 failures).

### Limits / assumptions
- JSDOM does not hide `<details>` children when closed, so disclosed-state assertions check the `details.open` property and `closest('details')` rather than visibility.
- `line-clamp-3` relies on Tailwind 3.4's built-in support (no plugin needed); behavior visible only in the browser, not asserted in tests.
- No visual regression / Storybook coverage was added (out of plan scope).
- Did not run a browser dev server — this is a JSX-only refactor of a single panel; visual verification would require a running backend. The component is exercised end-to-end via the Vitest + RTL suite.
