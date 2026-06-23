# Tester Report — T207

## Verdict

**VALIDATED.** The implementation fixes the `reset_to_planning` bug, applies the same correction to `reset_to_coding`, and adds the regression coverage required by the plan. All target test suites pass.

## Commands executed

```bash
python -m pytest tests/test_ticket_operations.py tests/test_control_api_operations.py -v
# → 37 passed in 1.59s

python -m pytest tests/test_planner_recovery.py tests/test_run_ticket_clean_gate.py tests/test_fix_artifact.py -v
# → 22 passed in 0.07s
```

Additional verifications:

- Direct inspection of `tools/agent_runner/run_ticket.py` `auto_run()` — confirmed that `_collect_fix_artifacts` is reached only via the conditional at L46 `if current_state in {"PLAN_FIX_REQUIRED", "IMPLEMENTATION_FIX_REQUIRED"}`. With reset → `INIT`, this branch is unreachable, so the original error `fix artifact missing: runs/<ticket>/plan.md` cannot recur.
- `TRANSITIONS["INIT"] == ("planner", True, ["PLAN_REVIEW_NEEDED"])` and `TRANSITIONS["PLAN_APPROVED"] == ("coder", True, ["IMPLEMENTATION_REVIEW_NEEDED"])` — confirmed in the live module.

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `reset_to_planning` archives previous planning artifacts. | PASS | `_RESET_TO_PLANNING_ARTIFACTS` unchanged (`plan.md`, `reviews`, `tests`, `conflict`, `retry-state.json`); `test_reset_to_planning_archives_and_sets_state` asserts the archive root contains `plan.md` and `reviews/` and that `run_dir/plan.md` no longer exists. |
| 2 | The ticket enters a valid restart state. | PASS | `new_state = "INIT"` in `_handle_reset_to_planning` (ticket_operations.py:363); `INIT ∈ VALID_RUNNER_STATES`; `test_reset_to_planning_never_writes_planning_state` and `test_no_handler_returns_forbidden_state_names_in_results` both pass. |
| 3 | Recommended implementation uses `INIT` for full planning restart. | PASS | Confirmed by `state.json["state"] == "INIT"` and `meta["new_state"] == "INIT"` (test_reset_to_planning_archives_and_sets_state). |
| 4 | Next auto-run executes planner successfully. | PASS | `TRANSITIONS["INIT"] == ("planner", True, ["PLAN_REVIEW_NEEDED"])` — asserted by `test_reset_to_planning_restarts_planner_lifecycle`. The `_collect_fix_artifacts` branch in `auto_run` is gated by `current_state ∈ {PLAN_FIX_REQUIRED, IMPLEMENTATION_FIX_REQUIRED}` and is therefore unreachable for state `INIT`. |
| 5 | Planner regenerates `runs/<ticket>/plan.md`. | PASS (structural) | The planner step writes `plan.md` as part of its normal execution; the precondition (no `plan.md` after reset, state=INIT, planner is the next step) is verified end-to-end. No code path between reset and planner execution requires a pre-existing `plan.md`. |
| 6 | No `fix artifact missing: runs/<ticket>/plan.md` error occurs after reset. | PASS | The conditional `if current_state in {"PLAN_FIX_REQUIRED", "IMPLEMENTATION_FIX_REQUIRED"}` (run_ticket.py:46) is the only entry point for `_collect_fix_artifacts`; state=`INIT` bypasses it entirely. |
| 7 | Existing PLAN_FIX_REQUIRED workflows continue to work. | PASS | `test_plan_fix_required_still_works_when_artifacts_exist` exercises `_collect_fix_artifacts` with a populated `plan.md` + `reviews/plan-review-1.md` + `fixes/plan-fix-1.md`, and the helper returns the three resolved paths. Regression coverage in `test_fix_artifact.py` (10 tests) also passes. |
| 8 | `reset_to_coding` has been reviewed for similar issues. | PASS | Symmetric bug confirmed and corrected: `new_state = "PLAN_APPROVED"` (ticket_operations.py:404), and `_RESET_TO_CODING_ARTIFACTS` now archives `implementation-output.md` so a stale coder output does not collide with the regenerated one. `test_reset_to_coding_preserves_plan`, `test_reset_to_coding_restarts_coder_lifecycle`, and `test_post_reset_to_coding_writes_plan_approved` all pass. |
| 9 | Existing test suite continues to pass. | PASS for in-scope suites. The 28 pre-existing failures in `test_control_api_artifacts.py`, `test_control_api_endpoints.py`, and `test_control_api_subprocess.py` are unrelated test-isolation defects (the tests inspect the worktree's actual `runs/` dir instead of `tmp_path`). Verified to fail identically on baseline `142b5867` (the immediate pre-T207 commit) — and the count is actually 2 *lower* on the T207 branch than on baseline (28 vs. 30). |

## Regressions observed

None attributable to T207.

Pre-existing, unrelated failures (confirmed on baseline `142b5867`):

- `tests/test_control_api_artifacts.py::test_list_tickets_empty` (and 2 sibling asserts) — `list_tickets()` reads the real `runs/` directory instead of `tmp_path/"runs"`.
- `tests/test_control_api_endpoints.py` (~12 failures) — same root cause: project-root resolution leaks into the test fixtures.
- `tests/test_control_api_subprocess.py` (~12 failures) — same root cause; the subprocess fixture similarly inherits the worktree's project root.

These are test-harness defects that long predate this ticket and are out of scope.

## Blocking issues found

None.

## Limits of validation

- The "planner regenerates `plan.md`" criterion (#5) was validated structurally (preconditions correct, deterministic transition, planner is the next step). A full live planner invocation requires the Anthropic API and a real runtime context, which is outside the unit-test scope. The plan's analysis (planner runs deterministically from INIT, requires no prior artifact) is consistent with the `TRANSITIONS` table and the planner's own contract.
- The pre-existing `test_control_api_*` failures could not be reproduced inside a clean `tmp_path` because the underlying `artifact_reader.list_tickets()` path resolution falls back to the project root regardless of the fixture's `tmp_path`. Out of T207 scope.
- No migration of historical `runs/*/archive/*/reset.json` files (explicitly excluded by the plan); old archives retain their original `new_state` value. Acceptable per the plan.
