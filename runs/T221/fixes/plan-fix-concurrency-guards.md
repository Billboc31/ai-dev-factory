# Plan fix — add atomic claim guards and concurrency tests

Update `runs/T221/plan.md` before implementation.

The plan already targets the right performance issue, but it must explicitly define how parallel processing stays safe.

## Required change 1 — atomic claim transitions

Before a worker starts Ticket Intelligence or Readiness, it must atomically claim the ticket.

The claim operation must be conditional on the current stage/status.

Example shape:

```sql
UPDATE ticket_pipeline
SET intelligence_status = 'running', intelligence_started_at = CURRENT_TIMESTAMP
WHERE ticket_id = ?
  AND intelligence_status IN ('pending', 'retry_pending')
```

The worker may proceed only if exactly one row was updated.

If zero rows are updated, another worker already claimed the ticket and this worker must skip.

Equivalent logic using existing runtime DB helpers is fine, but the semantics must be atomic.

## Required change 2 — no duplicate processing

The implementation must guarantee:

```text
- one Intelligence run per ticket at a time
- one Readiness run per ticket at a time
- no double intake for the same GitHub issue
- idempotent handling if GitHub returns the same issue across multiple polls
```

Use existing uniqueness constraints where possible.

If uniqueness is missing, add guarded checks or a small helper that safely records intake once.

## Required change 3 — bounded parallelism

The new settings should bound concurrency:

```text
MAX_PARALLEL_TICKET_INTELLIGENCE
MAX_PARALLEL_READINESS
```

The implementation must never start more active workers than configured.

If a configured value is invalid or <= 0, fall back to a safe default such as 1.

## Required change 4 — intake batch logs

Each GitHub poll should log a compact summary:

```text
github poll: discovered=20 intaked=20 skipped_existing=0 skipped_limit=0
```

When `MAX_ISSUES_INTAKED_PER_POLL` is reached, logs should make that obvious:

```text
github poll: discovered=80 intaked=50 skipped_limit=30
```

## Required tests

Add tests for:

```text
1. Multiple issues discovered in one poll
   - GitHub poll returns 20 eligible issues
   - all are intaken within the same poll up to MAX_ISSUES_INTAKED_PER_POLL

2. Existing issue returned again
   - same GitHub issue appears in a later poll
   - it is skipped/idempotent and not intaken twice

3. Intelligence parallel claim safety
   - two workers try to process the same ticket
   - only one claim succeeds

4. Readiness parallel claim safety
   - two workers try to process the same ticket
   - only one claim succeeds

5. Concurrency bound
   - MAX_PARALLEL_TICKET_INTELLIGENCE=4
   - more than 4 eligible tickets exist
   - no more than 4 intelligence workers run at the same time

6. Execution worker limit unchanged
   - MAX_WORKERS / Dispatcher execution scheduling is unaffected
```

## Acceptance criteria update

Add:

```text
- Stage workers claim tickets atomically before processing.
- Parallel Intelligence cannot process the same ticket twice.
- Parallel Readiness cannot process the same ticket twice.
- GitHub issue intake is idempotent across repeated polls.
- Poll logs include discovered/intaked/skipped counts.
- Tests cover 20 issues discovered in one poll and concurrent claims for the same ticket.
```

## Non-goal reminder

Do not change coding execution concurrency in this ticket.

This ticket improves:

```text
GitHub discovery
intake throughput
intelligence/readiness throughput
```

It must not increase:

```text
number of coding workers launched by Dispatcher/daemon
```
