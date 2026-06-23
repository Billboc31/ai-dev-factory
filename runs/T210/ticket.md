# T210 — Improve Ticket Intelligence observability to diagnose analyses stuck in running state

**Source**: GitHub Issue #276

## Description

# Improve Ticket Intelligence observability to diagnose analyses stuck in running state

## Context

Even after implementing T208, Ticket Intelligence analyses still appear to remain in the `running` state for a very long time.

The UI eventually reports:

```text
Analysis failed
Analysis stuck in 'running' for 900s — auto-recovered by reaper.
```

The current logs and diagnostics are not sufficient to determine where the execution is blocking.

## Problem

The Ticket Intelligence execution pipeline lacks detailed observability.

Today it is difficult to determine whether the failure occurs during:

```text
background thread startup
prompt generation
AI process launch
AI request execution
response parsing
result persistence
status transition
```

As a consequence, debugging production issues is slow and mostly based on assumptions.

## Goal

Add end-to-end observability for Ticket Intelligence execution so that developers can immediately identify where an analysis is blocked or failing.

## Required changes

### Lifecycle logging

Add structured logs for the full lifecycle:

```text
[INTEL] analysis requested
[INTEL] background thread started
[INTEL] prompt generation started
[INTEL] prompt generation completed
[INTEL] AI subprocess launch started
[INTEL] AI subprocess completed
[INTEL] response parsing started
[INTEL] response parsing completed
[INTEL] persistence started
[INTEL] persistence completed
[INTEL] analysis completed
```

### Error logging

Unexpected exceptions must always produce:

```text
full stacktrace
analysis identifier
ticket identifier
current execution stage
```

### Runtime events

Persist significant lifecycle events into runtime events/audit storage when available.

Example:

```text
analysis_started
ai_process_started
ai_process_completed
analysis_failed
analysis_completed
```

### Execution stage tracking

Introduce an optional execution stage field for running analyses.

Examples:

```text
starting
building_prompt
waiting_ai
parsing_result
persisting
completed
failed
```

This stage should be visible in the UI and/or diagnostics.

## UI improvements

When an analysis is running, the UI should display:

```text
Current stage: Waiting for AI response
Started: 2026-06-23 15:00
Running for: 32s
```

instead of only:

```text
Running
```

## Acceptance criteria

- Ticket Intelligence execution emits structured logs for every major stage.
- Exceptions always include the current execution stage.
- Developers can identify where an analysis is blocked without adding temporary logs.
- Runtime events capture significant lifecycle transitions.
- The UI exposes the current execution stage while an analysis is running.
- Existing Ticket Intelligence functionality continues to work.
- All existing tests continue to pass.
