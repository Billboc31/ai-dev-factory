# T201 — T201 - Add Execution Rules Engine and policy-based ticket governance

**Source**: GitHub Issue #258

## Description

# T200 - Add Execution Rules Engine and policy-based ticket governance

## Context

AI Dev Factory now supports:

- Ticket Intelligence
- Ticket Readiness Evaluation
- Human Approval Workflow

The next step is to introduce a configurable Rules Engine.

The Rules Engine decides whether a ticket may progress through the autonomous factory according to project policies.

This component does not execute tickets.

It only evaluates rules and produces decisions.

```text
Ticket
↓
Intelligence
↓
Readiness
↓
Human Approval
↓
Rules Engine
↓
ELIGIBLE / BLOCKED
```

## Goals

Create a generic project-level Rules Engine capable of evaluating execution policies.

Rules must be configurable per project.

The engine must explain every decision.

Example:

```text
ELIGIBLE
All execution rules satisfied.
```

or

```text
BLOCKED
Rule R-004 failed
Human approval required.
```

## Non-goals

Do not:

- start execution automatically
- dispatch workers
- reserve workers
- reorder queues
- implement scheduler changes
- launch daemons

The engine is advisory only.

## Database

Create:

```text
project_execution_rules
```

Suggested fields:

```text
project_id
rule_key
enabled
configuration_json
created_at
updated_at
```

Create:

```text
ticket_rule_evaluation
```

Suggested fields:

```text
ticket_id
project_id
eligibility_status
failed_rules_json
passed_rules_json
warnings_json
evaluated_at
created_at
updated_at
```

## Initial supported rules

### Require readiness candidate

```text
readiness_status == ready_candidate
```

### Require human approval

```text
approval_status == ready_to_take
```

### Require Ticket Intelligence

```text
analysis_status == completed
```

### Maximum estimated AI cost

Example:

```text
max_cost_usd = 0.50
```

Tickets exceeding the limit become blocked.

### Maximum difficulty

Example:

```text
difficulty <= 7
```

### Human review mandatory

Block tickets when:

```text
requires_human_plan_review == true
```

and no approval exists.

## Rules evaluator

Create:

```text
tools/agent_runner/execution_rules_engine.py
```

Responsibilities:

1. Load project rules.
2. Load ticket intelligence.
3. Load readiness state.
4. Load approval state.
5. Evaluate all enabled rules.
6. Persist evaluation.

Suggested output:

```json
{
  "eligibility_status": "blocked",
  "failed_rules": [
    "require_human_approval"
  ],
  "warnings": []
}
```

## API

Add:

```text
GET /projects/{project_id}/rules
PUT /projects/{project_id}/rules
GET /tickets/{ticket_id}/rule-evaluation
POST /tickets/{ticket_id}/evaluate-rules
```

Rule evaluation should run asynchronously and return 202 Accepted.

## Frontend

Add:

```text
Project Rules page
```

Allow enabling/disabling rules and editing thresholds.

Add:

```text
Ticket Rule Evaluation panel
```

Display:

- eligibility status
- failed rules
- warnings
- evaluation date

## Acceptance criteria

- Rules are configurable per project.
- Rule evaluations are persisted.
- Failed rules block eligibility.
- Every decision contains an explanation.
- API exposes rule configuration and evaluations.
- Dashboard displays project rules and ticket evaluations.
- Scheduler and execution pipeline remain unchanged.
- Existing test suite continues to pass.
