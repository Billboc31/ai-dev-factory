# Tester Report — T223

## Scope

Validate that the implementation of T223 (project-level option to disable the
Human Plan Approval gate) satisfies every acceptance criterion of the ticket.

## Commands executed

```
python -m pytest tests/test_run_ticket_plan_auto_approve.py \
                 tests/test_execution_rules_engine.py \
                 tests/test_execution_rules_api.py \
                 tests/test_execution_rules_pipeline_untouched.py \
                 tests/test_ticket_approval_service.py -v
```

→ 62 passed in 2.04s

```
npx vitest run tests/ProjectRulesPanel.test.jsx tests/TicketDetailPage.test.jsx
```

→ 2 files / 12 tests passed in 714 ms

```
python -m pytest tests/test_execution_rules_db.py \
                 tests/test_execution_rules_approval_isolation.py \
                 tests/test_ticket_eligibility_api.py \
                 tests/test_human_approval.py
```

→ 37 passed, 2 failed (both in `test_ticket_eligibility_api.py`, see Regressions)

## Acceptance criteria check

| # | Criterion | Status | Evidence |
| - | --------- | ------ | -------- |
| 1 | New project-level runtime setting exists | pass | `RULE_REGISTRY["require_human_plan_approval"]` at `tools/agent_runner/execution_rules_engine.py:243` — `RuleSpec` with description matching the ticket copy. Rule is persisted via existing `project_execution_rules` table (`tools/agent_runner/runtime_db.py:139`). |
| 2 | Default value is true | pass | `default_enabled=True` at `execution_rules_engine.py:250`. Verified by `test_get_rules_returns_registry_defaults_when_empty` (`tests/test_execution_rules_api.py:96`) and `test_require_human_plan_approval_registered_and_default_enabled` (`tests/test_execution_rules_engine.py`). |
| 3 | Setting can be changed from Project Settings | pass | Exposed through existing `GET/PUT /projects/{id}/rules` endpoints (`services/control_api/routes/rules.py`) and rendered by the existing `ProjectRulesPanel` component. `test_put_rules_roundtrips_require_human_plan_approval` (`tests/test_execution_rules_api.py:138`) round-trips PUT (enabled=false) → GET → PUT `reset_defaults` → GET (enabled=true). Dashboard test `ProjectRulesPanel.test.jsx` asserts the new rule renders with its key, description and toggle. |
| 4 | Changing the setting does not require restarting the application | pass | `is_human_plan_approval_required` reads via `_resolve_effective_rules` on every planner post-step call (`execution_rules_engine.py:331-349`); no cached module-level state. `test_put_rules_roundtrips_require_human_plan_approval` confirms the API round-trip is live in-process without any restart hook. |
| 5 | When disabled, tickets do not wait for manual plan approval | pass | `_maybe_auto_approve_plan` in `tools/agent_runner/run_ticket.py:910-968` is wired at `run_ticket.py:1312` right after the planner transitions to `PLAN_REVIEW_NEEDED`. When the rule is disabled it (a) calls `auto_approve_plan`, (b) writes `PLAN_APPROVED` via `save_state`, (c) appends the workflow-journal entry. Verified by `test_auto_approve_fires_when_gate_disabled` (`tests/test_run_ticket_plan_auto_approve.py:89`). |
| 6 | The generated plan is still persisted | pass | The helper only runs *after* `_checkpoint_planner_artifacts` has already written `plan.md` to `runs/<ticket>/plan.md` (checkpoint call precedes the state-transition block in the planner branch). No code path removes or overwrites the artifact. Plan is committed alongside code by the existing auto-commit block. |
| 7 | Automatic approvals distinguishable from manual approvals in UI and database | pass | **DB**: `auto_approve_plan` (`tools/agent_runner/ticket_approval_service.py:149-172`) inserts `approval_type="plan"`, `approval_status="approved"`, `approved_by="SYSTEM"`, `approval_comment="PROJECT_SETTING"`. Manual plan approvals still flow through `apply_human_approval` and do NOT write a ticket-approvals row, so the presence of a `plan` row with `approved_by='SYSTEM'` is an unambiguous marker. **UI**: `TicketDetailPage.jsx:342-350` computes `planAutoApproved` and renders the `Auto-approved (project setting)` badge (`TicketDetailPage.jsx:460-468`) while hiding the manual "Approve Plan / Request Plan Fix" buttons (`TicketDetailPage.jsx:471-476`). Covered by both branches of `TicketDetailPage.test.jsx > TicketDetailPage — plan approval badge`. |
| 8 | All other workflow gates remain unchanged | pass | `test_run_ticket_only_reads_plan_approval_rule` (`tests/test_execution_rules_pipeline_untouched.py`) grep-asserts that `run_ticket.py` reads only `require_human_plan_approval` from the engine (no other rule leaks in). Ticket Intelligence, Global Dependency Analysis, Readiness, Dispatcher, Human Execution Approval and the existing `HUMAN_APPROVAL_TRANSITIONS` map (`run_ticket.py:974-980`) are byte-identical to `main` — no branch of the state machine other than `planner → PLAN_REVIEW_NEEDED` is touched. `test_execution_rules_pipeline_untouched.py::test_no_other_pipeline_module_imports_engine` confirms no new consumer was added. |
| 9 | Existing projects continue to behave exactly as before by default | pass | Default `enabled=True` ⇒ `is_human_plan_approval_required` returns `True` ⇒ `_maybe_auto_approve_plan` returns `None` and state stays `PLAN_REVIEW_NEEDED`. Verified by `test_auto_approve_skipped_when_gate_enabled` and `test_is_human_plan_approval_required_default_when_no_row`. The helper also falls back to `True` on any exception (import failure, DB lookup failure, engine exception) — see the exception branches at `run_ticket.py:926-946` — preserving the safe default. |

