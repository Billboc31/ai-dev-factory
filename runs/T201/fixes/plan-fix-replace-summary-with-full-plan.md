# Plan fix — replace summary placeholder with a complete implementation plan

## Problem

The current `runs/T201/plan.md` does not contain an actual implementation plan.

Instead, it contains a short status/report message indicating that the plan was rewritten.

Example:

```text
Plan rewritten at runs/T201/plan.md ...
```

This is not a valid implementation plan and will not provide sufficient guidance to the coder.

## Required correction

Replace the entire contents of:

```text
runs/T201/plan.md
```

with a complete implementation plan.

The file must not contain meta-comments such as:

```text
plan rewritten
status report
summary only
```

The file itself must be the authoritative implementation plan.

## Mandatory sections

The plan must contain at least:

```markdown
## Objective
## Included
## Excluded
## Acceptance criteria
```

## Expected implementation details

The plan should explicitly describe:

### Database

- `project_execution_rules`
- `ticket_rule_evaluation`
- migrations
- indexes if required

### Backend services

Create:

```text
tools/agent_runner/execution_rules_engine.py
```

Responsibilities:

1. Load project rules.
2. Load ticket intelligence.
3. Load readiness state.
4. Load execution approval state.
5. Evaluate enabled rules.
6. Persist evaluation results.

### Rule evaluation

Document all supported rules:

```text
require_ticket_intelligence
require_readiness_candidate
require_human_approval
block_when_human_review_required
max_estimated_cost_usd
max_difficulty
```

The plan must explicitly state that:

```text
require_human_approval
```

uses canonical:

```text
ready_to_take
```

through:

```text
compute_execution_eligibility(...)
```

or:

```text
get_execution_approval_state(...)
```

and never directly inspects approval tables.

### API

Document:

```text
GET /projects/{project_id}/rules
PUT /projects/{project_id}/rules
GET /tickets/{ticket_id}/rule-evaluation
POST /tickets/{ticket_id}/evaluate-rules
```

including asynchronous evaluation behavior.

### Frontend

Document:

```text
Project Rules page
Ticket Rule Evaluation panel
```

including editable rule configuration.

### Tests

Explicitly describe tests for:

- rule evaluation success
- rule evaluation failure
- ready_to_take approval checks
- threshold rules
- persistence
- API endpoints

## Non-goals reminder

The plan must explicitly exclude:

- scheduler changes
- worker dispatch
- queue ordering
- automatic execution
- daemon lifecycle changes

The Rules Engine remains advisory only.

## Review verdict

PLAN_FIX_REQUIRED until `runs/T201/plan.md` is replaced by a complete implementation plan instead of a summary placeholder.
