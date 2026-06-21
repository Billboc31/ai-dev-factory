# Implementation review — T198 Ticket Readiness Evaluator

The Readiness Evaluator code itself is well-built and matches the approved plan: canonical lowercase statuses, structured `is_ticket_merged` helper, `ticket_readiness` table in both SQLite and Postgres, advisory-only behaviour, 202/idempotent POST, scoped React panel, 34/34 targeted tests pass.

## Blocking issue — silent revert of `main`'s commit `66165e13`

`git merge-base main HEAD` = `0532acd9`, which predates main's recent fix `66165e13` (*"fix(intelligence): run ticket analysis on host when API is in Docker"*). The T198 branch was never rebased on current `main`, so its diff against `main` **deletes** that fix when merged:

- `services/supervisor/main.py:2194-2287` — the host-side `POST /projects/{project_id}/tickets/{ticket_id}/intelligence/analyze` endpoint (−88 lines).
- `services/control_api/routes/intelligence.py` — `_supervisor_url`, `_needs_host_exec`, `_delegate_analyze_to_supervisor`, the project-id forwarding signature, and the in-route delegation branch (−72 lines).
- `tests/test_ticket_intelligence_api.py` — `test_project_post_analyze_delegates_to_supervisor_in_docker` (−15 lines).

None of these appear in the plan, the fix instructions, or `implementation-output.md` — the revert is unintentional. Impact: in the standard `docker-compose.yml` deployment the control_api container has no `claude` CLI, so `POST /tickets/{id}/intelligence/analyze` will fail again.

**Required fix:** rebase the branch onto current `main` so the three files above retain the post-`66165e13` content. T198's own code does not need to change.

## Minor observations
- `_check_human_approval` accepts the runtime `PLAN_APPROVED` state as a proxy for human approval; the plan only described a marker file (`runs/<id>/plan-approved.md`). The daemon's own agent-driven plan review can set this state without a human, so the fallback can produce false positives. Not blocking for advisory mode.
- `_check_dependencies` swallows `is_ticket_merged` exceptions into `Dependency T<id> merge state unknown` with no `warnings` entry — consider preserving the exception in `warnings`.
- Project-scoped readiness routes ignore `project_id` (mirrors `intelligence.py`); fine today, worth a TODO.
- `runs/T198/prompts/planner-attempt-1.md … attempt-7.md` and `coder-attempt-1.md` (~5,000 lines of generated prompts) are committed; prune if convention is final-only.
- Checkpoint commit `6ec637a1` carrying T198 code is labelled `T001:` — looks like an auto-commit hook mislabel, separate follow-up.

The review file is at `runs/T198/reviews/review-attempt-2.md`.

IMPLEMENTATION_FIX_REQUIRED
