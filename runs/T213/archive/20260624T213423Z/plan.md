## Objective

Restrict `TicketReadinessEvaluator` to *workflow-entry* prerequisites only. Stop blocking on `"Human plan approval missing"` (a downstream gate already enforced by the plan-review state machine, `ticket_execution_eligibility._eval_approval`, and `execution_rules_engine`). Demote the human-plan-review signal to a non-blocking advisory warning, so that a freshly created ticket with `requires_human_plan_review=True` reports `readiness_status="ready_candidate"` plus a forward-looking warning, instead of `"blocked"`.

## Included

### Evaluator — `tools/agent_runner/ticket_readiness_evaluator.py`

- Replace `_check_human_approval()` (lines 119–139) with `_check_human_plan_review_advisory()` returning `(required_flag, present_flag, warning_or_None)`. The function keeps the same detection logic (`requires_human_plan_review` from intelligence, plus marker-file / state lookup helpers) but never produces a blocking reason. When `required=True` and `present=False`, return the advisory string `"Human plan review may be required later"`. When `required=True` and `present=True`, return no warning. When `required=False`, return no warning.
- In `run_evaluation()` (lines 165–236):
  - Remove `approval_status` from the `all_passed` boolean (lines 201–205). `ready_candidate` must depend only on `intel_status` and `dep_status`.
  - Drop `approval_reason` from the `blocking_reasons` list (lines 198–199).
  - Build a `warnings` list containing the advisory string from the new function (and keep room for future advisory checks). Persist it via `warnings_json=warnings` instead of `warnings_json=[]` (line 228).
  - Continue to persist `approval_check_status`, `human_approval_required`, `human_approval_present` so the panel sub-check section keeps working. The `approval_check_status` value becomes `"advisory"` when `required=True` and `present=False`, and `"passed"` otherwise (i.e. it no longer takes the value `"failed"`).
- Update the docstring at the top of the file (lines 1–14) to state explicitly: "Readiness evaluates only workflow-entry prerequisites. Downstream gates (human plan approval, execution approval, execution rules) are NOT evaluated here — they live in the plan-review state machine, `ticket_execution_eligibility`, and `execution_rules_engine`."
- Remove the now-unused `_PLAN_APPROVED_OR_LATER` constant only if `_has_plan_approved_marker` / `_state_implies_plan_approved` end up unused after the rewrite. If they remain used by the advisory function, keep them.

### Tests — `tests/test_ticket_readiness_evaluator.py`

- Rewrite `test_missing_human_approval_blocks` (lines 140–148) into `test_missing_human_approval_emits_warning_not_block`: assert `readiness_status == "ready_candidate"`, `ready_candidate == 1`, `"Human plan review may be required later"` in `warnings_json`, no `"Human plan approval missing"` anywhere in `blocking_reasons_json`, `human_approval_required == 1`, `human_approval_present == 0`, and `approval_check_status == "advisory"`.
- Update `test_human_approval_present_via_marker_file_passes` (lines 151–160): assert `readiness_status == "ready_candidate"`, `approval_check_status == "passed"`, `warnings_json == []` (or at least no plan-review warning), `human_approval_present == 1`.
- Add `test_intelligence_missing_still_blocks`: verify that `"Missing Ticket Intelligence analysis"` remains a true blocker (regression guard).
- Add `test_dependency_missing_still_blocks`: regression guard for the dependency blocker.
- Add `test_warnings_persist_alongside_ready_candidate`: assert that a ticket with `requires_human_plan_review=1`, completed intelligence, and no dependency issues yields `ready_candidate` + non-empty `warnings_json`.

### Tests — `tests/test_ticket_readiness_api.py`

- Update `test_get_readiness_returns_blocking_reasons` (lines 117–140): replace `"Human plan approval missing"` in the test fixture with a still-valid blocking reason (only `"Dependency T001 not merged"` is needed), and add a separate assertion that the API surfaces `warnings` alongside blocking reasons.
- Add `test_get_readiness_returns_warnings`: stub a row with `warnings_json=["Human plan review may be required later"]`, assert `body["warnings"]` contains the string.

### UI — `apps/dashboard/src/components/TicketReadinessPanel.jsx`

- Update the approval sub-check sub-message at lines 190–192. Replace `"Human plan approval missing"` with `"Human plan review may be required later"` and render it in the existing amber/advisory style (not red). The condition stays `readiness.human_approval_required && !readiness.human_approval_present`.
- No other UI changes required: the warnings amber-box rendering at lines 172–181 already exists, the `READY CANDIDATE` badge at lines 123–127 already exists, and `blocking_reasons` rendering at lines 161–169 stays untouched.

### Documentation — none

No docs file currently describes the readiness contract beyond the module docstring. The docstring update inside `ticket_readiness_evaluator.py` is the canonical source. Do not introduce a new markdown file for this.

## Excluded

- No change to `ticket_execution_eligibility.py`: its `_eval_approval()` check still legitimately blocks execution when `requires_human_plan_review` is unmet, since eligibility (not readiness) is the right layer for that gate.
- No change to `execution_rules_engine.py`: rules `_rule_require_readiness_candidate`, `_rule_require_human_approval`, `_rule_block_when_human_review_required` keep their current semantics.
- No change to `ticket_approval_service.py`: execution approval workflow and the `ready_to_take` promotion remain as today.
- No change to the plan-review state machine in `run_ticket.py` / `run_daemon.py`: `PLAN_REVIEW_NEEDED`, `PLAN_APPROVED`, `PLAN_FIX_REQUIRED` transitions stay identical, and `tests/test_human_approval.py` is not touched.
- No change to the DB schema (`ticket_readiness` table already has `warnings_json` and `ready_candidate` columns).
- No change to the Pydantic `TicketReadiness` schema (warnings field already present).
- No new status enum values: `ready_candidate` already plays the role the ticket calls `READY_CANDIDATE`.
- No change to dependency parsing, intelligence check, or context-freshness check.
- No retroactive re-evaluation of historical tickets in the DB; status changes will appear next time each ticket is evaluated.

## Acceptance criteria

- `_check_human_approval()` no longer exists, or its replacement never appends to `blocking_reasons`.
- For a ticket with `requires_human_plan_review=1`, completed intelligence, and no failing dependencies: `runtime_db.get_ticket_readiness(...)` returns `readiness_status="ready_candidate"`, `ready_candidate=1`, `"Human plan approval missing"` absent from `blocking_reasons_json`, `"Human plan review may be required later"` present in `warnings_json`.
- A `grep` for the literal string `"Human plan approval missing"` over `tools/`, `services/`, and `tests/` returns no production source occurrences (test fixtures referencing it must be updated too).
- `tests/test_ticket_readiness_evaluator.py` passes, including the rewritten `test_missing_human_approval_emits_warning_not_block`.
- `tests/test_ticket_readiness_api.py`, `tests/test_ticket_readiness_db.py`, `tests/test_ticket_execution_eligibility.py`, `tests/test_ticket_approval_service.py`, `tests/test_execution_rules_engine.py`, and `tests/test_human_approval.py` all pass with no other modification than the targeted edits in `test_ticket_readiness_api.py`.
- The full test suite (`pytest tests/`) is green.
- The UI panel renders `"Human plan review may be required later"` (in amber, not red) for a ticket whose intelligence sets `requires_human_plan_review=1` and which has no plan approval marker yet.
- A ticket whose only outstanding concern is human plan review is no longer displayed with a red `BLOCKED` badge in the dashboard.