## Detailed behaviour verified

- **Registry entry**: `execution_rules_engine.py:243-253` — description matches the ticket-mandated help text.
- **Helper contract**: `is_human_plan_approval_required(db_path, project_id)` returns `True` when `project_id is None`, `db_path is None`, or any resolution raises (`execution_rules_engine.py:340-349`) — safe default is always to require human approval.
- **Idempotency**: `auto_approve_plan` returns the existing row when the latest `plan` approval is already `approved` (`ticket_approval_service.py:160-162`). Verified by `test_auto_approve_plan_is_idempotent`.
- **Approval isolation**: `test_auto_approve_plan_does_not_touch_execution_row` confirms the plan row does not affect the `execution` approval lifecycle — the two `approval_type` values are strictly independent.
- **DB comment**: `runtime_db.py:120-123` documents the two supported `approval_type` values (`execution`, `plan`) with no schema change (column is `TEXT` with no CHECK constraint).
- **Journal + log**: on auto-approve, `_append_workflow_journal` writes the transition and `_log_runtime` emits `"auto-approve: plan approval gate disabled for project=…"` and `"auto-run: transition PLAN_REVIEW_NEEDED → PLAN_APPROVED (auto, PROJECT_SETTING)"` (`run_ticket.py:950-967`), providing an audit trail beyond the DB row.
- **Project resolution**: `_resolve_project_id_from_state` reads `state["project_id"]` first, then falls back to `PROJECT_NAME` env var (mirrors `run_daemon.py`). Verified by `test_auto_approve_falls_back_to_env_project_name`.
- **API safety**: `test_put_rules_unknown_key_rejected` and `test_put_rules_rejects_negative_cost` confirm the existing input validator (`_validate_rule_input`) still enforces the whitelist and threshold rules — adding a new key did not weaken validation.
- **UI panel**: `TicketDetailPage.test.jsx` covers both the SYSTEM-approved branch (badge rendered, manual buttons hidden) and the human-approved branch (badge absent, manual buttons visible), and confirms the Implementation Approval buttons remain visible in both cases.
- **Documentation**: `docs/ai/workflow.md:240-250` documents the new toggle, the DB fields it writes, and the API surface used to change it.

## Regressions observed

- `tests/test_ticket_eligibility_api.py::test_eligibility_blocked_by_execution_approval` and
  `tests/test_ticket_eligibility_api.py::test_eligibility_module_does_not_import_scheduler` fail.
  - Both failures reproduce on `main` at commit `4963aa7c` with identical assertion output.
  - Neither `tools/agent_runner/ticket_execution_eligibility.py` nor `tests/test_ticket_eligibility_api.py` is modified on the T223 branch (`git log main..HEAD -- <files>` is empty).
  - **Conclusion**: pre-existing failures on `main`, unrelated to T223. Not attributable to this branch.
- No other regression across the 62 T223-focused Python tests, the 12 dashboard tests, or the 37 companion Python tests.

## Limitations

- Automated coverage only. I did not run the dashboard against a live control API and did not exercise the toggle end-to-end from the browser.
- Postgres backend not exercised — SQLite is the only storage backend covered by the 62 T223 tests. The rule storage path reuses the same `project_execution_rules` schema already mirrored in `runtime_db_pg.py`, so the behaviour should carry over, but this was verified by inspection only.
- The T223 branch is behind `main` (`main` gained `4963aa7c` "Wire MAX_WORKERS from runtime settings into daemon spawn." which is not on the branch — visible as an inverted diff on `services/control_api/services/daemon_manager.py`, `services/supervisor/main.py`, `tools/agent_runner/runtime_settings.py`). These are NOT changes made by T223; they are unrelated commits on `main` that will need to be merged/rebased before shipping. Flagging for the merge step, not a defect of the implementation.
- The engine still lists `block_when_human_review_required` (a documented deprecated no-op). Untouched by T223; noted for context.

## Verdict

All nine acceptance criteria pass. Every T223-focused Python test (62) and every relevant dashboard test (12) is green. The two failing tests in the companion suite are pre-existing failures on `main` that live in files this branch does not touch.

**Result: VALIDATED**
