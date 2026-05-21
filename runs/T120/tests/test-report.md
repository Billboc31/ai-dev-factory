---

## Test Report Summary — T120

All 7 acceptance criteria **pass**.

| # | Criterion | Status |
|---|-----------|--------|
| AC1 | `GET /tickets/{id}` includes `retry_info` when `retry-state.json` exists | **PASS** |
| AC2 | `GET /tickets/{id}/timeline` includes `retry_info` + `last_error` | **PASS** |
| AC3 | Dashboard overview tab shows retry fields when present | **PASS** |
| AC4 | Dashboard overview tab shows last error when present | **PASS** |
| AC5 | `WorkflowTimeline` annotates failed steps with attempt + failure class | **PASS** |
| AC6 | Existing API contract unchanged (new fields nullable) | **PASS** |
| AC7 | No new top-level routes introduced | **PASS** |

**Tests run**: 6 backend unit tests, 6 integration tests against real worktree paths, 4 live API calls against a running server, and static JSX analysis of both frontend components.

**One observation (non-blocking)**: The `WorkflowTimeline` retry annotation (AC5) is correct code, but the current `_STATUS_MAP` never produces a `failed` step status — so the annotation won't be visible until the runtime state machine emits `failed` steps. This is a pre-existing constraint outside T120's scope.

**Verdict**: `TEST_COMPLETE`
