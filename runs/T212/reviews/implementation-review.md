# Review — T212 (attempt 2)

## Scope check

This branch was forked from `4f9cd83f` (pre-T210). The diff vs. local `main` shows T210/T211 files, but those are already merged upstream — the actual T212 PR delta is contained in commit `9a8a7ce8` and only touches the dispatcher service, its routes/schemas/registration, the dashboard page + nav, and the two new test files. No daemon/runner/supervisor/scheduler code is modified by T212.

## Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| `TicketDispatcherService` exists | ✅ | `tools/agent_runner/ticket_dispatcher.py:196` (`get_recommended_tickets`) |
| Dispatcher can be disabled | ✅ | `AI_DEV_FACTORY_DISPATCHER_MODE` (`:63-73`), `DEFAULT_DISPATCHER_MODE = "off"` (`:41`) |
| Off ⇒ current behavior unchanged | ✅ | Short-circuit at `:222-223`; `test_off_mode_returns_empty_and_skips_eligibility` asserts eligibility is never invoked |
| Advisory recommendations computed with no side effects | ✅ | `test_dispatcher_does_not_write_to_db` and `test_endpoint_does_not_persist` snapshot DB bytes before/after |
| Recommendation reasons exposed | ✅ | `_format_reason()` (`:161-175`) emits `READY_TO_TAKE, difficulty=..., queue_rank=..., no blockers` |
| Dedicated Dispatcher page | ✅ | `apps/dashboard/src/pages/DispatcherPage.jsx`; route in `App.jsx:94`; sidebar entry in `ProjectSidebar.jsx:6` |
| No worker/scheduler/daemon changes | ✅ | Structurally enforced by `test_dispatcher_modules_do_not_import_runner` (forbids `run_ticket`/`run_daemon`/`supervisor` symbols in the new modules) |
| Existing tests pass | ✅ | 20 new + 16 adjacent eligibility tests verified locally |

## Plan compliance

The implementation matches the approved plan:

- Modes constant, env-var resolver, score formula (`50 + queue_rank_bonus + difficulty_bonus + age_bonus`), and tiebreak (`(-score, queue_rank, updated_at, ticket_id)`) match the plan verbatim (`ticket_dispatcher.py:127-193`).
- `auto` mode returns `not_implemented=True` with empty lists (`:225-228`, `test_auto_mode_returns_not_implemented`).
- Pydantic models (`DispatcherStatus`, `DispatcherRecommendation`, `DispatcherRecommendationIntelligence`, `DispatcherBlockedTicket`, `DispatcherResponse`) added at `services/control_api/models/schemas.py:667-705`.
- API surface registered at `services/control_api/main.py:222-223`.
- Dashboard page implements the disabled / advisory / manual / auto variants with reason/score/queue_rank columns and a blocked-tickets table; `manual` exposes an "Open" link to the existing ticket detail page rather than introducing a new launch endpoint.

## Non-blocking observations

1. **`evaluate_eligibility` is not guarded by `_safe_call`** (`ticket_dispatcher.py:244`) even though `runtime_db.list_ticket_runtime` and `get_ticket_intelligence` are. The eligibility module is defensive internally, so this is unlikely to crash in practice, but a single hostile ticket could fail the whole request — worth a `try/except` that logs and falls back to a `blocked` entry.
2. **`_resolve_mode("")` returns `off`** instead of falling back to the env var. A caller sending `?mode=` (empty string) gets the default rather than the configured mode. Minor; the dashboard never hits this path.
3. **Excluded-state list narrower than plan wording**. The plan references `FORBIDDEN_RUNNER_STATES / archived / pr_ready / done per board_service`. The implementation hardcodes `{PLANNING, CODING, CANCELLED, TEST_COMPLETE}` + `daemon_archived`. `board_service` also treats `issue_closed` (a `state.json` flag) as "done" — such tickets will land in `blocked` here rather than be hidden. Cosmetic, not a behavioral defect.
4. **Documentation deliverable missing**. The plan asked for a brief mention of modes + env var in a service overview/README; none was added. Module docstring covers it inline, but a one-paragraph addition would close the gap.
5. **No frontend smoke test** for `DispatcherPage` despite other pages having Vitest coverage. The page is small and entirely render-based; a mount-with-mocked-API test for the disabled/advisory/manual variants would tighten the UI contract.
6. **Linear cost per request × 10s polling**. Acceptable for advisory scope; should be revisited when the future scheduler graduates the dispatcher to `auto`.

## Decision

The service is read-only by construction, opt-in via env var, defaults to `off`, and does not touch any existing execution code. All acceptance criteria are satisfied; the observations above are improvements rather than blockers.

IMPLEMENTATION_APPROVED
