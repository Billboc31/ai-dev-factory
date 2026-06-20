# Plan fix — make T197 analysis bounded/non-blocking and provider-agnostic

## Required plan update

Update `runs/T197/plan.md` before starting the coder.

The plan is functionally good, but it must be corrected in two areas:

1. AI execution must be provider-agnostic.
2. The analysis endpoint must not be an unbounded synchronous AI call.

## 1. Use AI Dev Factory model/agent abstraction

Replace any Claude-specific wording such as:

```text
via existing Claude API integration pattern
```

with:

```text
via the existing AI Dev Factory agent/model execution abstraction
```

The analyzer must not directly depend on a specific provider.

It should work with logical model names from the model catalog, for example:

```text
local-qwen
cheap-fast-model
balanced-code-model
advanced-reasoning-model
```

Provider-specific configuration can exist behind the abstraction, but the Ticket Intelligence Analyzer should not hardcode Claude, OpenAI, local models, or any other provider.

## 2. Avoid unbounded synchronous POST analyze

The current plan proposes:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze
```

as a synchronous endpoint that runs the analyzer and returns the result.

This must be changed.

Preferred behavior:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze
→ validates the ticket exists
→ creates or updates ticket_intelligence with analysis_status = queued or running
→ triggers analysis via the existing job/worker mechanism if available
→ returns quickly with the current analysis state
```

Recommended HTTP response:

```text
202 Accepted
```

with body like:

```json
{
  "ticket_id": "T197",
  "analysis_status": "queued"
}
```

If AI Dev Factory does not yet have a generic background job mechanism suitable for this, a bounded synchronous MVP is acceptable for this ticket only if all of the following are true:

- the AI call has an explicit timeout
- failures are persisted with `analysis_status = failed`
- timeout errors are visible in the API response and UI
- the frontend never waits indefinitely
- tests cover timeout/failure handling

## 3. Analysis status lifecycle

The database and API must support at least these statuses:

```text
not_started
queued
running
completed
failed
```

Suggested behavior:

- no row yet: API may return 404 or `not_started`, but the behavior must be consistent
- POST analyze: `queued` or `running`
- successful analyzer result: `completed`
- validation / timeout / model failure: `failed`

## 4. UI behavior

`TicketIntelligencePanel` must handle:

- no analysis yet
- queued/running analysis
- completed analysis
- failed analysis

The button label may change depending on state:

```text
Analyze
Re-analyze
Analysis running
Retry analysis
```

The advisory badge must remain visible:

```text
Advisory only — not used by scheduler yet
```

## 5. Scheduler remains untouched

This fix must not introduce scheduler behavior changes.

The analysis remains advisory only.

Do not:

- reorder queue automatically
- block tickets
- route execution to selected model
- change worker dispatch
- enforce dependency rules

## Updated acceptance criteria

The corrected plan is acceptable only if:

- AI execution uses the existing model/agent abstraction, not Claude-specific direct integration
- `POST /api/tickets/{ticket_id}/intelligence/analyze` is non-blocking or explicitly bounded with timeout handling
- `analysis_status` supports queued/running/completed/failed states
- failures and timeouts are persisted and displayed
- UI handles running and failed states cleanly
- scheduler and worker dispatch are unchanged
