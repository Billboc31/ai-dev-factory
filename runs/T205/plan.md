## Objective
Restructure `apps/dashboard/src/components/TicketIntelligencePanel.jsx` so the completed-analysis view is compact and scannable by default, with verbose reasoning and raw diagnostic data hidden behind expandable disclosure sections. No analyzer, scheduler, readiness, rules, approval, dispatcher, worker, diagnostics, or operations behavior changes. Plan recalculated from current `main`.

## Included

### Component refactor — `apps/dashboard/src/components/TicketIntelligencePanel.jsx`

Keep the existing top-level structure (header with title + `StatusBadge` + advisory badge + analyze/re-analyze button, error banner, loading/empty/running/failed branches). Rework only the `status === 'completed'` branch.

1. **Add a local disclosure helper** inside the file:
   - `function Disclosure({ label, defaultOpen = false, children, dataTestId })` — renders a `<details>` element (uncontrolled by default) with a `<summary>` whose visible text is `label`. Use native `<details>` to keep accessibility (keyboard toggle, `aria-expanded` for free) and avoid extra state. Style the `<summary>` as a small clickable text button (text-xs, text-blue-600, cursor-pointer, list-none with `[&::-webkit-details-marker]:hidden`). Optionally accept `dataTestId` and pass it to the `<details>` for tests.

2. **Compact summary block** — replace the current single `<dl>` with a two-zone layout:

   a. **Key fields grid** (`<dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">`) showing only short labelled values (no inline reasons / no inline complexity-factor chips):
      - `Difficulty` → `ScoreBadge` (existing)
      - `Risk` → `ScoreBadge` (existing)
      - `Estimated cost` → formatted `$min – $max CCY` (reuse existing logic, fallback `unknown`)
      - `Recommended model` → existing `font-mono` chip (no reason text in compact view)
      - `Plan review` → `BoolBadge` with `Required` / `Not required` (no reason text)
      - `Code review` → `BoolBadge` with `Required` / `Not required` (no reason text)
      - `Dependencies` → comma-joined `dependency_hints` as small mono chips, or `—` when empty/missing
      - `Parallel safe` → `BoolBadge` mapping `parallel_safe_candidate` → `Yes` / `No`, `—` when null
      - `Autonomous execution` → existing mono chip
      - `Last analyzed` → formatted `updated_at` (move out of footer into the compact grid)

   b. **One-line summary**: render `analysis_summary` as a single short paragraph below the grid with a clamp class (`line-clamp-3`) and `title={analysis_summary}` so the full text is reachable via hover. If absent, render nothing.

3. **`Disclosure label="Show detailed analysis"` (collapsed by default)** containing the verbose fields removed from the compact grid:
   - `Recommended model reason` (`recommended_model_reason`)
   - `Plan review reason` (`human_plan_review_reason`)
   - `Code review reason` (`human_code_review_reason`)
   - `Cost estimate details` (`cost_estimate_status`, `estimated_input_tokens`, `estimated_output_tokens`) when present
   - `Queue rank (advisory)` (`queue_rank` + `queue_reason`) — moved out of compact view
   - `Complexity factors` (`complexity_factors`) — chips, full list
   - `Dependency hints (full)` (`dependency_hints`) — same chips, only render here when the list is non-empty (compact view already shows them inline, but keep them here for symmetry with reasoning labels)
   - `Full analysis summary` (`analysis_summary`) without clamping
   Each sub-field renders only when its value is present; missing fields are simply omitted. No new API calls.

4. **`Disclosure label="Show raw intelligence data"` (collapsed by default)** rendered only when `intelligence.computed_signals_json` is present. Inside, render the existing object inside a `<pre className="bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-auto whitespace-pre-wrap max-h-96">` via `JSON.stringify(intelligence.computed_signals_json, null, 2)`. The whole intelligence object is *not* exposed here (no new debug surface).

