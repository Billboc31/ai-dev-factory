# Plan fix — discard current `plan.md` and rewrite the complete plan from scratch

## Current problem

`runs/T201/plan.md` is still invalid.

It is not an implementation plan.

It is a meta-report that says the plan was rewritten.

The current content starts with sentences like:

```text
The plan in `runs/T201/plan.md` is now a standalone implementation document...
It uses the four mandatory headings...
Key points covered...
```

This is forbidden.

The planner must stop describing what the plan contains and must write the actual plan content itself.

## Mandatory action

Completely discard the current contents of:

```text
runs/T201/plan.md
```

Then rewrite the file from scratch.

The output written to `runs/T201/plan.md` must start directly with:

```markdown
## Objective
```

or, if a title is allowed by the runner, with:

```markdown
# T201 Execution Rules Engine

## Objective
```

But it must not start with any of these phrases:

```text
The plan...
This plan...
Plan rewritten...
Key points covered...
Replaced the summary...
I updated...
I changed...
```

## Required exact structure

The final `runs/T201/plan.md` must contain the real plan with exactly these level-2 headings:

```markdown
## Objective
## Included
## Excluded
## Acceptance criteria
```

The file may contain level-3 headings under `## Included`, for example:

```markdown
### Database
### Backend
### API
### Frontend
### Tests
```

But the four level-2 headings above must be present as real Markdown headings and in that order.

## Content that must appear in the actual plan

The rewritten `runs/T201/plan.md` must include concrete implementation instructions for:

### Database

- Add `project_execution_rules` to both SQLite and PostgreSQL runtime DB initialisation.
- Add `ticket_rule_evaluation` to both SQLite and PostgreSQL runtime DB initialisation.
- Add helpers for reading/upserting project rules.
- Add helpers for reading/upserting ticket rule evaluations.

### Rules engine

Create:

```text
tools/agent_runner/execution_rules_engine.py
```

The plan must describe:

- `RULE_REGISTRY`
- `evaluate_ticket(project_id, ticket_id)`
- loading ticket intelligence
- loading ticket readiness
- loading execution approval state
- applying only enabled rules
- persisting `eligible` or `blocked` result
- storing passed rules, failed rules, warnings, and human-readable reasons

### Supported rules

The plan must explicitly list these six rules:

```text
require_ticket_intelligence
require_readiness_candidate
require_human_approval
block_when_human_review_required
max_estimated_cost_usd
max_difficulty
```

### Human approval rule

This is mandatory:

```text
require_human_approval
```

must be based on canonical execution eligibility:

```text
ready_to_take
```

through:

```text
compute_execution_eligibility(...)
```

or a wrapper such as:

```text
get_execution_approval_state(...)
```

The plan must explicitly forbid direct rule-level reads of:

```text
ticket_approvals.approval_status == approved
```

### Default policy

The plan must explicitly state:

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

### API

The plan must include:

```text
GET /projects/{project_id}/rules
PUT /projects/{project_id}/rules
GET /tickets/{ticket_id}/rule-evaluation
POST /tickets/{ticket_id}/evaluate-rules
```

The POST endpoint must return `202 Accepted` and run evaluation asynchronously.

### Frontend

The plan must include:

- Project Rules page
- Ticket Rule Evaluation panel
- API client helper
- status rendering
- failed rule reasons
- warnings
- last evaluation date

### Tests

The plan must include tests for:

- DB schema and round-trip persistence
- each rule pass/fail behavior
- `require_human_approval` using `ready_to_take`
- thresholds enabled/disabled
- default policy fallback
- API GET/PUT/POST behavior
- no scheduler / worker / daemon changes

## Strong invalid-output examples

The final plan is invalid if it contains only a report like:

```text
The plan now includes database changes...
```

or:

```text
Key points covered:
- DB schema
- API routes
```

or:

```text
Replaced the placeholder with a complete plan...
```

The final plan must contain the actual implementation details directly.

## Review verdict

PLAN_FIX_REQUIRED until `runs/T201/plan.md` is fully rewritten from scratch as the real implementation plan, not a summary or report about the plan.
