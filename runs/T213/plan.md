## Objective

Restrict `TicketReadinessEvaluator` and its UI rendering to **workflow-entry prerequisites only**, so that gates owned by later stages (human plan approval, human execution approval, planner review states, execution rules, ready-to-take) can never block readiness and instead surface as non-blocking warnings. The PR also tightens tests and decouples the readiness timeline view from execution-eligibility semantics.

## Included

### 1. `tools/agent_runner/ticket_readiness_evaluator.py`

- Add an explicit module docstring stating the contract: *"Readiness answers only: can this ticket ENTER the workflow now? It must never block on plan approval, execution approval, planner review states, execution rules, or ready-to-take."*
- Audit and harden the blocker construction (currently lines ~204–207):
  - Confirm `blocking_reasons` is populated only from `_check_intelligence()` and `_check_dependencies()`.
  - Add a guard helper `_is_entry_prerequisite_reason(reason: str) -> bool` and assert (via tests) that every appended reason passes it. Reasons referencing `"approval"`, `"plan review"`, `"execution rule"`, `"ready_to_take"` must be rejected at runtime (raise + log, then drop the reason rather than block).
- Refactor `_check_human_plan_review_advisory()` into a more general `_collect_future_approval_warnings()` that:
  - Returns warnings (never blockers) for: missing future plan review *and* missing future execution approval, when intelligence indicates either may be required later.
  - Preserves the existing wording `"Human plan review may be required later"` and adds `"Human execution approval may be required later"` when applicable.
- Keep `_state_implies_plan_approved()` as a *signal* only (to promote `ready_candidate` → `ready_to_take` when a downstream approval already exists). Do not let any planner-review state (`PLAN_REVIEW_NEEDED`, `PLAN_FIX_REQUIRED`) influence the `blocked` status — add a comment to that effect.
- Remove any dead branch (if found during audit) that consults `execution_rules_engine` or `ticket_approval_service` from inside the readiness path.

### 2. `services/control_api/routes/readiness.py`

- No behavioural change to endpoints; ensure the `_parse_row()` payload still exposes `blocking_reasons`, `warnings`, `human_approval_required`, `human_approval_present` unchanged.
- Add a short docstring at the top of the module restating the readiness scope, mirroring the evaluator.
- Confirm `POST /tickets/{ticket_id}/evaluate-readiness` does not pass any approval-state inputs to the evaluator.

### 3. UI — readiness rendering & timeline

- `apps/dashboard/src/lib/ticketWorkflowStatus.js` `readinessStep()`:
  - When `readiness_status === "ready_candidate"`, render the step as `READY_CANDIDATE` (not `BLOCKED`), even if `human_approval_required && !human_approval_present`.
  - Move any text derived from `human_approval_required && !human_approval_present` from "blocking reason" rendering into the `warnings` list.
  - Add explicit handling for completed tickets: when downstream workflow state is `PLAN_APPROVED` or later, render readiness as `PASSED` / `N/A` rather than re-evaluating.
- `apps/dashboard/src/components/TicketWorkflowTimeline.jsx`:
  - Stop auto-opening the readiness step as "blocked" when only warnings are present.
  - Ensure the global summary derives `BLOCKED` only from `blocking_reasons.length > 0`, not from the presence of advisory warnings.
- `apps/dashboard/src/components/TicketReadinessPanel.jsx`:
  - Verify warning rendering already uses amber/non-blocking styling; add the new `"Human execution approval may be required later"` warning to the rendered warnings list (driven by payload, no hardcoded copy).

### 4. Boundary with Eligibility (read-only verification, no code move)

- Add a short comment in `tools/agent_runner/ticket_execution_eligibility.py` near the approval check (~line 210) clarifying: *"This belongs to Eligibility, not Readiness. Readiness must never surface this message as a blocker."* No logic change.
- Confirm the dashboard renders Eligibility's `"Human plan approval required"` only inside the Eligibility panel/section, not the Readiness timeline step. Adjust the readiness step builder if it currently reads from eligibility fields.