5. **Visual emphasis for warnings (always visible, not behind disclosure)**:
   - When `risk_score >= 7` **or** `requires_human_plan_review === true` **or** `requires_human_code_review === true`, the panel container gets an extra `border-orange-300` class.
   - The `failed` branch is unchanged.

6. **State branches preserved**:
   - `not_started` → existing "No analysis yet" message + `Analyze` button (unchanged).
   - `queued` / `running` → existing in-progress message + button label (`Analysis running…`) and polling (unchanged).
   - `failed` → existing red error box + `Retry analysis` button (unchanged).
   - `completed` → new compact layout described above.

7. **Behavior preserved**:
   - `usePolling` interval, `ACTIVE_STATUSES` set, `triggerAnalysis` flow, `analyzeLabel` button text, error display, 404 → null intelligence — all unchanged.
   - `api.getTicketIntelligence` / `api.analyzeTicketIntelligence` calls and their arguments unchanged.

### Tests — `apps/dashboard/tests/TicketIntelligencePanel.test.jsx`

Update and extend the existing Vitest + RTL suite. The fixture `COMPLETED_INTELLIGENCE` stays as is and is reused; add a second fixture `COMPLETED_INTELLIGENCE_WITH_SIGNALS` that includes `computed_signals_json: { foo: 'bar', n: 3 }`.

- Keep existing tests for advisory badge, "No analysis yet", `Analyze` button, basic completed-state field rendering (difficulty/risk/model), `Re-analyze` button, running/failed/retry state, `analyzeTicketIntelligence` click, polling on/off, and cost formatting. Where assertions target text that now lives only inside the collapsed disclosure (`Requires architecture reasoning`, `DB schema change`, `#20` queue rank), update each assertion to first click the `Show detailed analysis` summary, then assert.
- Add new tests:
  - `compact view shows key fields without expanding` — asserts presence of `Difficulty`, `Risk`, `Estimated cost`, `Recommended model`, `Plan review`, `Code review`, `Dependencies`, `Parallel safe`, `Autonomous execution`, `Last analyzed` labels and that `Requires architecture reasoning.` is **not** in the DOM initially.
  - `detailed analysis is collapsed by default` — assert the `Show detailed analysis` summary is present and that verbose reasoning text (`Requires architecture reasoning.`, `DB schema change.`, `#20`) is not visible (use `queryByText` returning null or use `details` `open` attribute assertion via `closest('details').open === false`).
  - `clicking Show detailed analysis reveals verbose fields` — click the summary, assert `Requires architecture reasoning.`, `DB schema change.`, and `#20` are visible.
  - `raw intelligence data section is hidden by default and absent when computed_signals_json missing` — with default fixture, `Show raw intelligence data` summary is **not** rendered; with `COMPLETED_INTELLIGENCE_WITH_SIGNALS`, the summary is rendered and the closest `<details>` has `open === false`.
  - `clicking Show raw intelligence data reveals JSON` — click the summary, assert the rendered `<pre>` contains `"foo": "bar"`.
  - `missing optional fields do not crash` — render with minimal `{ ticket_id, analysis_status: 'completed' }`; expect the compact grid to render without throwing and key labels like `Difficulty` to still be present.
  - `high risk applies warning border` — render with `risk_score: 9`; assert the outermost panel container has the `border-orange-300` class.
- Do not change `not_started`, `running`, `failed`, `Retry analysis`, polling, or click-to-analyze tests.

### Files touched

- `apps/dashboard/src/components/TicketIntelligencePanel.jsx` — refactor only.
- `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` — adjust existing assertions, add new ones, add second fixture.

No other component, page, route, helper, hook, API client, schema, or backend file is modified.

## Excluded

