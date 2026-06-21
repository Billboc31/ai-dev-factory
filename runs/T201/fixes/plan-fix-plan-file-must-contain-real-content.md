# Plan fix — `runs/T201/plan.md` must contain the actual implementation plan

## Problem

`runs/T201/plan.md` still does not contain the implementation plan itself.

The file currently contains a narrative describing what the plan supposedly contains.

Example:

```text
Replaced the summary placeholder...
Key points covered:
...
```

This is still a report about the plan.

It is not the plan.

The coder cannot reliably implement T201 from this document.

## Required correction

Completely replace the contents of:

```text
runs/T201/plan.md
```

with the actual implementation plan.

The file itself must contain detailed implementation instructions.

The file must not contain sentences such as:

```text
The plan covers...
The plan was rewritten...
Key points covered...
```

## Required structure

The document must contain real sections such as:

```markdown
# T201 Execution Rules Engine

## Objective
...

## Included
...

## Database changes
...

## Backend implementation
...

## API
...

## Frontend
...

## Tests
...

## Excluded
...

## Acceptance criteria
...
```

## Minimum implementation details

The plan must explicitly describe:

- database schema changes
- migrations
- runtime_db.py changes
- runtime_db_pg.py changes
- `execution_rules_engine.py`
- supported rules
- evaluation algorithm
- persistence flow
- API routes
- dashboard changes
- test files

The plan must describe implementation steps, not summarize them.

## Human approval rule reminder

The plan must explicitly state:

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

or equivalent abstraction.

Direct inspection of approval tables remains forbidden.

## Acceptance criteria reminder

The plan file itself must contain complete acceptance criteria.

A reviewer must be able to approve the implementation by reading only:

```text
runs/T201/plan.md
```

without consulting additional notes or summaries.

## Review verdict

PLAN_FIX_REQUIRED until `runs/T201/plan.md` becomes a complete standalone implementation plan.
