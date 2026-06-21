# T199 — Tester Report

**Ticket**: T199 — Add Human Approval Workflow and READY_TO_TAKE lifecycle
**Branch**: `ticket/T199-add-human-approval-workflow-and-ready-to-take-life`
**Verdict**: **VALIDATED**

## Commands executed

```bash
# Backend: SQLite (default — RUNTIME_DB_BACKEND=sqlite)

# 1. New T199 suite
python3 -m pytest tests/test_ticket_approval_db.py \
                  tests/test_ticket_approval_service.py \
                  tests/test_ticket_approval_api.py -v

# 2. Targeted regression (directly impacted by T199)
python3 -m pytest tests/test_ticket_readiness_db.py \
                  tests/test_ticket_readiness_evaluator.py \
                  tests/test_ticket_readiness_api.py \
                  tests/test_human_approval.py \
                  tests/test_ticket_intelligence_db.py \
                  tests/test_runtime_db.py

# 3. Broad sweep
python3 -m pytest tests/ \
  --ignore=tests/test_control_api_endpoints.py \
  --ignore=tests/test_control_api_artifacts.py \
  --ignore=tests/test_control_api_subprocess.py -q --tb=no

# 4. Pre-existing-failure verification — same files at the parent commit ea2ae883 (T198)
git worktree add /tmp/T199-baseline ea2ae883
cd /tmp/T199-baseline && python3 -m pytest <same files> --tb=no -q
```

## Results

| Suite | Result |
|---|---|
| `tests/test_ticket_approval_db.py` (9 tests) | **9 passed** |
| `tests/test_ticket_approval_service.py` (15 tests) | **15 passed** |
| `tests/test_ticket_approval_api.py` (14 tests) | **14 passed** |
| Targeted regression (readiness + intelligence + human_approval + runtime_db) | **66 / 66 passed** |
| Broad sweep (excluding 3 known-flaky files) | **1545 passed / 82 failed** |
| Baseline ea2ae883 broad sweep (same files) | **same 82 failures** |
| Net regressions introduced by T199 | **0** |

The 82 broad-sweep failures fall into two groups, **all reproduced bit-for-bit at the parent commit ea2ae883**:

- 60 failures across `test_environment_routes.py`, `test_environment_supervisor.py`, `test_host_path_mapping.py`, `test_operational_scripts.py`, `test_presync_hygiene.py`, `test_project_scoped_isolation.py`, `test_run_daemon.py`, `test_sandbox_worktree.py`, `test_ticket_timeline.py`, `test_traefik_separation.py`
- 22 failures across `tests/supervisor/test_supervisor.py`, `test_coder_autocommit_lifecycle.py`, `test_daemon_checkpoint.py`, `test_daemon_issue_polling.py`, `test_dashboard_daemon_docker_launch.py`, `test_dashboard_daemon_env.py`, `test_environment_infra_bootstrap.py`

