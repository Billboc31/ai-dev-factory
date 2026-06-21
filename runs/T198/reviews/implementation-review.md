The previous IMPLEMENTATION_FIX_REQUIRED (silent revert of main's `66165e13`) is resolved — the branch reapplied the fix as commit `21432e5a`, and `git diff main HEAD` for the three affected files is now empty. Writing the review.

# Implementation review — T198 Ticket Readiness Evaluator

## Verdict

The blocker from review-attempt-2 (silent revert of main's `66165e13` intelligence-in-Docker fix) has been fixed: the T198 branch reapplied that exact commit as `21432e5a`, and `git diff main HEAD -- services/control_api/routes/intelligence.py services/supervisor/main.py tests/test_ticket_intelligence_api.py` is now empty. The deleted test `test_project_post_analyze_delegates_to_supervisor_in_docker` is back at `tests/test_ticket_intelligence_api.py:266`.

The remaining T198 code is faithful to the approved plan: canonical lowercase enum (`not_started|queued|running|ready_candidate|blocked|failed`), no uppercase forms leaking into DB/API/tests; `ticket_readiness` table in both SQLite (`tools/agent_runner/runtime_db.py:98-113`) and Postgres (`tools/agent_runner/runtime_db_pg.py:132-149`) with the same column set; `MergeCheckResult` dataclass and three-tier resolution (runtime DB → `gh pr view` → `git log --grep`) in `tools/agent_runner/ticket_merge_state.py`; evaluator (`tools/agent_runner/ticket_readiness_evaluator.py`) never raises and persists `readiness_status="failed"` on unexpected errors; advisory 202/idempotent POST in `services/control_api/routes/readiness.py`; React panel with sub-check badges, blocking-reasons block, freshness sha, and re-evaluate button.

Targeted tests: 34/34 readiness + 14/14 intelligence-API (48/48). With Postgres env unset, the broader 74-test focused superset also passes. The 111 failures in the full 1638-test sweep (`test_sandbox_worktree`, `test_ticket_timeline`, `test_traefik_separation`, `test_runtime_db` when `RUNTIME_DB_BACKEND=postgres` is set, etc.) are pre-existing and unrelated to T198 files; the same failures reproduce on `main`.

## Acceptance criteria check

All eleven criteria from the plan are met. Spot checks: `tests/test_ticket_readiness_evaluator.py:151-180` validates `ready_candidate=1` + non-null `evaluated_at` and `main_sha_when_evaluated` on the happy path; `tests/test_ticket_merge_state.py:92-106` validates `source="runtime_db"` precedence; `test_ticket_readiness_api.py:182-197` validates idempotent POST while running. No call to `git log --grep` from the evaluator (confirmed by grep).

## Minor observations (non-blocking, carry over)

- `tools/agent_runner/ticket_readiness_evaluator.py:106-116` — `_state_implies_plan_approved` accepts the daemon's `PLAN_APPROVED` runtime state as a proxy for human approval. The plan only described the marker file `runs/<ticket>/plan-approved.md`. Because the daemon's planner/reviewer agents can drive the ticket to `PLAN_APPROVED` without a human, this fallback can produce a false-positive `approval_check_status="passed"`. Advisory-only, so not a merge blocker — but worth a follow-up issue when readiness becomes a real gate.
- `ticket_readiness_evaluator.py:86-90` — exceptions from `is_ticket_merged` collapse to `Dependency T<id> merge state unknown` with no entry in `warnings`. Consider preserving the exception there for debuggability.
- `services/control_api/routes/readiness.py:142-158` — project-scoped routes accept `project_id` but ignore it (same pattern as `intelligence.py`); fine today, worth a TODO.
- `runs/T198/prompts/planner-attempt-{1..7}.md` and `coder-attempt-{1..2}.md` (~5,000 lines of generated prompts) are committed. If the convention is final-only, prune in a future cleanup.
- Checkpoint commit `6ec637a1` carries T198 code under a `T001:` label — auto-commit-hook mislabel, separate follow-up.

IMPLEMENTATION_APPROVED
