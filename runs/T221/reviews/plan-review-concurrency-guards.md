# Plan review — concurrency guards for near real-time intake

The T221 plan is directionally correct.

It targets the right bottleneck:

```text
GitHub polling / intake should not be limited to one ticket per daemon cycle.
```

It also correctly keeps execution scheduling separate from intake throughput:

```text
fast intake + parallel intelligence/readiness
!= more coding workers
```

However, the plan should explicitly cover concurrency safety before implementation.

## Concern

Parallelizing Ticket Intelligence and Readiness introduces a common race condition:

```text
worker A sees ticket T001 eligible
worker B sees ticket T001 eligible
both workers start processing T001
```

The plan currently mentions bounded thread pools, but it does not explicitly require atomic claim transitions.

## Required additions

The plan should add explicit concurrency guards:

```text
- atomic claim transitions before worker execution
- no duplicate Intelligence processing for the same ticket
- no duplicate Readiness processing for the same ticket
- tests with many tickets discovered at once
- logs showing discovered / intaken / skipped counts per poll
```

## Expected behavior

For each pipeline stage:

```text
eligible ticket
↓
atomic claim
↓
worker runs stage
```

Example:

```text
NEW / INTELLIGENCE_PENDING
→ INTELLIGENCE_RUNNING
```

must happen atomically before the worker starts.

If another worker tries to claim the same ticket, it should get zero rows updated / no-op and skip it.

## Review verdict

PLAN_FIX_REQUIRED until atomic claim semantics and concurrency tests are explicitly added to the plan.