Symptom pattern: 404s / tickets_count assertions / sandbox path leakage — consistent with running pytest from a checked-out worktree where the project's real `runs/` directory is visible to tests that expect a clean `tmp_path`. The 3 explicitly-ignored files (`test_control_api_endpoints.py`, `test_control_api_artifacts.py`, `test_control_api_subprocess.py`) exhibit the same environmental sensitivity and were also confirmed to fail identically at ea2ae883.

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Tickets may be approved or rejected for execution | **PASS** | `test_approve_happy_path_promotes_to_ready_to_take`, `test_reject_happy_path_blocks_with_reason` |
| 2 | Approval history is persisted | **PASS** | `test_history_is_append_only_never_overwritten`, `test_get_approvals_returns_history_after_decisions` |
| 3 | `READY_TO_TAKE` lifecycle state exists | **PASS** | `test_approve_on_ready_candidate_promotes_to_ready_to_take` + `compute_execution_eligibility` |
| 4 | Only `READY_CANDIDATE` tickets can be approved | **PASS** | `test_approve_without_ready_candidate_raises_invalid_state`, `test_approve_invalid_state_returns_409` |
| 5 | Rejected approvals move ticket back to `BLOCKED` with reason | **PASS** | `test_reject_on_ready_candidate_blocks_with_reason` (reason: `"Execution approval rejected by <approver>"`) |
| 6 | API exposes approval history | **PASS** | `GET /tickets/{id}/approvals` + project-scoped mount; `test_get_approvals_returns_history_after_decisions` |
| 7 | Dashboard exposes approval actions and history | **PASS** (code review) | `HumanApprovalPanel.jsx` rendered under `TicketReadinessPanel` in `TicketDetailPage.jsx:279`; Board badges + filter in `BoardPage.jsx`. **Not exercised in a browser** (see limitations). |
| 8 | Scheduler/worker behaviour unchanged | **PASS** | `grep ready_to_take\|ticket_approval` in `tools/agent_runner/run_daemon.py`, `tools/agent_runner/run_ticket.py`, `services/supervisor/` → **0 matches**. |
| 9 | Existing tests continue to pass | **PASS** | All 82 broad-sweep failures reproduced verbatim at baseline `ea2ae883`. No new regressions. Targeted regression suite (readiness/intelligence/human_approval/runtime_db, 66 tests) fully green. |

## Plan-level acceptance criteria (idempotency / 409 / 404 / re-eval / project scope)

| Criterion | Status | Evidence |
|---|---|---|
| Idempotent approve (replay returns 200, history stays at 1) | PASS | `test_approve_idempotent_returns_same_row`, `test_approve_idempotent_replay_returns_200_same_row` |
| Idempotent reject (replay returns 200, no duplicate reason) | PASS | `test_reject_idempotent_does_not_duplicate_reason`, `test_reject_idempotent_replay_does_not_duplicate_reason` |
| Contradictory transitions → 409 | PASS | `test_approve_after_reject_raises_contradictory`, `test_reject_after_approve_raises_contradictory`, `test_approve_after_reject_returns_409`, `test_reject_after_approve_returns_409` |
| Invalid state → 409 | PASS | `test_approve_with_no_readiness_row_raises_invalid_state`, `test_approve_invalid_state_returns_409` |
| Unknown ticket → 404 | PASS | `test_get_approvals_404_when_ticket_missing`, `test_approve_404_when_ticket_missing`, `test_reject_404_when_ticket_missing` |
| Re-running readiness preserves `ready_to_take` | PASS | `test_reevaluation_preserves_ready_to_take_after_approval` + `ticket_readiness_evaluator.py:212-220` |
| Project-scoped routes mounted | PASS | `test_project_scoped_get_approvals`, `test_project_scoped_approve` |

## Regressions observed

**None.** Every broad-sweep failure was reproduced identically at the parent commit ea2ae883.

## Blocking issues found

**None.**

## Limitations

- **Frontend**: `HumanApprovalPanel` and `BoardPage` readiness badges/filter verified by code review only — the dashboard was not exercised in a headless browser. The implementer flagged the same limitation. The component imports (`api.getTicketReadiness`, `api.getTicketApprovals`, `api.approveExecution`, `api.rejectExecution`) and the readiness-driven button enablement logic (`readinessStatus === 'ready_candidate'` ∨ idempotent replay) match the API contract verified by the backend tests.
- **Postgres backend**: tests ran under `RUNTIME_DB_BACKEND=sqlite` only. The Postgres rebind block exists in `runtime_db.py:685-687` and `runtime_db_pg.py` has matching `ticket_approvals` schema and helpers, but live Postgres validation was not in scope here.
- **Pre-existing broken tests**: 82 failures in the broad sweep + 11 known failures in the 3 ignored files are inherited from the baseline. Out of scope for T199; flagging for future maintenance.

## Verdict

**VALIDATED.** All 9 ticket acceptance criteria and all 7 plan-level acceptance criteria are satisfied. 38 new tests pass, no regressions introduced.
