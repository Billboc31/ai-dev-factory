I've reviewed the T202 implementation against the ticket, the approved plan, and the code/test diff vs main. All 25 T202-related tests pass locally.

# Review — T202 (Prevent planner meta-reports during PLAN_FIX_REQUIRED)

## Scope & plan compliance

All four pillars from the plan are delivered, and only the five files listed in `## Included` are touched:

- `prompts/generic/planner.md` — new "Artifact-only output (strict)" section near the top, applies to first-pass and rewrites (planner.md:4-13).
- `tools/agent_runner/run_step.py` — adds `_META_REPORT_OPENING_PATTERNS` (run_step.py:158-165), `META_REPORT_REASON` constant (run_step.py:169), `_looks_like_meta_report()` (run_step.py:409-460), and `artifact_type="plan"` parameter on `validate_planner_output()` (run_step.py:463). Default keeps the signature backward compatible.
- `tools/agent_runner/run_ticket.py` — `_build_fix_context_file()` now takes `current_state` and prepends an artifact-only preamble for `PLAN_FIX_REQUIRED` (run_ticket.py:804-832); `_build_planner_meta_report_retry_context()` writes the reinforcement file (run_ticket.py:849-872); planner branch retries `_call_run_step` once on meta-report and emits `runtime warning: planner_meta_report_retry` then `runtime failure: planner_invalid` on second failure (run_ticket.py:1146-1163).
- Tests added in `tests/test_validate_planner_output.py` (T201 repro, summary-heading variant, structured-plan counter-test, bullets counter-test, `artifact_type` default) and `tests/test_planner_recovery.py` (retry-once success path with log ordering + retry-context naming; retry-twice failure path).

No scope creep into coder/reviewer/tester, daemon-level retry policy, or historical `runs/T201/**`.

## Correctness

- Meta-report heuristic suppression chain (fenced code, `-`/`*` bullets, file-path tokens) gives high precision — the bullets counter-test confirms false-positive guard.
- Heading-wrapped meta-report case (`## Summary\n\nThe plan has been rewritten…`) is correctly caught: the loop in `_looks_like_meta_report` skips `#`-prefixed lines before matching the opening regex.
- Retry path is bounded to exactly one extra call; second meta-report falls through to the existing `if reasons:` block and exits rc=2 — no infinite loop. Confirmed by `test_planner_meta_report_retry_failing_again_logs_planner_invalid`.
- `_checkpoint_planner_artifacts` runs after both the first and the retried planner call, so the rejected attempt is preserved in git history per the ticket's intent.
- Signature compatibility verified by `test_artifact_type_default_is_plan`; existing tests in both files still pass unchanged.

## Code quality & safety

- Regexes are narrow and curated; no risk of catastrophic backtracking.
- Logging strings (`runtime warning: planner_meta_report_retry`, `runtime failure: planner_invalid`) follow the existing `runtime failure: <class>` convention so the daemon's classifier (`re.search(r"runtime failure: (\w+)", ...)`) keeps working.
- No secrets, no destructive ops, no permission changes.
- Comments justify the *why* (suppression signals, backward-compat reason for `artifact_type`) rather than restating the code.

## Non-blocking observations

1. **Retry drops the original fix context.** The retry call passes `retry_context` (artifact-only reinforcement) as `extra_context_file`, replacing the previous output + review + fix-instructions bundle. The plan explicitly allowed either "a small file generated next to the fix context, or appended to it" — the implementation chose the standalone variant, which is plan-compliant. Practical risk: the retried planner regenerates the plan without seeing the review feedback that triggered the fix in the first place; it may converge on a different (still valid) plan that doesn't address the original critique. Worth a small follow-up to append the preamble to the fix context instead.
2. **Ordered-list bullets not suppressed.** `_looks_like_meta_report` treats only `- ` and `* ` as bullet signals. A meta-report-shaped file that happened to use `1. `, `2. ` would still trigger the heuristic. Meta-reports rarely use ordered lists, so this is a marginal blind spot, not a correctness issue.
3. **Double checkpoint per cycle when retry succeeds.** Cosmetic — `_checkpoint_planner_artifacts` is idempotent (swallows the "nothing staged" error), but the git log will show two near-identical checkpoint commits when the retry path fires.

## Acceptance criteria

- T201-style meta-report opening → rejected with `META_REPORT_REASON` ✅ (`test_meta_report_t201_repro_is_rejected`).
- Structured plan that *mentions* a meta-report phrase → still passes ✅ (`test_meta_report_phrase_inside_structured_plan_is_not_rejected`).
- `prompts/generic/planner.md` contains the artifact-only wording, and the fix-mode context prepends it with the concrete `runs/<ticket>/plan.md` path ✅.
- Retry-once path produces `runtime warning: planner_meta_report_retry` before `runtime failure: planner_invalid`, covered by both recovery tests ✅.
- All pre-existing validator/recovery tests still pass ✅ (25/25).
- `artifact_type` default keeps existing callers working ✅.

## Verdict

The implementation matches the plan, addresses every acceptance criterion, and stays within scope. The retry-context concern is real but explicitly allowed by the plan and easy to follow up on later.

IMPLEMENTATION_APPROVED
