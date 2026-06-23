Now I have enough information to write the plan.

## Objective
Restructure `apps/dashboard/src/components/TicketIntelligencePanel.jsx` so the completed-state view is compact and scannable by default, with verbose reasoning and raw debug data tucked into collapsible sections. No backend, scheduler, rules, readiness, dispatcher, or analyzer behavior changes.

## Included

- **`apps/dashboard/src/components/TicketIntelligencePanel.jsx`** — refactor the `status === 'completed'` rendering branch:
  - Introduce two local `useState` toggles: `showDetails` (default `false`) and `showRaw` (default `false`).
  - **Compact summary block** (always visible when completed). A two-column responsive grid containing only:
    - `Difficulty` — `ScoreBadge` (existing helper).
    - `Risk` — `ScoreBadge` (existing helper).
    - `Estimated cost` — `$min – $max currency` short form (drop reason text from this row).
    - `Recommended model` — model name badge only (no reason in compact view).
    - `Human plan review` — `BoolBadge` `Required` / `Not required` only (no reason in compact view).
    - `Human code review` — `BoolBadge` only (no reason in compact view).
    - `Dependencies` — comma-separated ticket IDs from `dependency_hints` (or `—`).
    - `Parallel safe` — new `BoolBadge` using `parallel_safe_candidate` (currently unused in the UI), with `Yes` (green) / `No` (orange) semantics inverted vs. risk (`No` is the cautious state).
    - `Autonomous recommendation` — `autonomous_execution_recommendation` as a short badge.
    - `Last analyzed` — formatted `updated_at`, small text under the grid.
  - **Prominent warning strip**: when `requires_human_plan_review`, `requires_human_code_review`, or `risk_score >= 8`, render a one-line amber/red banner above the grid (e.g. `"High risk – human plan review required"`). Always visible without expanding.
  - **One-line summary**: render `analysis_summary` as a paragraph below the grid, visually clamped (CSS `line-clamp-3` via a `max-h-*` + `overflow-hidden` fallback if `line-clamp` plugin is unavailable). No behavior change to text content.
  - **Expandable detailed analysis** — toggle button labelled `Show detailed analysis` / `Hide detailed analysis`. Collapsed by default. When expanded, render in a bordered sub-panel:
    - `complexity_factors` (chips) — moved out of compact grid.
    - `recommended_model_reason`.
    - `cost_estimate_status` and any other cost-detail text the field exposes.
    - `queue_rank` + `queue_reason`.
    - `dependency_hints` reasoning (full list with any explanatory text, distinct from the compact comma list).
    - `human_plan_review_reason` and `human_code_review_reason`.
    - Any other non-raw informational fields currently shown (e.g. computed deterministic signals if surfaced by the existing payload).
  - **Raw intelligence section** — second toggle button labelled `Show raw intelligence data` / `Hide raw intelligence data`. Collapsed by default. When expanded, render the full `intelligence` object as `JSON.stringify(intelligence, null, 2)` inside a `<pre>` with debug styling (small monospace, muted background, `overflow-auto`, capped height). Only rendered when an analysis is `completed`.
  - Preserve unchanged:
    - Header row (title, status badge, advisory tag, Analyze/Re-analyze button).
    - Error banner.
    - Loading / `not_started` / `queued` / `running` / `failed` branches.
    - Polling behavior (`usePolling` hook, `ACTIVE_STATUSES`, `POLL_INTERVAL`).
    - All API calls (`getTicketIntelligence`, `analyzeTicketIntelligence`) and their props.

- **`apps/dashboard/tests/TicketIntelligencePanel.test.jsx`** — extend the existing test file (do not delete existing passing assertions; adjust only those that break because a field moved into the collapsed section):
  - Existing tests for `medium`, `moderate`, model name, `Required`, `T001`, summary text, cost range, `#20` queue rank: update the ones whose targets move into the detailed section so they first click `Show detailed analysis` before asserting (queue rank, complexity factors text, model reason, plan-review reason).
  - New test: detailed analysis section is collapsed by default — `Show detailed analysis` button visible, verbose-only content (e.g. queue reason `'Backend foundation first.'`) is not in the document.
  - New test: clicking `Show detailed analysis` reveals the verbose fields (queue reason, model reason, complexity factors, plan-review reason) and the button label switches to `Hide detailed analysis`.
  - New test: raw intelligence section is collapsed by default; clicking `Show raw intelligence data` renders a `<pre>` containing the ticket id string.
  - New test: compact summary renders `Parallel safe` `No` for `parallel_safe_candidate: false`.
  - New test: high-risk warning banner appears when `requires_human_plan_review: true` (uses existing fixture).
  - Keep existing tests for advisory badge, empty state, Analyze button, running state, failed state, Retry analysis button, click-through to `analyzeTicketIntelligence`, polling start/stop.

## Excluded

- Any change to `apps/dashboard/src/api/tickets.js` or any backend endpoint, schema, analyzer prompt, or persisted intelligence field.
- Any change to scheduler, dispatcher, rules engine, readiness evaluator, approvals, or worker behavior.
- Any change to `TicketDetailPage.jsx` beyond what the panel already exposes (the panel keeps the same props and remains drop-in).
- Restyling unrelated panels (`TicketDiagnosticsPanel`, `TicketOperationsPanel`, etc.).
- Adding new persisted fields, telemetry, or feature flags.
- Persisting the `showDetails` / `showRaw` toggle state across reloads (local component state only).
- Internationalization, accessibility audit beyond keeping buttons as `<button>` elements with descriptive text.
- Migrating to a different CSS/UI library or introducing new dependencies (use existing Tailwind classes only).

## Acceptance criteria

- Opening the Ticket Detail page on a completed-analysis ticket shows a single-screen-height compact card (no detailed reasoning, no raw JSON visible) on a laptop viewport.
- The compact grid displays Difficulty, Risk, Estimated cost, Recommended model, Human plan review, Human code review, Dependencies, Parallel safe, Autonomous recommendation, and Last analyzed.
- `analysis_summary` is visible without expanding anything; long summaries are visually clamped.
- A `Show detailed analysis` button is present and collapsed by default; clicking it reveals complexity factors, model reason, queue rank/reason, dependency reasoning, and human review reasons; clicking again hides them.
- A `Show raw intelligence data` button is present and collapsed by default; clicking it reveals a `<pre>` JSON dump of the intelligence object.
- When `requires_human_plan_review`, `requires_human_code_review`, or `risk_score >= 8`, a visible warning strip is rendered without needing to expand any section.
- The failed-analysis branch still shows `Analysis failed` and the summary error; the running/queued/not_started branches render unchanged; the Analyze / Re-analyze / Retry analysis button labels are unchanged.
- All assertions in `tests/TicketIntelligencePanel.test.jsx` pass (existing ones, adjusted where a target moved into the collapsible section, plus the new tests listed above).
- `npm test` in `apps/dashboard` passes with no other test files modified.
- No file outside `apps/dashboard/src/components/TicketIntelligencePanel.jsx` and `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` is modified.
