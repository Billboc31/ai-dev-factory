# T206 — T206 - Fix Ticket Intelligence analysis never completing due to supervisor/API state desynchronization

**Source**: GitHub Issue #267

## Description

# T206 - Fix Ticket Intelligence analysis never completing due to supervisor/API state desynchronization

## Problem

Ticket Intelligence analyses sometimes never complete from the dashboard perspective.

Observed behavior:

```text
User clicks Analyze
↓
status becomes queued
↓
UI displays "Analysis in progress..."
↓
analysis never completes
```

The issue appears intermittently when the Control API delegates analysis execution to the Supervisor because Claude is not available inside the API container.

Potential causes:

- Control API and Supervisor are not reading/writing the same runtime database.
- Analysis completion is persisted in a different runtime root.
- UI polling never observes the final status.
- The supervisor endpoint returns successfully but the final state is never visible from the dashboard API.
- The analysis thread fails silently after delegation.

## Context

Current flow:

```text
Dashboard
↓
POST /tickets/{id}/intelligence/analyze
↓
Control API
↓
if claude unavailable
↓
delegate to Supervisor
↓
Supervisor runs analyzer
↓
result written to DB
↓
Dashboard polls GET /tickets/{id}/intelligence
```

The final GET may not see the same persisted state.

## Goals

Fully diagnose and fix Ticket Intelligence lifecycle synchronization.

Guarantee that:

```text
queued
→ running
→ completed | failed
```

always becomes visible in the dashboard.

## Required investigation

Investigate:

### Runtime paths

Verify:

```text
AI_DEV_FACTORY_RUNTIME_ROOT
runs directory
worktrees directory
database path
```

used by:

```text
Control API
Supervisor
Analyzer
```

Ensure all components use the same project runtime.

### Database consistency

Verify:

```text
runtime_db.upsert_ticket_intelligence()
get_ticket_intelligence()
```

operate on the same DB file across all processes.

Log effective DB paths during analysis.

### Delegation flow

Verify:

```text
POST /projects/{project_id}/tickets/{ticket_id}/intelligence/analyze
```

on Supervisor:

- analysis starts
- analysis finishes
- final state persisted
- errors persisted

### UI polling

Verify dashboard polling behavior.

Ensure polling stops only when:

```text
completed
failed
```

and not because of stale or missing state.

## Required improvements

Add structured logs:

```text
analysis queued
analysis started
analysis completed
analysis failed
analysis delegated
analysis DB path
runtime root path
```

If delegation fails:

```text
analysis_status = failed
```

must always be persisted.

Never leave tickets permanently in:

```text
queued
running
```

without timeout or recovery.

## Recovery requirements

Add stale analysis detection.

Example:

```text
queued > 10 minutes
running > 15 minutes
```

should automatically transition to:

```text
failed
```

with a clear diagnostic message.

## Tests

Add tests covering:

- local analysis execution
- delegated supervisor execution
- shared DB persistence
- analysis timeout
- failed AI subprocess
- stale queued analysis recovery
- stale running analysis recovery
- dashboard polling reaching completed state

## Acceptance criteria

- Ticket Intelligence never remains indefinitely queued or running.
- Dashboard always receives the final completed or failed state.
- API, Supervisor, and analyzer use the same runtime DB for a project.
- Delegated analysis behaves identically to local analysis.
- Failures are persisted and visible in the UI.
- Diagnostic logs clearly show the analysis lifecycle.
