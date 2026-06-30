# Plan review — batch status and dependency analysis retry semantics

The T218 plan is strong overall. It introduces a coherent batch-oriented ingestion flow:

```text
collect tickets
→ run Ticket Intelligence
→ freeze batch
→ run Global Dependency Analysis
→ run Readiness
→ allow Dispatcher scheduling
```

This matches the desired architecture for stable Dispatcher execution.

However, two points must be corrected before implementation.

## 1. `pending_collecting` is referenced but not defined

The plan defines the following `BatchStatus` values:

```text
collecting
frozen
dependency_analysis_running
dependency_analysis_failed
readiness_running
dispatching
completed
```

But later it says that when `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, new tickets discovered while another batch is dispatching should land in a new `pending_collecting` batch.

That status does not exist in the planned enum.

This creates ambiguity for:

- schema constraints
- lifecycle transitions
- freeze behavior
- tests
- Dispatcher gating

The plan must choose one explicit strategy.

Recommended strategy for V1:

```text
collecting + blocked_from_freezing flag/reason
```

instead of introducing `pending_collecting` as a separate lifecycle status.

Alternative acceptable strategy:

```text
add pending_collecting to BatchStatus
```

but then transitions must be fully defined.

## 2. `dependency_analysis_failed` retry behavior is unclear

The plan says that dependency analysis failures transition the batch to:

```text
dependency_analysis_failed
```

without raising.

But the acceptance criteria says malformed or timeout AI responses are retried on the next cycle.

The retry policy is not defined.

The plan must explicitly define:

- whether retry is automatic or manual
- max retry count
- retry cooldown
- where retry metadata is stored
- what happens after retries are exhausted
- whether partial persisted rows are cleared or reused

Recommended V1 strategy:

```text
- automatic retry
- max 3 attempts
- cooldown controlled by setting or default 5 minutes
- store retry_count and last_error in backlog_batches
- after max attempts, keep dependency_analysis_failed and require manual reset/future ticket
```

The analyzer must remain idempotent:

```text
retrying the same batch must not duplicate dependency rows or events incorrectly
```

## Review verdict

PLAN_FIX_REQUIRED until:

1. the `pending_collecting` / blocked collecting behavior is made explicit;
2. dependency analysis retry semantics are fully specified.
