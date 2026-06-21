All 25 tests pass.

## Summary of changes

Implemented per the approved plan to prevent the planner from returning meta-reports during `PLAN_FIX_REQUIRED` (committed in `f409fb3a` by the daemon auto-commit):

**Files modified:**
- `prompts/generic/planner.md` — added an "Artifact-only output (strict)" section at the top with the verbatim "rewrite the artifact itself, do not describe modifications, do not produce a status report" wording. Applies to both initial plans and rewrites.
- `tools/agent_runner/run_step.py` — added `_looks_like_meta_report()` helper, `META_REPORT_REASON` constant, and the new `artifact_type: str = "plan"` parameter on `validate_planner_output` (backward compatible). The heuristic only fires when the opening line matches a curated regex set AND the file has no fenced code block, bullet list, or file path.
- `tools/agent_runner/run_ticket.py` — `_build_fix_context_file` now takes `current_state` and prepends an artifact-only preamble for `PLAN_FIX_REQUIRED`. Added `_build_planner_meta_report_retry_context()` and a single-retry path in the planner branch that runs `_call_run_step` again with the reinforcement context, logs `runtime warning: planner_meta_report_retry`, and falls back to `runtime failure: planner_invalid` (rc=2) on second failure.

**Tests added:**
- `tests/test_validate_planner_output.py` — 5 new tests: T201 repro, summary-heading variant, structured-plan counter-test, bullets counter-test, artifact_type default.
- `tests/test_planner_recovery.py` — 2 new tests covering the retry-once success path (log ordering + retry context naming) and the retry-failure path (planner_invalid + exactly one retry).

All 25 T202-related tests pass. The 116 pre-existing failures in the broader suite (sandbox, traefik, runtime_db, timeline, etc.) are unrelated and reproduce on the parent commit without my changes.
