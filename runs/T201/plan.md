Replaced the summary placeholder in `runs/T201/plan.md` with a complete implementation plan organized under the four mandatory headings (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`).

Key points covered:
- DB schema additions in both `runtime_db.py` and `runtime_db_pg.py` for `project_execution_rules` and `ticket_rule_evaluation` with unique/index constraints.
- New `execution_rules_engine.py` with explicit public surface, load order, and pure rule functions.
- `require_human_approval` resolved exclusively through `get_execution_approval_state(...) → compute_execution_eligibility(...) == "ready_to_take"`; an acceptance criterion forbids direct `ticket_approvals` access (verifiable by grep).
- Explicit default policy: four enabled rules and two disabled threshold rules.
- API routes including `POST /tickets/{id}/evaluate-rules` returning **202** via `BackgroundTasks`.
- Frontend page + panel under `apps/dashboard/src/`.
- Three new test files explicitly enumerated.
- Excluded section names the scheduler/daemon/worker files that must not change, and an acceptance criterion makes that verifiable.
