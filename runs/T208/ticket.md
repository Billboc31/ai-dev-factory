# T208 — Fix Ticket Intelligence analysis stuck in running state

**Source**: GitHub Issue #272

## Description

# Fix Ticket Intelligence analysis stuck in running state

## Context

The Ticket Intelligence feature currently fails to complete analyses reliably.

Observed behavior:

```text
User clicks 'Analyze'
↓
analysis status = running
↓
analysis never completes
↓
after 900 seconds
↓
reaper marks analysis as failed
```

UI error:

```text
Analysis failed

Analysis stuck in 'running' for 900s — auto-recovered by reaper.
```

This makes Ticket Intelligence effectively unusable.

## Problem

The analysis lifecycle enters:

```text
running
```

but never reaches:

```text
completed
```

or

```text
failed
```

The reaper eventually detects the stale analysis and forces failure.

Possible causes include:

- background worker never starts
- exception swallowed inside background task
- AI call hangs indefinitely
- subprocess never exits
- missing timeout on LLM execution
- analysis result never persisted
- status transition never executed
- deadlock while updating runtime database

## Goal

Guarantee that every Ticket Intelligence analysis eventually reaches:

```text
completed
```

or

```text
failed
```

with a meaningful error message.

No analysis should remain indefinitely in:

```text
running
```

## Scope

Investigate the complete Ticket Intelligence execution pipeline:

```text
UI trigger
↓
Control API endpoint
↓
background execution
↓
AI invocation
↓
database persistence
↓
status transitions
↓
reaper interaction
```

## Required changes

### Background execution reliability

Verify that analysis jobs always start and always terminate.

Unexpected exceptions must never be silently swallowed.

All exceptions must:

```text
log error
persist failure reason
set status = failed
```

### AI timeout handling

Ensure all AI/model invocations have explicit timeouts.

### Runtime persistence

Successful analyses always persist:

```text
status = completed
completed_at
analysis payload
```

Failures must persist:

```text
status = failed
error_message
failed_at
```

### Observability

Add detailed runtime logging:

```text
analysis started
analysis step started
AI request started
AI request completed
analysis persisted
analysis failed
```

### Reaper improvements

The reaper should preserve original failure causes when known instead of always replacing them with the generic timeout message.

## Tests

Add tests covering:

- successful execution
- AI timeout
- unexpected exception path
- reaper recovery
- no silent failures

## Acceptance criteria

- No Ticket Intelligence analysis remains indefinitely in `running`.
- Every analysis eventually becomes `completed` or `failed`.
- AI calls use explicit timeouts.
- Exceptions are logged and persisted.
- Failure reasons are visible in UI.
- Reaper preserves original failure causes when available.
- Runtime logs clearly show analysis lifecycle steps.
- Existing Ticket Intelligence functionality continues to work.
- All new and existing tests pass.
