## Objective

Add a project-level toggle that lets a project skip the Human Plan Approval
gate. Default behaviour (approval required) is preserved. When disabled, the
runner auto-transitions `PLAN_REVIEW_NEEDED → PLAN_APPROVED` right after the
planner finishes, persists an auditable auto-approval row, and lets the
implementation continue without waiting for a human. All other gates
(Intelligence, Dependencies, Readiness, Dispatcher, Human Execution Approval,
tests, CI) remain untouched.

## Included

### Project setting (project-level rule)

- `tools/agent_runner/execution_rules_engine.py`:
  - Register a new rule in `RULE_REGISTRY` with key
    `require_human_plan_approval`, `default_enabled=True`,
    `default_configuration={}`, description matching the ticket copy
    ("Require Human Plan Approval on generated plans. When disabled, plans are
    auto-approved after generation.").
  - Its evaluator is a documented no-op (`RuleResult(passed=True, …)`) — same
    pattern as `block_when_human_review_required`. The rule is enforced by the
    runner state machine, not by the eligibility engine.
  - Export a helper `is_human_plan_approval_required(db_path, project_id)`
    that consults `_resolve_effective_rules(project_id, db_path)` for the
    `require_human_plan_approval` entry and falls back to
    `spec.default_enabled` when no project row exists or `project_id is
    None`. Any exception falls back to `True` (safe default).

The setting name `PROJECT_REQUIRE_HUMAN_PLAN_APPROVAL` from the ticket is
implemented as this project-scoped rule so it reuses the existing
`project_execution_rules` table, `GET/PUT /projects/{project_id}/rules`
endpoints and `ProjectRulesPanel` UI — the only pattern in the codebase
currently used for per-project toggles. No new table, no new API surface, no
new UI page.

### Approval persistence (audit)

- `tools/agent_runner/ticket_approval_service.py`:
  - Add `auto_approve_plan(db_path, ticket_id, *, reason="PROJECT_SETTING")`
    that appends a row to `ticket_approvals` with
    `approval_type="plan"`, `approval_status="approved"`,
    `approved_by="SYSTEM"`, `approval_comment=reason`. It is idempotent: if
    the latest `plan` approval for the ticket is already `approved` it
    returns the existing row without inserting a duplicate.
  - No change to the `execution` approval flow — plan and execution approvals
    are stored as distinct `approval_type` values in the same table.
- `tools/agent_runner/runtime_db.py`:
  - No schema change (the table's `approval_type` column is `TEXT` and
    already supports arbitrary values). Add a brief comment near the
    `ticket_approvals` DDL block noting the two supported values
    (`execution`, `plan`).

### Runner enforcement

- `tools/agent_runner/run_ticket.py`:
  - After a successful planner step, once
    `save_state(ticket_id, {**state, "state": "PLAN_REVIEW_NEEDED"})` has been
    written and the workflow journal entry appended, call a new helper
    `_maybe_auto_approve_plan(ticket_id, state, project_id, project_root)`.
  - Helper behaviour:
    - Resolve `project_id` from `state["project_id"]` (or existing runtime
      resolution used elsewhere in the file — `os.environ.get("PROJECT_NAME")`
      as fallback, same as `run_daemon.py`).
    - Call `execution_rules_engine.is_human_plan_approval_required(db_path,
      project_id)`. If it returns `True`, do nothing (current behaviour).
    - If `False`:
      - Call `ticket_approval_service.auto_approve_plan(db_path, ticket_id)`.
      - Update state to `PLAN_APPROVED` via `save_state`.
      - Append a workflow journal entry:
        `_append_workflow_journal(ticket_id, "PLAN_REVIEW_NEEDED", "auto-approve", "PLAN_APPROVED")`.
      - Emit two log lines via `_log_runtime`:
        `"auto-approve: plan approval gate disabled for project=<id>"` and
        `"auto-run: transition PLAN_REVIEW_NEEDED → PLAN_APPROVED (auto, PROJECT_SETTING)"`.
  - The helper is only invoked from the planner branch (not from
    `PLAN_FIX_REQUIRED` re-runs? — it *is* invoked from both, because the
    state machine sends both `INIT → PLAN_REVIEW_NEEDED` and
    `PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED` through the same planner branch
    at `run_ticket.py:1179`).
  - The plan artifact (`plan.md`) is unchanged and still persisted by the
    existing `_checkpoint_planner_artifacts` call — auditability requirement
    "generated plan is still persisted" is satisfied without new code.
  - The daemon's `HUMAN_GATE_STATES` handling in `run_daemon.py` is not
    changed: when the auto-approval fires the ticket leaves
    `PLAN_REVIEW_NEEDED` before the next daemon poll sees it, so it will be
    picked up as `PLAN_APPROVED` (`AUTO_RUNNABLE_STATES`) on the following
    tick.

### Manual approval path is untouched

- No change to the CLI `--approve-plan` / `--request-plan-fix` flags or their
  `HUMAN_APPROVAL_TRANSITIONS` mapping. Human approval keeps writing state
  through the existing path; only automatic approval creates a `plan` row in
  `ticket_approvals`.

### API surface

- No new endpoints. The rule is exposed through the existing
  `GET /projects/{project_id}/rules` and
  `PUT /projects/{project_id}/rules` because `RULE_REGISTRY` is the single
  source of truth walked by `_get_effective_rules`. `_validate_rule_input` in
  `services/control_api/routes/rules.py` needs no branch (no threshold
  configuration).
- `services/control_api/routes/approvals.py`: no change needed if it already
  serialises `list_ticket_approvals` rows generically. If it currently
  filters on `approval_type == "execution"`, extend the filter to include
  `"plan"` so the API surfaces auto-approvals for the UI to consume. Update
  the corresponding Pydantic model if `approval_type` is enumerated.

### UI

- `apps/dashboard/src/components/ProjectRulesPanel.jsx`: no code change
  required — the panel iterates the effective rules returned by the API and
  renders a checkbox + description per rule, which already handles the new
  `require_human_plan_approval` entry. Verify the help text sent from the
  backend (`RuleSpec.description`) matches the ticket copy:
  `"Require Human Plan Approval. When disabled, implementation plans are
  automatically approved after generation. Useful for demos and fully
  automated projects."`
- `apps/dashboard/src/components/HumanApprovalPanel.jsx` (or the equivalent
  component that renders the plan-review checkpoint — locate by grepping for
  `PLAN_REVIEW_NEEDED` under `apps/dashboard/src`): when the latest `plan`
  approval row has `approved_by === "SYSTEM"`, render a distinct badge
  `Auto-approved (project setting)` in place of the "Approved by …" label,
  and keep the manual "Approve plan / Request plan fix" buttons hidden. If
  no such panel currently reads plan approvals, add a minimal read-only
  block driven by the extended approvals endpoint.

### Documentation

- `docs/ai/workflow.md`: append a short note that the `PLAN_REVIEW_NEEDED`
  gate can be waived per project via the `require_human_plan_approval` rule,
  producing a `plan` approval row with `approved_by=SYSTEM` and
  `approval_comment="PROJECT_SETTING"`. One paragraph, no diagram change.

### Tests

- `tests/test_execution_rules_engine.py`: assert the new rule is registered
  with `default_enabled=True`, its evaluator returns `passed=True`, and
  `is_human_plan_approval_required` returns `True` when no project row
  exists and `False` when a project row disables it.
- `tests/test_ticket_approval_service.py` (or a new
  `tests/test_ticket_approval_service_plan.py`): unit-test
  `auto_approve_plan` — one insert on first call, idempotent on repeated
  calls, `approval_type="plan"`, `approved_by="SYSTEM"`,
  `approval_comment="PROJECT_SETTING"`.
- `tests/test_run_ticket_plan_auto_approve.py` (new): drive `run_ticket.py`
  with a stubbed planner subprocess and verify:
  - Default (rule enabled): state stays `PLAN_REVIEW_NEEDED`, no `plan` row
    in `ticket_approvals`.
  - Rule disabled for the project: state becomes `PLAN_APPROVED`, exactly
    one `plan` row exists with the expected audit fields, workflow journal
    contains the auto-approve transition.
- `tests/test_ticket_eligibility_api.py` or
  `tests/test_execution_rules_api.py`: confirm the project rules API round-
  trips the new key (GET returns it, PUT persists and re-reads it,
  `reset_defaults` restores `enabled=True`).
- Dashboard: update `apps/dashboard/tests/ProjectRulesPanel.test.jsx` to
  assert the new rule renders. Add a small test on the plan-approval
  component that renders the `Auto-approved` badge when the latest `plan`
  approval has `approved_by === "SYSTEM"`.

## Excluded

- No global (non-project) toggle for plan approval. The setting lives on the
  project only, per the ticket ("per project"). Adding a global mirror in
  `runtime_settings.py` is out of scope.
- No change to Ticket Intelligence, Global Dependency Analysis, Readiness,
  Dispatcher scheduling, Human Execution Approval, tests, or CI — the ticket
  explicitly prohibits touching them.
- No retroactive auto-approval of tickets already in `PLAN_REVIEW_NEEDED`
  when the setting is flipped. New behaviour applies from the next planner
  run onward; existing waiting tickets are still resolved manually or by
  re-running the planner. Backfilling is not requested.
- No new `pending` plan approval row on plan generation when the gate is
  enabled — the human path already relies on the state machine, and adding
  a symmetric pending row is not requested.
- No schema migration on `ticket_approvals` (column is `TEXT`, no CHECK
  constraint to update).
- No UI change to the readiness / execution-eligibility panels: those keep
  gating on the `execution` approval type only.
- No new secrets, environment variables, or migration scripts.

## Acceptance criteria

- `execution_rules_engine.RULE_REGISTRY["require_human_plan_approval"]`
  exists with `default_enabled=True` and description text matching the
  ticket copy.
- `GET /projects/{project_id}/rules` returns the new rule for any project;
  `PUT` persists a disabled state and a follow-up `GET` reflects it without
  restarting the control API (satisfies "applied dynamically after
  configuration reload").
- With the rule at its default (enabled), running the planner on a ticket
  leaves it in `PLAN_REVIEW_NEEDED` and inserts no row of
  `approval_type="plan"` in `ticket_approvals`.
- With the rule disabled for a project, running the planner on a ticket
  ends the run in state `PLAN_APPROVED`, and `ticket_approvals` contains
  exactly one row with
  `(approval_type="plan", approval_status="approved",
  approved_by="SYSTEM", approval_comment="PROJECT_SETTING")`.
- Re-invoking `auto_approve_plan` on the same ticket does not insert a
  second row.
- The plan artifact `runs/<ticket>/plan.md` is still written and committed
  by `_checkpoint_planner_artifacts` in both branches.
- `docs/ai/workflow.md` documents the new toggle.
- All existing tests still pass. The dashboard renders the new rule in
  `ProjectRulesPanel` and, when the latest `plan` approval was auto-created,
  shows an `Auto-approved (project setting)` badge instead of the manual
  approver name.
- Grep confirms no other pipeline gate reads
  `require_human_plan_approval` — the enforcement point is uniquely
  `run_ticket.py` after the planner step.
