No out-of-scope changes. The implementation is tightly scoped to `tools/agent_runner/ticket_operations.py`, the two test files, and workflow artifacts.

---

# Review — T207 (Implementation)

## Verdict

The implementation is faithful to the approved plan, the root cause is correctly diagnosed, and the fix is the minimal change set.

## Correctness vs. ticket

- **Bug fix** (`_handle_reset_to_planning`, `ticket_operations.py:363`): `new_state` is now `"INIT"`. `TRANSITIONS["INIT"] == ("planner", True, ["PLAN_REVIEW_NEEDED"])` and `auto_run` only enters the `_collect_fix_artifacts` branch for `PLAN_FIX_REQUIRED`/`IMPLEMENTATION_FIX_REQUIRED` (`run_ticket.py:1112`), so the `fix artifact missing: runs/<ticket>/plan.md` error path is no longer reachable after reset. Matches the ticket's "Expected behavior" lifecycle exactly.
- **Symmetric fix on `reset_to_coding`** (`ticket_operations.py:404`): `new_state` is now `"PLAN_APPROVED"` (deterministic predecessor of `coder`). `implementation-output.md` was added to `_RESET_TO_CODING_ARTIFACTS` so a stale coder output is not carried into the next coder run. This addresses the ticket's `### Similar operations` audit ask and the related acceptance criterion.
- **Guardrails** unchanged: both `INIT` and `PLAN_APPROVED` are in `VALID_RUNNER_STATES` (`ticket_operations.py:36`), so the post-condition check at line 837 still passes.

## Tests

- Updated assertions in `test_reset_to_planning_archives_and_sets_state`, `test_reset_to_coding_preserves_plan`, and the route-layer test renamed to `test_post_reset_to_planning_writes_init`.
- New: `test_reset_to_planning_restarts_planner_lifecycle`, `test_reset_to_coding_restarts_coder_lifecycle`, `test_plan_fix_required_still_works_when_artifacts_exist`, `test_post_reset_to_coding_writes_plan_approved`.
- Local verification: `pytest tests/test_ticket_operations.py tests/test_control_api_operations.py` → 37 passed. `pytest tests/test_planner_recovery.py tests/test_run_ticket_clean_gate.py tests/test_fix_artifact.py` → 22 passed. No regression on the genuine `*_FIX_REQUIRED` paths.

## Scope / quality

- Diff is contained to `tools/agent_runner/ticket_operations.py` and the two test modules. No code outside the planned files was touched. No new dependencies, no incidental refactors.
- `_archive_artifacts` (`ticket_operations.py:314`) safely skips missing files, so adding `implementation-output.md` to the tuple is benign when the file is absent.
- Reset metadata (`archive/*/reset.json`) correctly records `new_state = "INIT"` / `"PLAN_APPROVED"`; historical archives are intentionally untouched (called out in the plan's "Excluded").

## Minor observations (non-blocking)

- The dashboard label "Reset ticket to planning" remains accurate; no UI text needed to change.
- Diagnostics in `tools/agent_runner/ticket_diagnostics.py:535,731` recommend `reset_to_planning` as an action — only the operation key is referenced, not the resulting state, so no follow-up is needed there.

## Acceptance criteria

All eight criteria in the ticket are satisfied — corresponding tests assert each one.

IMPLEMENTATION_APPROVED
