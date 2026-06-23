## Summary

Implementation strictly follows the approved plan.

### Changes

**`tools/agent_runner/ticket_operations.py`**
- `_handle_reset_to_planning`: `new_state` changed from `"PLAN_FIX_REQUIRED"` → `"INIT"`. The planner can now restart cleanly without `_collect_fix_artifacts` requiring an archived `plan.md`.
- `_handle_reset_to_coding`: `new_state` changed from `"IMPLEMENTATION_FIX_REQUIRED"` → `"PLAN_APPROVED"` (the deterministic predecessor of the `coder` step). Same symmetric bug.
- `_RESET_TO_CODING_ARTIFACTS` now also archives `implementation-output.md` so a stale coder output is not left behind when the next coder run starts.

**`tests/test_ticket_operations.py`**
- `test_reset_to_planning_archives_and_sets_state` and `test_reset_to_coding_preserves_plan`: assertions updated to the new states (`INIT`, `PLAN_APPROVED`) and the archived `implementation-output.md`.
- New: `test_reset_to_planning_restarts_planner_lifecycle` (asserts state, missing `plan.md`, and `TRANSITIONS["INIT"]`).
- New: `test_reset_to_coding_restarts_coder_lifecycle` (asserts state, preserved `plan.md`, archived `implementation-output.md`, and `TRANSITIONS["PLAN_APPROVED"]`).
- New: `test_plan_fix_required_still_works_when_artifacts_exist` (regression — `_collect_fix_artifacts` still resolves planner/review/fix paths when the legitimate fix loop runs).

**`tests/test_control_api_operations.py`**
- Renamed `test_post_reset_to_planning_writes_plan_fix_required` → `test_post_reset_to_planning_writes_init`.
- New: `test_post_reset_to_coding_writes_plan_approved` covering the route-layer transition for the symmetric fix.

### Verifications
- `pytest tests/test_ticket_operations.py tests/test_control_api_operations.py` — 37 passed.
- `pytest tests/test_planner_recovery.py tests/test_run_ticket_clean_gate.py tests/test_fix_artifact.py` — 22 passed (no regression in the fix-artifact / planner-recovery paths).

### Limits / assumptions
- The plan flagged that historical `runs/*/archive/*/reset.json` files retain their old `new_state` values; no migration is included, as called out in the plan's "Excluded" section.
- The dashboard UI label "Reset ticket to planning" was left untouched; the operation still resets planning, only the resulting runner state changes.
