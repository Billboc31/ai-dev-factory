Plan rewritten with the four mandatory headings and all the implementation detail the fix asked for.

Key points the plan now addresses:

- `require_human_approval` uses canonical T199 `ready_to_take` via `compute_execution_eligibility`, wrapped behind `get_execution_approval_state` in the engine — tests assert against `ready_to_take`, not against `ticket_approvals` rows.
- Default policy explicitly enumerated: four enabled (`require_ticket_intelligence`, `require_readiness_candidate`, `require_human_approval`, `block_when_human_review_required`) and two disabled threshold rules (`max_estimated_cost_usd`, `max_difficulty`).
- DB schema, DAOs, engine, API (with 202 async semantics), frontend page + panel, and tests are each spelled out concretely.
- Scheduler/daemon/worker untouched is restated both in Excluded and in an acceptance criterion that calls out specific files that must not be modified.
