Plan updated. All four review points addressed in `runs/T201/plan.md`:

1. **`require_human_approval` uses canonical `ready_to_take`** — now goes through `ticket_approval_service.compute_execution_eligibility(db_path, ticket_id)` (verified to exist at `tools/agent_runner/ticket_approval_service.py:148`), with the optional `get_execution_approval_state` wrapper as documented fallback.
2. **Result mapping made explicit** — `ready_to_take` passes; `ready_candidate`, `blocked`, `not_started`/unknown each fail with a specific human-readable reason.
3. **`block_when_human_review_required` realigned** — now also reads via `compute_execution_eligibility`, no direct approval-table inspection.
4. **Default policy listed explicitly** — four enabled rules and two disabled threshold rules, named one by one (no more ambiguous "four `require_*`" wording).
5. **Test description updated** — `require_human_approval` is tested through the canonical eligibility contract; approval-table internals must not be the rule contract.
6. **Acceptance criteria extended** — three new criteria covering canonical state usage, deterministic default policy, and human-readable failure reasons; advisory-only constraint reiterated.
