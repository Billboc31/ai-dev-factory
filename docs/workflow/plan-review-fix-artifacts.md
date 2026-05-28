# Plan review and fix artifact conventions

This document defines the canonical artifact structure used when reviewing and fixing ticket plans in `ai-dev-factory`.

The goal is to make plan feedback traceable, implementation-safe, and consistent across human and AI agents.

## Canonical locations

For a ticket `TXXX`, the canonical plan lives at:

```text
runs/TXXX/plan.md
```

Example:

```text
runs/T154/plan.md
```

Plan review artifacts live under:

```text
runs/TXXX/reviews/
```

Required plan fix artifacts live under:

```text
runs/TXXX/fixes/
```

## Review files

The default plan review file is:

```text
runs/TXXX/reviews/plan-review.md
```

Optional specialized reviews may be added when useful:

```text
runs/TXXX/reviews/plan-review-runtime.md
runs/TXXX/reviews/plan-review-security.md
runs/TXXX/reviews/plan-review-ux.md
```

A review file describes the review decision, risks, required fixes, optional suggestions, architecture concerns, and scope concerns.

A review file must not rewrite the plan and must not contain implementation code.

Expected structure:

```markdown
# Plan review — TXXX

Decision:
- PLAN_APPROVED
- PLAN_APPROVED_WITH_MINOR_FIXES
- PLAN_REJECTED

## What is good

...

## Required fixes

...

## Optional improvements

...

## Architecture concerns

...

## Scope concerns

...
```

## Fix files

Required plan adjustments must be written as incremental fix artifacts:

```text
runs/TXXX/fixes/plan-fix-1.md
runs/TXXX/fixes/plan-fix-2.md
```

Fix files exist to describe exact requested adjustments without rewriting the whole plan.

Expected structure:

```markdown
# Plan fix — TXXX

## Objective

...

## Required adjustments

### 1. ...

...

## Scope unchanged

...
```

## Important distinction

Reviews are not fixes.

Reviews describe:

- approval state
- risks
- architectural analysis
- high-level concerns
- optional suggestions

Fixes describe:

- concrete requested modifications
- exact required adjustments
- implementation-safe clarifications
- scope that must remain unchanged

## Expected workflow

The standard workflow is:

```text
issue
→ runs/TXXX/plan.md
→ runs/TXXX/reviews/plan-review.md
→ runs/TXXX/fixes/plan-fix-1.md
→ update plan if required
→ implementation
```

Avoid:

```text
random chat feedback
lost context
untracked review comments
```

## Constraints

Do not:

- overwrite `plan.md` during review
- rewrite the entire plan for small fixes
- mix implementation code into review artifacts
- put runtime logs into `reviews/`
- put long architecture discussions directly into implementation commits

Do:

- keep reviews concise
- keep fixes incremental
- preserve ticket history
- make review reasoning traceable
- keep implementation notes separate from approval decisions

## Decision semantics

Use one of the following decisions in plan reviews:

- `PLAN_APPROVED`: the plan can move to implementation as-is.
- `PLAN_APPROVED_WITH_MINOR_FIXES`: the plan is broadly acceptable, but concrete clarifications/fixes should be captured before or during implementation.
- `PLAN_REJECTED`: the plan should not move to implementation until the required fixes are addressed.

## Future evolution

This structure is intentionally extensible for:

- multiple reviewer agents
- reviewer specialization
- automatic review aggregation
- review status tracking
- reviewer voting
- implementation blockers
- architecture approval gates
