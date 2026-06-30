# Plan fix — clarify collecting batches and dependency analysis retries

Update `runs/T218/plan.md` before implementation.

The current plan must be corrected in two areas:

1. remove or explicitly define `pending_collecting`;
2. define retry semantics for `dependency_analysis_failed`.

## 1. Batch lifecycle when parallel batches are disabled

T218 V1 should avoid introducing an undefined `pending_collecting` status.

### Required V1 approach

Use only the planned statuses:

```text
collecting
frozen
dependency_analysis_running
dependency_analysis_failed
readiness_running
dispatching
completed
```

When `BACKLOG_ALLOW_PARALLEL_BATCHES=false` and a batch is already `dispatching`, newly discovered tickets should still be placed into a new `collecting` batch.

However, that collecting batch must be prevented from freezing until the active dispatching batch is completed.

Add explicit metadata to `backlog_batches`, for example:

```text
freeze_blocked BOOLEAN DEFAULT FALSE
freeze_blocked_reason TEXT NULL
```

or an equivalent field.

Expected behavior:

```text
Batch A = dispatching
new tickets arrive
→ Batch B created with status collecting
→ Batch B receives tickets and Ticket Intelligence runs
→ Batch B does not freeze while Batch A is dispatching
→ when Batch A reaches completed, Batch B becomes eligible for idle/max-size freeze
```

Do not use `pending_collecting` unless it is added to `BatchStatus` and fully documented.

### Required plan edits

Replace wording like:

```text
pending_collecting
```

with:

```text
collecting batch blocked from freezing while another batch is dispatching
```

Update tests accordingly:

```text
allow_parallel_batches=false:
- while Batch A is dispatching, Batch B remains collecting even if idle timeout is exceeded
- after Batch A completed, Batch B can freeze on the next cycle
```

## 2. Dependency analysis retry semantics

The plan must define what happens after:

```text
dependency_analysis_failed
```

### Required V1 retry policy

Use automatic retry with bounded attempts.

Add metadata to `backlog_batches`, for example:

```text
dependency_analysis_attempts INTEGER DEFAULT 0
last_dependency_analysis_error TEXT NULL
next_dependency_analysis_retry_at TEXT NULL
```

Defaults:

```text
max attempts = 3
retry cooldown = 5 minutes
```

These may be hardcoded in V1 or exposed as settings if simple.

### State behavior

On dependency analysis start:

```text
frozen or dependency_analysis_failed eligible for retry
→ dependency_analysis_running
→ attempts += 1
```

On success:

```text
dependency_analysis_running
→ readiness_running
```

On failure before max attempts:

```text
dependency_analysis_running
→ dependency_analysis_failed
next_dependency_analysis_retry_at = now + cooldown
```

On next daemon cycles:

```text
if status = dependency_analysis_failed
and attempts < max_attempts
and now >= next_dependency_analysis_retry_at
→ retry automatically
```

After max attempts:

```text
status remains dependency_analysis_failed
no automatic retry
batch is not dispatchable
log explicit terminal failure
future manual reset can be handled by another ticket
```

### Idempotency requirements

Retries must be safe:

```text
- upsert ticket_dependency_analysis rows
- do not duplicate dependency rows
- do not duplicate membership rows
- emit clear runtime_events per attempt
```

If a previous failed attempt partially persisted rows, the next successful attempt may overwrite/upsert them.

## Acceptance criteria updates

Add or update acceptance criteria:

- No undefined `pending_collecting` status is used.
- With `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, a second collecting batch cannot freeze while an earlier batch is dispatching.
- After the earlier batch completes, the second collecting batch can freeze normally.
- Dependency analysis failure increments attempt count and records last error.
- Failed dependency analysis retries automatically after cooldown until max attempts.
- After max attempts, the batch remains `dependency_analysis_failed` and is not scheduled by Dispatcher.
- Retry logic is idempotent and uses upserts for `ticket_dependency_analysis`.
- Tests cover failure, retry success, and max-attempt exhaustion.

## Non-goals

Keep these out of T218:

- UI for manually resetting failed dependency analysis batches
- dashboard visualization for batches
- cross-batch dependency recomputation
- human approval UI for dependency suggestions

Those can be future tickets.