### 5. Tests

- Update `tests/test_ticket_readiness_evaluator.py`:
  - Keep the existing assertion that `"Human plan approval missing"` never appears in blockers.
  - Add: `test_missing_human_execution_approval_does_not_block` — readiness stays `ready_candidate` with a warning.
  - Add: `test_planner_review_states_do_not_block_readiness` — parametrize over `PLAN_REVIEW_NEEDED`, `PLAN_FIX_REQUIRED`, `PLAN_APPROVED` and assert no blocking reason mentions plan/review/approval.
  - Add: `test_execution_rules_state_does_not_block_readiness` — even when execution rules would deny, readiness ignores it.
  - Add: `test_blocking_reasons_only_from_entry_prerequisites` — asserts every blocker passes `_is_entry_prerequisite_reason`.
- Update `tests/test_ticket_readiness_api.py`:
  - Add: `test_readiness_returns_warnings_not_blockers_when_approvals_pending`.
  - Add: `test_readiness_status_ready_candidate_with_advisory_warnings_is_not_blocked`.
- Add a small JS test (or Storybook fixture if the project uses one — otherwise extend the existing test pattern) for `readinessStep()` in `apps/dashboard/src/lib/ticketWorkflowStatus.js` covering:
  - `ready_candidate` + warnings → step status `READY_CANDIDATE`, not `BLOCKED`.
  - Completed ticket (downstream state ≥ `PLAN_APPROVED`) → readiness shown as passed, no re-blocking.

## Excluded

- Any change to the workflow engine states `PLAN_REVIEW_NEEDED`, `PLAN_APPROVED`, `PLAN_FIX_REQUIRED` or to `run_step.py` transitions.
- Any change to `TicketApprovalService` business logic, the approval API, or approval persistence schema.
- Any change to `ExecutionRulesEngine` rule definitions or their evaluation outcomes.
- Refactor or relocation of `TicketExecutionEligibility` (only a clarifying comment is added).
- Renaming the `ready_to_take` status or altering its promotion semantics from `ready_candidate`.
- Adding new readiness checks beyond what is required to enforce the entry-prerequisite contract.
- Backfilling or migrating existing `ticket_readiness` rows — the next evaluation will overwrite them.

## Acceptance criteria

- `TicketReadinessEvaluator` produces blocking reasons only from intelligence completeness and unmet dependencies; every other concern is a warning or is ignored.
- A unit test asserts that *no* blocking reason ever contains the substrings `approval`, `plan review`, `execution rule`, or `ready_to_take` (case-insensitive).
- For a ticket whose intelligence flags `requires_human_plan_review=1` and has no approval yet, the readiness payload returns `readiness_status="ready_candidate"`, `blocking_reasons=[]`, and a `warnings` list containing `"Human plan review may be required later"`.
- For a ticket whose intelligence additionally flags future execution approval, the warnings list also contains `"Human execution approval may be required later"`.
- The dashboard timeline renders the readiness step as `READY_CANDIDATE` (not `BLOCKED`) when only warnings are present; the global summary is not `BLOCKED` in that case.
- For a completed ticket (workflow state ≥ `PLAN_APPROVED`), the readiness step in the timeline is rendered as passed and is not re-flagged as blocked.
- The existing assertion in `tests/test_ticket_readiness_evaluator.py:152` and `tests/test_ticket_readiness_api.py:140` (that `"Human plan approval missing"` is absent from blockers) still passes.
- All previously passing tests in `tests/test_ticket_readiness_evaluator.py`, `tests/test_ticket_readiness_api.py`, and `tests/test_ticket_readiness_db.py` still pass.
- `PLAN_REVIEW_NEEDED` / `PLAN_APPROVED` / `PLAN_FIX_REQUIRED` transitions in `run_step.py` are unchanged (verified by absence of diff in that file and by existing workflow tests still passing).
- Eligibility's `"Human plan approval required"` message remains reachable through the eligibility endpoint/panel, and is not surfaced inside the readiness step of the timeline.
