# Implementation review — T198 Ticket Readiness Evaluator

## Summary

The Readiness Evaluator implementation itself is well-built and faithful to the
approved plan: canonical lowercase statuses, structured `is_ticket_merged`
helper, `ticket_readiness` table in both SQLite and Postgres, advisory-only
behaviour, 202/idempotent POST, scoped React panel mounted next to the
intelligence panel, and 34/34 targeted tests pass.

However, the branch diff against `main` introduces a **scope violation that is
also a production regression** for an unrelated feature (Ticket Intelligence in
Docker). That single point must be fixed before merge. Everything else listed
below is a minor observation.

---

## Blocking issue — silent regression of commit `66165e13` (intelligence-in-Docker fix)

`git merge-base main HEAD` is `0532acd9`, which predates the recent main
commit `66165e13` ("fix(intelligence): run ticket analysis on host when API is
in Docker"). Because the T198 branch was never rebased onto current `main`, the
PR diff against `main` will *delete* that fix when merged:

- `services/supervisor/main.py`: removes the host-side
  `POST /projects/{project_id}/tickets/{ticket_id}/intelligence/analyze`
  endpoint (88 lines).
- `services/control_api/routes/intelligence.py`: removes
  `_supervisor_url`, `_needs_host_exec`, `_delegate_analyze_to_supervisor`,
  the project-id forwarding signature, and the in-route delegation branch
  (72 lines).
- `tests/test_ticket_intelligence_api.py`: removes
  `test_project_post_analyze_delegates_to_supervisor_in_docker` (15 lines).

T198 is the Readiness Evaluator. None of these intelligence-in-Docker
changes appear in `runs/T198/plan.md`, `runs/T198/fixes/...`, or
`runs/T198/implementation-output.md`. The implementation-output.md lists only
readiness-related files. So this revert is silent and unintentional — a direct
consequence of branching from an older `main`.

Impact: in the standard `docker-compose.yml` deployment where `control_api`
runs in a container without `claude`, `POST /tickets/{id}/intelligence/analyze`
will once again try to invoke `claude` inside the container and fail.
`_api_in_docker` / `AI_DEV_FACTORY_API_IN_DOCKER` is still consumed by
`services/control_api/services/daemon_manager.py` and other call sites, but
the only place that fanned out intelligence work to the host has been removed.

Required fix: rebase the T198 branch onto current `main` so the three files
above retain the post-`66165e13` content (the project-scoped delegation), then
re-run `tests/test_ticket_intelligence_api.py` to confirm
`test_project_post_analyze_delegates_to_supervisor_in_docker` still passes.
T198's own code does not need to change — it just must not co-exist with the
pre-`66165e13` versions of `routes/intelligence.py`, `services/supervisor/main.py`,
or `tests/test_ticket_intelligence_api.py`.

---

## Minor observations (non-blocking)

### 1. `_check_human_approval` silently accepts the runtime PLAN_APPROVED state

`tools/agent_runner/ticket_readiness_evaluator.py:106-116,119-139` introduces
`_state_implies_plan_approved`, which treats any ticket whose
`runs/<ticket>/state.json` is at `PLAN_APPROVED` (or any later state) as
having a human plan approval. The plan only described a marker file
(`runs/<ticket>/plan-approved.md` "or equivalent existing convention"). The
state-machine fallback is broader than what the plan described and is not
covered by a dedicated test.

Risk: the daemon itself can move a ticket to `PLAN_APPROVED` via its
agent-driven plan review path (no human in the loop), in which case the
evaluator will report `approval_check_status="passed"` and
`human_approval_present=1` for a ticket the human never approved. For an
advisory-only feature this is tolerable, but it inverts the intent of the
check.

Suggested follow-up: either (a) drop the state-implied path and rely on the
marker file alone, or (b) keep it but add a test covering this fallback and
document it as the intended convention in this codebase.

### 2. `_git_log_grep` "not_merged" answer is broad

`tools/agent_runner/ticket_merge_state.py:170-197`: when `git log main --grep
T<id>` exits 0 with empty stdout, the helper returns `not_merged` with
`source="git_fallback"`. The plan explicitly allows this. Worth noting: a
project that has *no* `main` branch will exit non-zero and correctly fall
through to `unknown`, but a project on `main` with squash-merge commit
messages that don't mention the ticket ID will produce a false `not_merged`
verdict. The plan's preferred sources (runtime DB, GitHub metadata) are
intended to absorb this risk; flagging it here so the team is aware
git-fallback verdicts should be treated as low-confidence.

### 3. `_check_dependencies` exception path collapses to "unknown"

`tools/agent_runner/ticket_readiness_evaluator.py:85-90`: any exception from
`is_ticket_merged` is mapped to `Dependency T<ID> merge state unknown` and
appended to blocking reasons, with no entry added to `warnings`. This is
consistent with the plan but loses the underlying error. Consider appending a
short warning (`f"is_ticket_merged({dep}) raised: {exc!r}"`) alongside the
blocking reason so future debugging does not require re-running the evaluator.

### 4. Project-scoped readiness routes ignore `project_id`

`services/control_api/routes/readiness.py:146-158`: the project-scoped GET and
POST handlers simply forward to the non-scoped handlers without using
`project_id`. This mirrors `routes/intelligence.py` and is acceptable today
because the app-state DB handle already carries the project context, but it
means the URL parameter is decorative. Worth a TODO comment if a future
multi-tenant flow expects the routes to actually scope by `project_id`.

### 5. Workflow artefact noise (informational only)

`runs/T198/` adds 7 planner attempt prompts (`planner-attempt-1.md` …
`planner-attempt-7.md`) plus `coder-attempt-1.md` and `prompts/` files,
totalling ~5,000 lines of generated prompts. Not a code concern — but if the
team's convention is to keep only the final accepted prompt per agent role
under version control, those earlier attempts could be pruned before merge.
(`6ec637a1` was labelled `T001:` despite carrying T198 implementation code,
which suggests the auto-commit hook mislabels checkpoints — separate
follow-up.)

---

## Verifications performed

- `pytest tests/test_ticket_readiness_db.py tests/test_ticket_merge_state.py
  tests/test_ticket_readiness_evaluator.py tests/test_ticket_readiness_api.py`
  → 34 passed.
- `pytest tests/test_ticket_intelligence_api.py` → 13 passed (note: the
  delegation-in-Docker test has been deleted in this branch, see blocking
  issue above).

---

## Decision

The Readiness Evaluator implementation is sound. The blocking concern is the
silent revert of the intelligence-in-Docker fix in `main`'s commit `66165e13`.
Rebase the branch onto current `main` (preserving `66165e13`'s changes) and the
implementation is ready to merge.

IMPLEMENTATION_FIX_REQUIRED
