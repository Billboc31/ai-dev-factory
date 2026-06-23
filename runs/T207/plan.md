I have enough context to write the plan. The bug is clear: `_handle_reset_to_planning` archives `plan.md` then writes `PLAN_FIX_REQUIRED`, but `_collect_fix_artifacts` requires `plan.md` to exist for that state. The fix is to transition to `INIT` (the planner step runs deterministically from `INIT` without requiring prior artifacts). `reset_to_coding` has the analogous bug — it archives `reviews/` (which includes the implementation review) while transitioning to `IMPLEMENTATION_FIX_REQUIRED`, which then needs that review back.

## Objective
Fix `reset_to_planning` so it restarts the planning lifecycle from a clean state. Currently it archives `plan.md` and writes `PLAN_FIX_REQUIRED`, but that state requires `plan.md` to exist, producing `fix artifact missing: runs/<ticket>/plan.md` on the next auto-run. The handler must instead transition to `INIT`, the state already wired to run the planner deterministically without any previous artifact. Apply the same correction to `reset_to_coding`, which suffers from the symmetric bug (it archives the implementation review while writing `IMPLEMENTATION_FIX_REQUIRED`, a state that requires that review).

## Included

- `tools/agent_runner/ticket_operations.py`
  - In `_handle_reset_to_planning` (~line 353): replace `new_state = "PLAN_FIX_REQUIRED"` with `new_state = "INIT"`. The archived artifacts set `_RESET_TO_PLANNING_ARTIFACTS` stays unchanged (`plan.md`, `reviews`, `tests`, `conflict`, `retry-state.json`).
  - In `_handle_reset_to_coding` (~line 388): replace `new_state = "IMPLEMENTATION_FIX_REQUIRED"` with `new_state = "PLAN_APPROVED"` (the state from which `TRANSITIONS` runs the `coder` deterministically). Extend `_RESET_TO_CODING_ARTIFACTS` to also include `implementation-output.md` so the regenerated implementation does not collide with a stale archived output.
  - `INIT` and `PLAN_APPROVED` already belong to `VALID_RUNNER_STATES`, so the post-condition guardrail in `execute_operation` continues to accept them without further change.

- `tests/test_ticket_operations.py`
  - Update `test_reset_to_planning_archives_and_sets_state`: assert the new `state.json["state"] == "INIT"` and `meta["new_state"] == "INIT"`. Keep the archive-content assertions (`plan.md`, `reviews/` moved into the archive directory).
  - Update `test_reset_to_planning_never_writes_planning_state`: the assertion `state != "PLANNING"` and `state in VALID_RUNNER_STATES` still holds, no functional change needed beyond confirming `INIT` is acceptable.
  - Update `test_reset_to_coding_preserves_plan`: assert `state.json["state"] == "IMPLEMENTATION_FIX_REQUIRED"` → `"PLAN_APPROVED"`, and `meta["new_state"] == "PLAN_APPROVED"`. Adjust the `implementation-output.md` setup so the test verifies that the file is archived (the new artifact in `_RESET_TO_CODING_ARTIFACTS`). Keep the assertion that `plan.md` is preserved.
  - Update `test_no_handler_returns_forbidden_state_names_in_results`: still valid (asserts `state` ∉ `FORBIDDEN_RUNNER_STATES`), just confirms `INIT` / `PLAN_APPROVED` pass.
  - Add `test_reset_to_planning_restarts_planner_lifecycle`: after `reset_to_planning`, simulate the next auto-run prerequisites — confirm `state.json["state"] == "INIT"`, confirm `_collect_fix_artifacts` is *not* invoked for `INIT` (i.e. the function is only triggered for `PLAN_FIX_REQUIRED` / `IMPLEMENTATION_FIX_REQUIRED` in `run_ticket.auto_run`). Concretely: import `run_ticket._collect_fix_artifacts`, build a `state` dict with `state="INIT"`, and verify the `auto_run` control flow at `run_ticket.py:1112` only enters the fix-artifact branch for the two `*_FIX_REQUIRED` states. A simple unit test calling `_collect_fix_artifacts` with `state="INIT"` should not be added (the helper is only called from inside the conditional); instead assert that after reset the run dir contains no `plan.md` and that `INIT` is the deterministic predecessor of the `planner` step in `TRANSITIONS["INIT"]`.
  - Add `test_reset_to_coding_restarts_coder_lifecycle`: after `reset_to_coding`, `state == "PLAN_APPROVED"`, `plan.md` preserved, no `implementation-output.md` in the run dir, and `TRANSITIONS["PLAN_APPROVED"]` is `("coder", True, ["IMPLEMENTATION_REVIEW_NEEDED"])`.
  - Add `test_plan_fix_required_still_works_when_artifacts_exist`: regression for the legitimate fix loop — build a run dir with `plan.md`, `reviews/plan-review-x.md`, `fixes/plan-fix-1.md`, state `PLAN_FIX_REQUIRED`. Call `run_ticket._collect_fix_artifacts` (imported by path) and assert it returns the three artifacts without raising.

