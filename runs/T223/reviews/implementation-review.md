All tests pass and the implementation matches the plan closely. Let me finalize the review.

## Review — T223: Project-level toggle for Human Plan Approval gate

### Verification
- Python: 62/62 tests pass (`test_ticket_approval_service.py`, `test_execution_rules_engine.py`, `test_execution_rules_api.py`, `test_run_ticket_plan_auto_approve.py`, `test_execution_rules_pipeline_untouched.py`).
- Dashboard: 12/12 tests pass (`ProjectRulesPanel.test.jsx`, `TicketDetailPage.test.jsx`).

### Scope
Implementation stays inside the boundaries of the ticket:
- Only touches the plan-approval gate; no changes to Intelligence, Dependency Analysis, Readiness, Dispatcher, execution approval, tests, or CI.
- Static guard `test_execution_rules_pipeline_untouched.py` is tightened rather than loosened: `evaluate_ticket` remains fully forbidden in the pipeline; `run_ticket` is only allowed to touch the new read-only helper `is_human_plan_approval_required`. Any regression that pulls broader engine surface into the runner will fail this test.

### Correctness
- `RULE_REGISTRY["require_human_plan_approval"]` at `execution_rules_engine.py:243` has `default_enabled=True` — safe default matches ticket (existing projects unchanged).
- `is_human_plan_approval_required` at `execution_rules_engine.py:331` has three safe-default fallbacks: no project id, missing rule row, any lookup exception → return `True`. Correct: the safe default is always to require human approval.
- `auto_approve_plan` at `ticket_approval_service.py:149` is idempotent (checks latest `plan` row first) and writes `approval_type="plan"`, `approval_status="approved"`, `approved_by="SYSTEM"`, `approval_comment="PROJECT_SETTING"` — exact match with the ticket's audit fields (`approval_type=AUTO`, `approval_reason=PROJECT_SETTING`, `approved_by=SYSTEM`). Note the type is `"plan"` not `"AUTO"`; the audit distinction (auto vs manual) is carried by `approved_by="SYSTEM"`, not by `approval_type`. This is a reasonable interpretation and the UI badge correctly keys on `approved_by === "SYSTEM"`.
- `_maybe_auto_approve_plan` at `run_ticket.py:908` is wired at the single correct site (`run_ticket.py:1312`, after both `INIT → PLAN_REVIEW_NEEDED` and `PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED` transitions). Plan artifact is still checkpointed at `run_ticket.py:1258` before this branch runs, so `plan.md` persistence is preserved.
- Daemon interaction is safe: `PLAN_APPROVED` is in `AUTO_RUNNABLE_STATES` (`run_daemon.py:229`), so the next daemon tick continues to the coder step without seeing `PLAN_REVIEW_NEEDED`.
- The `approvals` API needs no change: `TicketApproval.approval_type: str` already surfaces arbitrary values; `TicketDetailPage.jsx:346` filters by `approval_type === 'plan'` on the client side.

### Dashboard
- Badge at `TicketDetailPage.jsx:461` (`data-testid="plan-auto-approved-badge"`) with distinctive purple styling.
- Manual "Approve Plan / Request Plan Fix" buttons hidden when `planAutoApproved`, but "Approve Implementation / Request Impl Fix" remain visible — this matches the ticket ("ONLY affects the Human Plan Approval gate").
- Both test cases exercise the badge visibility and the button visibility across auto and human approval paths.

### Code quality
- Comments in `_resolve_project_id_from_state`, `_maybe_auto_approve_plan`, and `runtime_db.py:120` explain non-obvious choices (safe default, DDL comment listing `execution`/`plan` types). No excess commentary.
- Deferred imports in `_maybe_auto_approve_plan` are consistent with the rest of `run_ticket.py` (which imports `runtime_db` lazily elsewhere) and keep CLI startup unchanged.
- No new dependencies, no new API endpoints, no schema migration.

### Observations (non-blocking)
- `auto_approve_plan` signature accepts a `reason` keyword but `_maybe_auto_approve_plan` never uses anything but the default; the parameter is currently only wired for future callers/tests. This is fine — it's a natural extension point and is used in `test_auto_approve_plan_accepts_custom_reason`.
- The log line `"auto-run: transition PLAN_REVIEW_NEEDED → PLAN_APPROVED (auto, PROJECT_SETTING)"` hardcodes the reason string. If a future caller passes a different `reason`, the log will lie. Not a real bug today; worth a small refactor only if that flexibility ever ships.
- `PLAN_REVIEW_NEEDED` in this codebase is the checkpoint used by both the AI plan-review step and the human plan-approval step (`STATE_MACHINE` at `run_ticket.py:72` sends it through `review`). Disabling the toggle skips both. This matches the ticket's stated flow ("Plan generated → Automatically approved → Implementation") — flagging for awareness, not a blocker.

### Acceptance criteria coverage
- New project-level rule ✓
- Default `true` ✓ (`test_get_rules_returns_registry_defaults_when_empty`)
- Configurable via existing rules API/UI ✓ (`test_put_rules_roundtrips_require_human_plan_approval`)
- No app restart required ✓ (rule is read on each planner completion)
- Plan is persisted ✓ (unchanged `_checkpoint_planner_artifacts`)
- Auto approvals distinguishable ✓ (`approved_by="SYSTEM"`, badge)
- All other gates unchanged ✓ (static guard test)
- Existing projects behave as before ✓ (default `enabled=True`)

Implementation is complete, well-scoped, correctly tested, and does not compromise the advisory-only contract of the rules engine.

IMPLEMENTATION_APPROVED
