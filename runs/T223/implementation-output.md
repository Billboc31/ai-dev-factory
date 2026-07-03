Implementation complete. All changes match the approved plan:

## Summary

Added a project-level toggle (`require_human_plan_approval` rule) that lets projects skip the Human Plan Approval gate. Default remains `enabled=True`. When disabled, `run_ticket.py` auto-transitions `PLAN_REVIEW_NEEDED → PLAN_APPROVED` after the planner step, persists an auditable `plan / approved / SYSTEM / PROJECT_SETTING` row in `ticket_approvals`, and lets implementation continue immediately. `plan.md` is still persisted via the existing checkpoint.

## Files modified
- `tools/agent_runner/execution_rules_engine.py` — new rule + `is_human_plan_approval_required` helper.
- `tools/agent_runner/ticket_approval_service.py` — new idempotent `auto_approve_plan`.
- `tools/agent_runner/runtime_db.py` — DDL comment listing `execution` / `plan` `approval_type`s.
- `tools/agent_runner/run_ticket.py` — `_maybe_auto_approve_plan` helper wired at the single post-planner transition.
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — "Auto-approved (project setting)" badge + hides manual plan buttons when the latest `plan` approval is by `SYSTEM`.
- `docs/ai/workflow.md` — new "Auto-approbation du plan" section.
- `tests/test_execution_rules_engine.py`, `tests/test_execution_rules_api.py`, `tests/test_ticket_approval_service.py`, `tests/test_execution_rules_pipeline_untouched.py` — updated.
- `tests/test_run_ticket_plan_auto_approve.py` — new.
- `apps/dashboard/tests/ProjectRulesPanel.test.jsx`, `apps/dashboard/tests/TicketDetailPage.test.jsx` — updated.
- `runs/T223/implementation-output.md` — implementation report with `IMPLEMENTATION_COMPLETE` keyword.

## Verifications
- 122 Python tests across engine / approvals / runner / API pass together.
- Dashboard tests for `ProjectRulesPanel` (6) and `TicketDetailPage` (6) pass; both pre-existing suites + the new plan-badge cases.
- Pre-existing unrelated failures (`test_eligibility_blocked_by_execution_approval`, dashboard full-suite `ERR_WORKER_OUT_OF_MEMORY`) also fail on `main`.

IMPLEMENTATION_COMPLETE
