## Objective

Decouple GitHub issue discovery from ticket pipeline processing so that a single poll cycle intakes every eligible issue in parallel, backed by atomic per-stage claim transitions that keep Ticket Intelligence and Readiness safe under concurrent execution. Coding execution concurrency (`MAX_WORKERS`) is left unchanged.

## Included

### 1. Runtime settings (`ai_dev_factory/runtime_settings.py`)

Add four new integer settings with environment-variable overrides and validation:

- `GITHUB_POLL_INTERVAL_SECONDS` — default `5`.
- `MAX_ISSUES_INTAKED_PER_POLL` — default `50`.
- `MAX_PARALLEL_TICKET_INTELLIGENCE` — default `4`.
- `MAX_PARALLEL_READINESS` — default `4`.

Validation rules:

- Non-integer, missing, or `<= 0` values fall back to a documented safe default of `1` for the three concurrency/batch caps, and to `30` for `GITHUB_POLL_INTERVAL_SECONDS`.
- Fallback path logs a single warning per setting at daemon start.
- `MAX_WORKERS` is not read, mutated, or referenced in this diff.

Expose the settings through the existing `RuntimeSettings` accessor pattern so downstream code (`run_daemon.py`, `ticket_pipeline.py`) can import them without re-parsing env vars.

### 2. GitHub poller — batch discovery (`ai_dev_factory/run_daemon.py`)

Modify the polling loop in `poll_ticket_pipeline` (currently near `run_daemon.py:1432` and `run_daemon.py:1501`):

- Remove the `break` at `run_daemon.py:1432` (post-discovery early exit) and at `run_daemon.py:1501` (post-intake early exit) so a single poll iterates over every eligible issue GitHub returned.
- Bound the batch by `MAX_ISSUES_INTAKED_PER_POLL`: after that many intakes in one cycle, stop and record a `skipped_limit` count.
- Track four counters per poll: `discovered`, `intaked`, `skipped_existing`, `skipped_limit`.
- Emit exactly one summary log line per poll:
  ```
  github poll: discovered=<N> intaked=<N> skipped_existing=<N> skipped_limit=<N>
  ```
  Existing per-issue log lines remain; the summary is additive.

### 3. Idempotent intake

Guard intake against the same GitHub issue being registered twice across polls:

- Use the existing `tickets.github_issue_number` uniqueness (or add a `UNIQUE` index on `(github_repo, github_issue_number)` in a new migration if the current schema lacks one — checked before implementation).
- Wrap the intake insert in a helper `record_intake_once(github_issue)` in `ai_dev_factory/ticket_pipeline.py` that:
  - Attempts the insert.
  - On `IntegrityError` / conflict, returns `already_intaken=True` without raising.
  - Increments `skipped_existing` in the poller counters.

### 4. Parallel Ticket Intelligence & Readiness with atomic claims

In `ai_dev_factory/ticket_pipeline.py` add two claim helpers:

```python
def claim_intelligence(ticket_id: str) -> bool:
    # UPDATE ticket_pipeline
    # SET analysis_status='running', analysis_started_at=CURRENT_TIMESTAMP
    # WHERE ticket_id=? AND analysis_status IN ('queued','retry_pending')
    # returns rowcount == 1
```

```python
def claim_readiness(ticket_id: str) -> bool:
    # UPDATE ticket_pipeline
    # SET readiness_status='running', readiness_started_at=CURRENT_TIMESTAMP
    # WHERE ticket_id=? AND readiness_status IN ('queued','retry_pending')
    # returns rowcount == 1
```

Semantics:

- Executed inside a single SQL statement (SQLite `UPDATE ... WHERE`) so the transition is atomic.
- A worker proceeds only if the helper returns `True`. On `False` it logs `skip: already_claimed ticket=<id> stage=<intelligence|readiness>` and returns.
- No new columns are added: the existing `analysis_status` / `readiness_status` fields and their `queued` / `running` values are reused. If either field is absent, the plan adds it in a minimal migration (verified before implementation).

Scheduler wiring in `run_daemon.py`:

- Replace the current sequential per-ticket loops with two `concurrent.futures.ThreadPoolExecutor` instances:
  - `intel_pool` sized `MAX_PARALLEL_TICKET_INTELLIGENCE`.
  - `readiness_pool` sized `MAX_PARALLEL_READINESS`.
- Both pools created once per daemon lifetime (not per poll) and shut down cleanly on daemon stop.
- Each submitted task first calls the matching claim helper; on `False` it returns immediately without running the stage.
- The daemon never submits more than `pool_size` in-flight tasks — the executor’s bounded queue enforces this.

