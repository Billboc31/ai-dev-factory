# Plan fix — align `require_human_approval` with canonical `ready_to_take`

## Required plan update

Update `runs/T201/plan.md` before implementation starts.

The plan is directionally correct, but `require_human_approval` must be aligned with the lifecycle introduced by T199.

## 1. Use canonical execution eligibility state

Replace this rule definition:

```text
require_human_approval
→ reads latest ticket_approvals.approval_status == approved for type execution
```

with:

```text
require_human_approval
→ passes when execution eligibility is ready_to_take
```

Preferred implementation:

```python
compute_execution_eligibility(db_path, ticket_id) == "ready_to_take"
```

If `compute_execution_eligibility` is not available or not appropriate, introduce a small abstraction in the rules engine:

```python
def get_execution_approval_state(db_path: str, ticket_id: str) -> str:
    """Return canonical execution approval state such as ready_candidate, ready_to_take, blocked, unknown."""
```

The Rules Engine must not depend directly on the physical approval-table representation.

Direct reads from T199 tables may exist only behind this helper.

## 2. Rule behavior

The `require_human_approval` rule should behave as follows:

```text
ready_to_take
→ passed

ready_candidate
→ failed: Human approval required before execution

blocked
→ failed: Ticket is blocked

not_started / unknown / missing state
→ failed or warning depending on existing readiness/intelligence rule result, but must not pass
```

The exact reason text can vary, but it must be human-readable.

## 3. Default policy clarification

Replace ambiguous wording like:

```text
all four require_* rules enabled; thresholds disabled
```

with an explicit list:

```text
Default policy enables:
- require_ticket_intelligence
- require_readiness_candidate
- require_human_approval
- block_when_human_review_required

Default policy disables:
- max_estimated_cost_usd
- max_difficulty
```

This avoids confusion because `block_when_human_review_required` is not named as a `require_*` rule.

## 4. Test updates

Add or adjust tests so that:

- `require_human_approval` passes when the canonical execution state is `ready_to_take`.
- `require_human_approval` fails when the canonical execution state is `ready_candidate`.
- Tests do not assert `ticket_approvals.approval_status == approved` as the rule contract.
- The helper or abstraction is tested separately if introduced.

## 5. Non-goals reminder

This fix must not change:

- scheduler behavior
- worker dispatch
- queue ordering
- daemon state machine
- run execution lifecycle

The Rules Engine remains advisory only in this ticket.

## Updated acceptance criteria

Add acceptance criteria:

- `require_human_approval` evaluates canonical `ready_to_take` execution eligibility, not approval-table internals.
- Default project policy is explicitly listed and deterministic.
- Rule evaluation output explains failures with human-readable reasons.