- Any change to `services/control_api/routes/intelligence.py`, `services/control_api/models/schemas.py`, or any other backend file. The current `TicketIntelligence` schema already exposes every field the compact and detailed views need (`difficulty_*`, `risk_*`, `complexity_factors`, `recommended_model*`, `estimated_cost_*`, `cost_currency`, `cost_estimate_status`, `queue_rank`, `queue_reason`, `dependency_hints`, `parallel_safe_candidate`, `requires_human_plan_review` + reason, `requires_human_code_review` + reason, `autonomous_execution_recommendation`, `analysis_summary`, `computed_signals_json`, `updated_at`).
- Any change to analyzer logic, persisted intelligence fields, scheduler, readiness evaluator, rules engine, human approval workflow, dispatcher, worker, diagnostics, or operations behavior.
- Any change to `TicketDetailPage.jsx` mounting order or to sibling panels (`TicketReadinessPanel`, `HumanApprovalPanel`, `TicketRuleEvaluationPanel`, `TicketDiagnosticsPanel`, `TicketOperationsPanel`).
- Any change to `apps/dashboard/src/api/tickets.js` or to the `getTicketIntelligence` / `analyzeTicketIntelligence` endpoints/arguments.
- Removal of any existing intelligence field from the UI — all verbose fields stay reachable via the `Show detailed analysis` disclosure.
- Introduction of a global UI library, design-system component, or new dependency. The disclosure uses the native `<details>` element; no new package install.
- Persisting the open/closed state of the disclosure across renders or routes (the native uncontrolled `<details>` is sufficient).
- Renaming, splitting, or moving `TicketIntelligencePanel.jsx`.
- Storybook entries, screenshot/visual-regression tooling, or new e2e tests beyond the existing Vitest suite.

## Acceptance criteria

- This plan was recalculated from current `main` after `TicketIntelligencePanel.jsx`, `TicketDetailPage.jsx`, `api/tickets.js`, and `schemas.py` were re-read; it targets the current location `apps/dashboard/src/components/TicketIntelligencePanel.jsx`.
- After implementation, when a `completed` analysis is loaded, the panel renders only: the header row (title + status badge + advisory badge + analyze button), a key-fields grid with `Difficulty`, `Risk`, `Estimated cost`, `Recommended model`, `Plan review`, `Code review`, `Dependencies`, `Parallel safe`, `Autonomous execution`, `Last analyzed`, a short `analysis_summary` paragraph (clamped), a collapsed `Show detailed analysis` summary, and (only when `computed_signals_json` is present) a collapsed `Show raw intelligence data` summary.
- The compact panel for a typical completed analysis fits within roughly one laptop viewport (no long scroll required to see all key fields).
- `complexity_factors`, `recommended_model_reason`, `human_plan_review_reason`, `human_code_review_reason`, `cost_estimate_status` / token estimates, `queue_rank` + `queue_reason`, and the full `analysis_summary` render only inside the `Show detailed analysis` disclosure (collapsed by default).
- `computed_signals_json` renders only inside the `Show raw intelligence data` disclosure (collapsed by default); the disclosure is not rendered when the field is missing.
- High risk (`risk_score >= 7`) or required human plan/code review applies a visible `border-orange-300` accent on the panel container without requiring any disclosure to be expanded.
- The `not_started`, `queued`/`running` (with polling), and `failed` branches behave exactly as before; `Analyze`, `Re-analyze`, `Retry analysis`, and `Analysis running…` button states are unchanged.
- `api.getTicketIntelligence` and `api.analyzeTicketIntelligence` are called with the same arguments and at the same moments as before; no new endpoints are introduced.
- `TicketDetailPage.jsx` continues to mount, in order: `TicketIntelligencePanel`, `TicketReadinessPanel`, `HumanApprovalPanel`, `TicketRuleEvaluationPanel`, `TicketDiagnosticsPanel`, `TicketOperationsPanel`.
- `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` passes, covering: compact summary fields, detailed-analysis collapsed by default, expanding reveals verbose fields, raw JSON collapsed by default and absent when missing, missing optional fields do not crash, high-risk warning border, and unchanged not_started/running/failed/Retry/polling/click-to-analyze behaviors.
- The full dashboard test suite (`npm test` under `apps/dashboard/`) passes without modification to any other test file.
- No file outside `apps/dashboard/src/components/TicketIntelligencePanel.jsx` and `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` is modified.
