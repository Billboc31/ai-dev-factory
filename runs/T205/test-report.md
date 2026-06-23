# T205 — Tester Report

**Ticket**: T205 — Compact Ticket Intelligence UI with expandable detailed analysis
**Branch**: `ticket/T205-t205-compact-ticket-intelligence-ui-with-expandabl`
**HEAD**: `0f133612` (review)
**Merge base with main**: `56bfb251`
**Date**: 2026-06-23

## Verdict

**PASS** — Implementation satisfies the ticket's acceptance criteria. No new test regressions vs. main.

## Scope verification

`git diff <merge-base> HEAD --stat` (workflow artifacts excluded) confirms the branch only touches the dashboard:

```
apps/dashboard/src/components/TicketIntelligencePanel.jsx | 298 ++++++++---
apps/dashboard/tests/TicketIntelligencePanel.test.jsx     | 130 ++++-
```

No changes to backend code (`services/`, `tools/agent_runner/`, scheduler, dispatcher, supervisor, readiness evaluator, rules engine, approvals). The non-goal "do not change scheduler / dispatcher / analyzer / rules / readiness / approvals / worker behavior" is honored.

> Note: `git diff main HEAD` does show backend file diffs, but those come from commit `6a6ab89f` (T206) which landed on main after T205 branched. T205 itself touches no backend file.

## Commands executed

1. Branch HEAD test suite — from `apps/dashboard/`:
   ```
   npm test           # vitest run, full suite
   ```
2. Baseline comparison run on `main` worktree (same command).
3. Targeted re-run of failing test files on `main` worktree.

## Test results

### T205 branch — full suite

```
 Test Files  4 failed | 13 passed (18)
      Tests  16 failed | 144 passed (166)
```

`tests/TicketIntelligencePanel.test.jsx`: **25 / 25 PASSED** (new and pre-existing tests).

Failing test files:

| File | Tests failed | Same failures on `main`? |
| --- | --- | --- |
| `tests/DaemonActivityFeed.test.jsx` | 1 / 4 | yes (pre-existing) |
| `tests/TicketDetailPage.test.jsx` | 3 / 3 | yes (pre-existing) |
| `tests/RuntimeDashboardPage.test.jsx` | 4 / 9 | yes (pre-existing) |
| `tests/TicketDetail.test.jsx` | 8 / 9 | yes (pre-existing) |

### Baseline on `main` — full suite

```
 Test Files  4 failed | 13 passed (18)
      Tests  16 failed | 136 passed (158)
```

Same 16 test failures, in the same 4 files, with the same error signatures (`TypeError: Cannot read properties of undefined (reading 'then')` for `getTicketIntelligence` mocks not provided, and unrelated DaemonActivityFeed / RuntimeDashboardPage failures). T205 added 8 new tests to `TicketIntelligencePanel.test.jsx`, all passing — total grew from 158 → 166, passes from 136 → 144, failures stayed at 16.

**Conclusion**: T205 introduces **zero new test failures**. AC "Existing tests continue to pass" is met (the 16 pre-existing failures are out of T205 scope and unchanged).

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Panel is compact by default | PASS | `dl` grid with 10 short fields; verbose content moved behind `<Disclosure>` (`TicketIntelligencePanel.jsx:206-269`). Test `compact view shows key fields without expanding` confirms `Difficulty` field is not inside a `<details>` element. |
| Key operational fields visible without expanding | PASS | Difficulty, Risk, Estimated cost, Recommended model, Plan review, Code review, Dependencies, Parallel safe, Autonomous execution, Last analyzed — all rendered in the default grid. Confirmed by `compact view shows key fields without expanding`. |
| Long reasoning / verbose data hidden behind expandable section | PASS | `Disclosure label="Show detailed analysis"` wraps recommended-model reason, plan/code review reasons, cost details, queue rank, complexity factors, full dependency list, full analysis summary. Test `detailed analysis is collapsed by default` asserts `details.open === false`. |
| Raw/debug info behind separate collapsed section | PASS | `Disclosure label="Show raw intelligence data"` wraps `<pre>` JSON; only rendered when `computed_signals_json` exists. Tests `raw intelligence section is collapsed by default when present`, `raw intelligence section is absent when computed_signals_json missing`, `clicking Show raw intelligence data reveals JSON`. |
| Existing analyze / re-analyze behavior still works | PASS | `triggerAnalysis` and `analyzeLabel()` unchanged (`TicketIntelligencePanel.jsx:127-142`). Tests `shows Analyze button when no analysis`, `shows Re-analyze button when completed`, `shows Retry analysis button when failed`, `calls analyzeTicketIntelligence when Analyze is clicked`, `shows "Analysis running" on button when active`. |
| No scheduler / dispatcher / readiness / rules / approval / worker behavior changed | PASS | Branch touches only `apps/dashboard/**`. No backend files modified (see *Scope verification* above). |
| Existing tests continue to pass | PASS (with caveat) | All previously-passing tests still pass; the 16 failures present on the branch are identical to the 16 failures on `main` and are unrelated to T205. |

## UX / non-goal verification

| Item | Status | Evidence |
| --- | --- | --- |
| One-line summary visible by default | PASS | `analysis_summary` rendered with `line-clamp-3` and `title` attribute for hover-full-text (`TicketIntelligencePanel.jsx:271-278`). |
| Important warnings remain visible without expanding | PASS | `highlightWarning` ring (orange-300 border) triggers when `risk_score >= 7` or either human review is required (`TicketIntelligencePanel.jsx:144-153`). Test `high risk applies warning border`. Failed state shows red banner before any expansion. |
| Detailed reasoning remains accessible | PASS | `<details>` element keeps content in the DOM, accessible to assistive tech and audit. |
| Empty / running / failed / not_started / queued / completed states all render | PASS | Tests cover `No analysis yet`, `Analysis in progress`, `Analysis failed`, completed compact view, queued (polling). |
| Re-analyze action preserved | PASS | Button labels still `Analyze` / `Re-analyze` / `Retry analysis` / `Analysis running…` / `Starting…`. |
| No persisted-intelligence-field changes | PASS | No backend or schema change. Component reads existing fields only. |

## Anomalies observed

None attributable to T205.

Pre-existing failures (out of scope, present on `main` too):

- `tests/DaemonActivityFeed.test.jsx > passes custom lines count to API` — argument-order mismatch in `getDaemonActivity` mock assertion.
- `tests/TicketDetailPage.test.jsx > TicketDetailPage — runtime state change > *` (3 tests) — `Cannot read properties of undefined (reading 'then')` because `getTicketIntelligence` is not mocked.
- `tests/RuntimeDashboardPage.test.jsx > *` (4 tests) — `Sandbox Runs` section not found / log drawer assertions; appears to be a copy-state issue unrelated to TI panel.
- `tests/TicketDetail.test.jsx > *` (8 tests) — `getTicketIntelligence` not mocked, same root cause as TicketDetailPage failures.

These should be fixed in a follow-up ticket (likely a one-line fix: add `ticketsApi.getTicketIntelligence.mockRejectedValue({ response: { status: 404 } })` to the failing test setup).

## Limits of validation

- Tests run in jsdom under vitest. The UX criteria around screen fit, scroll length and visual obviousness were verified at code-level only; no live browser screenshot review was performed.
- The `line-clamp-3` class depends on the Tailwind `@tailwindcss/line-clamp` plugin / Tailwind 3.3+ built-in support; not visually inspected.

## Final decision

**Implementation accepted from a testing standpoint.** All ticket acceptance criteria are met. No regressions vs. `main`. The 16 pre-existing test failures are out of scope and predate this branch.
