# T207 — Fix reset_to_planning workflow to correctly restart planning lifecycle

**Source**: GitHub Issue #270

## Description

# Fix reset_to_planning workflow to correctly restart planning lifecycle

## Context

T204 introduced a guarded manual operation:

```text
reset_to_planning
```

A bug has been discovered when this operation is executed.

Current behavior:

```text
reset_to_planning
↓
archives or removes previous planning artifacts
↓
runner enters PLAN_FIX_REQUIRED
↓
auto-run starts planner
↓
runner expects runs/<ticket>/plan.md
↓
ERROR: fix artifact missing
```

Observed runtime log:

```text
auto-run start: state=PLAN_FIX_REQUIRED
auto-run: running step=planner
auto-run: fix artifact missing: runs/T205/plan.md
```

This creates an invalid recovery state.

## Problem

`reset_to_planning` is intended to restart the planning lifecycle from scratch.

However, the current implementation leaves the ticket in a state that assumes a previous plan artifact still exists.

This prevents planner execution and breaks the reset workflow.

## Goal

Ensure that:

```text
reset_to_planning
↓
archives previous planning artifacts
↓
returns ticket to a clean planning lifecycle state
↓
planner executes normally on next run
↓
a new plan.md is generated
```

## Expected behavior

Recommended lifecycle:

```text
reset_to_planning
↓
archive previous planning artifacts
↓
set state = INIT
↓
next auto-run
↓
planner executes normally
↓
runs/<ticket>/plan.md recreated
↓
PLAN_REVIEW_NEEDED
```

## Scope

Investigate:

- Ticket Operations reset logic
- runner state transitions
- planner execution prerequisites
- PLAN_FIX_REQUIRED artifact requirements
- planner validation logic

## Required changes

### Reset operation

Review:

```text
reset_to_planning
```

and ensure it transitions to a state compatible with a full planner restart.

Recommended:

```text
INIT
```

instead of:

```text
PLAN_FIX_REQUIRED
```

when the intent is to regenerate planning artifacts from scratch.

### Planner recovery

Verify that planner execution:

```text
state = INIT
```

never requires an existing:

```text
runs/<ticket>/plan.md
```

### Artifact lifecycle

Ensure:

```text
reset_to_planning
```

may safely archive or remove previous planning artifacts without breaking the next planner execution.

### Similar operations

Audit:

```text
reset_to_coding
```

and confirm that it does not suffer from the same invalid recovery behavior.

## Tests

Add tests covering:

### reset_to_planning

```text
reset_to_planning
↓
archives old artifacts
↓
state becomes INIT
↓
next auto-run executes planner
↓
new plan.md generated
```

### Missing plan artifact

Verify:

```text
state = INIT
```

works correctly when:

```text
runs/<ticket>/plan.md
```

is absent.

### Regression

Ensure:

```text
PLAN_FIX_REQUIRED
```

still behaves correctly when a genuine plan-fix workflow is executed.

## Acceptance criteria

- `reset_to_planning` archives previous planning artifacts.
- The ticket enters a valid restart state.
- Recommended implementation uses `INIT` for full planning restart.
- Next auto-run executes planner successfully.
- Planner regenerates `runs/<ticket>/plan.md`.
- No `fix artifact missing: runs/<ticket>/plan.md` error occurs after reset.
- Existing PLAN_FIX_REQUIRED workflows continue to work.
- `reset_to_coding` has been reviewed for similar issues.
- Existing test suite continues to pass.