### 5. Dispatcher / execution concurrency untouched

- No change to `MAX_WORKERS`, `Dispatcher.launch`, or any code path that spawns coding workers.
- An explicit regression test (see below) locks this in.

### 6. Tests (`tests/`)

New tests, added under the existing test layout (mirroring current test module names):

1. `test_poll_batch_intake.py::test_20_issues_discovered_one_poll`
   - Stub GitHub client returns 20 eligible issues.
   - Assert one poll intakes all 20; summary log contains `discovered=20 intaked=20`.

2. `test_poll_batch_intake.py::test_repeated_issue_is_idempotent`
   - Same issue returned across two polls.
   - Assert only one row in `tickets`; second poll logs `skipped_existing=1`.

3. `test_poll_batch_intake.py::test_max_issues_intaked_per_poll_caps_batch`
   - 80 eligible issues, `MAX_ISSUES_INTAKED_PER_POLL=50`.
   - Assert `intaked=50 skipped_limit=30`.

4. `test_claim_intelligence.py::test_two_workers_same_ticket_only_one_claims`
   - Two threads call `claim_intelligence(t)` concurrently on a `queued` ticket.
   - Assert exactly one returns `True`, the other `False`; DB row is `running` once.

5. `test_claim_readiness.py::test_two_workers_same_ticket_only_one_claims`
   - Symmetric test for `claim_readiness`.

6. `test_parallel_bounds.py::test_intelligence_pool_bounded`
   - `MAX_PARALLEL_TICKET_INTELLIGENCE=4`, 10 eligible tickets, stage function blocks on a barrier.
   - Assert peak concurrent workers observed == 4.

7. `test_parallel_bounds.py::test_readiness_pool_bounded`
   - Symmetric test with `MAX_PARALLEL_READINESS=4`.

8. `test_settings_fallback.py::test_invalid_setting_falls_back_to_safe_default`
   - Set each of the four env vars to `"0"`, `""`, `"abc"`.
   - Assert `RuntimeSettings` returns the documented safe default and logs one warning.

9. `test_execution_workers_unchanged.py::test_max_workers_untouched`
   - Snapshot `MAX_WORKERS` and dispatcher scheduling before/after enabling the new pools.
   - Assert the value and the set of dispatcher call sites are unchanged.

### 7. Documentation

- Update `docs/configuration.md` (or the existing settings doc) with the four new env vars, defaults, and the invalid-value fallback rule.
- No changes to CLAUDE.md or README beyond a one-line pointer in the daemon settings section if that section exists.

## Excluded

- Any change to `MAX_WORKERS` or coding-worker scheduling.
- Any change to Dispatcher execution ordering, retry backoff, or PR-lifecycle logic.
- Migration of `analysis_status` / `readiness_status` to a new state machine — reused as-is.
- Persistent job queue (Redis, Celery, etc.); the intake and stage pools remain in-process.
- Webhook-based GitHub intake (still polling-based).
- Changes to the memory pipeline or review pipeline.
- Renames or refactors of `poll_ticket_pipeline` beyond the specific edits listed above.

## Acceptance criteria

- `GITHUB_POLL_INTERVAL_SECONDS`, `MAX_ISSUES_INTAKED_PER_POLL`, `MAX_PARALLEL_TICKET_INTELLIGENCE`, `MAX_PARALLEL_READINESS` are readable via `RuntimeSettings` and overridable by env vars.
- Invalid or `<= 0` values for any of the four settings fall back to the documented safe default and emit one warning at daemon start.
- A single GitHub poll intakes every eligible issue up to `MAX_ISSUES_INTAKED_PER_POLL` without any `break` short-circuit.
- Creating 10 eligible GitHub issues results in all 10 being intaken within one or two poll cycles at the demo defaults.
- The same GitHub issue returned in successive polls is intaken exactly once (`skipped_existing` counter increments on repeats).
- Every poll emits one summary log line of the form `github poll: discovered=<N> intaked=<N> skipped_existing=<N> skipped_limit=<N>`.
- Ticket Intelligence workers call `claim_intelligence` before running the stage; a losing claim skips without side effects.
- Readiness workers call `claim_readiness` before running the stage; a losing claim skips without side effects.
- Under concurrent claims for the same ticket, exactly one worker proceeds per stage (verified by tests 4 and 5).
- The number of simultaneously running Intelligence workers never exceeds `MAX_PARALLEL_TICKET_INTELLIGENCE`; same for Readiness (verified by tests 6 and 7).
- `MAX_WORKERS` and Dispatcher execution scheduling are byte-identical to `main` (verified by test 9).
- All nine new tests pass; the existing test suite continues to pass.
