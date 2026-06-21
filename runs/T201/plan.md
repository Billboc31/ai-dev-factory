The plan in `runs/T201/plan.md` is now a standalone implementation document — not a narrative about a plan.

It uses the four mandatory level-2 headings (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`) and addresses both fix instructions:

- **Real plan content, not a report.** Every section gives concrete instructions: DDL for both DB backends, the engine's public surface (function-by-function), API route shapes with status codes, frontend file paths and prop shapes, the three test files and what each verifies.
- **`require_human_approval` aligned with T199.** §3 of `## Included` and acceptance criterion #3 both pin the rule to `compute_execution_eligibility(...) == "ready_to_take"` via a `get_execution_approval_state` wrapper, and a grep check forbids direct `ticket_approvals` access.
- **Explicit default policy.** `DEFAULT_RULES` is given as a literal: 4 enabled (`require_ticket_intelligence`, `require_readiness_candidate`, `require_human_approval`, `block_when_human_review_required`) + 2 disabled threshold rules (`max_estimated_cost_usd`, `max_difficulty`). Acceptance criterion #4 makes this verifiable.
- **Scheduler isolation enforced.** `## Excluded` names the specific files that must not change, and criterion #10 grep-checks it.

Plan is grounded in the actual repo: routes mirror `intelligence.py`/`readiness.py`/`approvals.py`, panel mirrors sibling panels, tests mirror the existing `test_ticket_readiness_*` triplet.
