# Plan review — T197 async execution and model abstraction

The T197 plan is generally aligned with the issue goal: it adds an advisory Ticket Intelligence Analyzer, stores structured metadata in the database, exposes API endpoints, and displays the result on the ticket detail page without changing scheduler behavior.

However, two points must be fixed before implementation starts.

## Blocking issue 1 — POST analyze should not block indefinitely

The current plan says:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze — triggers the analyzer synchronously, persists result, returns it
```

This is risky because the analyzer calls an AI model. Depending on model latency, network behavior, prompt size, or retries, the HTTP request could block the UI for too long or hit a timeout.

The implementation should avoid designing this endpoint as a long-running blocking call.

Acceptable approaches:

- enqueue an intelligence analysis job and return quickly with `202 Accepted`
- or perform a bounded synchronous execution with strict timeout and clear status fields

Preferred approach for this ticket:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze
→ creates/updates ticket_intelligence row with analysis_status = queued or running
→ starts the analyzer through the existing worker/job mechanism if available
→ returns current analysis state quickly
```

If no job mechanism exists yet, a bounded synchronous MVP is acceptable only if:

- timeout is explicit
- failure is stored as `analysis_status = failed`
- UI handles running/failed states
- endpoint does not hang indefinitely

## Blocking issue 2 — do not hardcode Claude-specific integration

The current plan says:

```text
Calls the configured AI model (via existing Claude API integration pattern in the project)
```

This is too provider-specific. The whole point of Ticket Intelligence is to recommend and later route by model, so the analyzer must use the existing project abstraction for agent/model execution, not hardcode Claude.

The plan must be corrected to say:

```text
Calls the configured AI model through the existing AI Dev Factory agent/model execution abstraction.
```

The model catalog should contain logical model identifiers and pricing hints, but must not force one provider.

## Required correction

Rewrite or amend `runs/T197/plan.md` so that:

1. The analyzer uses the existing agent/model execution abstraction, not direct Claude-specific code.
2. The analyze endpoint is non-blocking or bounded with explicit timeout/failure handling.
3. `analysis_status` supports at least:

```text
not_started
queued
running
completed
failed
```

4. The UI can render loading/running/failed states.
5. Scheduler and worker dispatch behavior remain unchanged.

## Review verdict

PLAN_FIX_REQUIRED until the plan clarifies async/bounded analysis execution and removes provider-specific Claude assumptions.