- `tests/test_control_api_operations.py`
  - Rename `test_post_reset_to_planning_writes_plan_fix_required` → `test_post_reset_to_planning_writes_init` and assert `state["state"] == "INIT"`.
  - Add `test_post_reset_to_coding_writes_plan_approved` covering the route layer transition (analogous to the renamed one).

- No dashboard change is needed: `apps/dashboard/tests/TicketOperationsPanel.test.jsx` only references `operation_key: 'reset_to_planning'` as a label; it does not encode the resulting runner state.

## Excluded

- No change to the `TRANSITIONS` table in `run_ticket.py`. `INIT → planner → PLAN_REVIEW_NEEDED` and `PLAN_APPROVED → coder → IMPLEMENTATION_REVIEW_NEEDED` already exist and are correct.
- No change to `_collect_fix_artifacts` in `run_ticket.py`. Its behaviour for the genuine `PLAN_FIX_REQUIRED` / `IMPLEMENTATION_FIX_REQUIRED` workflows must remain intact (covered by the regression test above).
- No change to the planner prompt, planner validation, or `validate_planner_output`. The bug is upstream of planner execution.
- No change to `_RESET_TO_PLANNING_ARTIFACTS` content (still archives `plan.md`, `reviews`, `tests`, `conflict`, `retry-state.json`). Only `_RESET_TO_CODING_ARTIFACTS` gains `implementation-output.md`.
- No new operation key, no new safety level, no new audit field. The handlers, registry, and confirmation requirements (`requires_typed_ticket_id`, `requires_reason`) remain unchanged.
- No migration of historical `reset.json` metadata files in `runs/*/archive/*/reset.json`. Old archives keep their original `new_state` value.
- No change to the dashboard UI copy. The label "Reset ticket to planning" remains accurate.

## Acceptance criteria

- After `reset_to_planning` with a valid reason and typed ticket id, `runs/<ticket>/state.json["state"] == "INIT"` and the archive directory's `reset.json` records `new_state == "INIT"`.
- After `reset_to_planning`, `runs/<ticket>/plan.md` no longer exists and the archived `plan.md` lives under `runs/<ticket>/archive/<ts>/plan.md`.
- A subsequent `run_ticket.py --auto` run reaches the planner step without raising `fix artifact missing: runs/<ticket>/plan.md`; the `_collect_fix_artifacts` branch in `auto_run` is not entered for state `INIT`.
- After `reset_to_coding` with a valid reason and typed ticket id, `runs/<ticket>/state.json["state"] == "PLAN_APPROVED"`, `runs/<ticket>/plan.md` is preserved, and `runs/<ticket>/implementation-output.md` is archived (not present in the run dir).
- The legitimate `PLAN_FIX_REQUIRED` workflow continues to work: when `plan.md`, a `reviews/plan-review*.md`, and a `fixes/plan-fix-*.md` exist, `_collect_fix_artifacts` returns the three paths without error.
- All existing tests in `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py` pass after the assertion updates listed above.
- New tests `test_reset_to_planning_restarts_planner_lifecycle`, `test_reset_to_coding_restarts_coder_lifecycle`, `test_plan_fix_required_still_works_when_artifacts_exist`, and `test_post_reset_to_coding_writes_plan_approved` pass.
- `VALID_RUNNER_STATES` is unchanged and the post-condition guardrail in `execute_operation` accepts the new outputs (`INIT`, `PLAN_APPROVED`) without raising.
- `pytest tests/test_ticket_operations.py tests/test_control_api_operations.py` exits with code 0.
