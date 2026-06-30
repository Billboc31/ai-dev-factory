## Objective
Introduce a batch-oriented backlog ingestion layer in the daemon so that newly discovered tickets are first analyzed individually by Ticket Intelligence, then grouped into a backlog batch that, once idle, is frozen and submitted to a new Global Dependency Analysis step with bounded automatic retries. Readiness evaluation and Dispatcher scheduling only run on tickets belonging to a finalized batch, while tickets arriving during execution land in a new collecting batch that is blocked from freezing until the prior dispatching batch completes.

## Included

### New module: backlog batch lifecycle
- New file `tools/agent_runner/backlog_batch.py`:
  - Defines `BatchStatus` enum with exactly these values: `collecting`, `frozen`, `dependency_analysis_running`, `dependency_analysis_failed`, `readiness_running`, `dispatching`, `completed`. No other status exists; in particular `pending_collecting` is not introduced.
  - Functions:
    - `get_or_create_collecting_batch(db_path, *, allow_parallel_batches, now) -> batch_id` — returns the current open `collecting` batch, creating a new one only if none exists or if the existing one is full. When `allow_parallel_batches=false` and another batch is already `dispatching`, the newly created (or returned) `collecting` batch is marked with `freeze_blocked=TRUE` and `freeze_blocked_reason='prior_batch_dispatching'`.
    - `add_ticket_to_batch(db_path, batch_id, ticket_id)` — idempotent membership insert; bumps `last_activity_at`.
    - `try_freeze_idle_batches(db_path, idle_timeout_minutes, max_batch_size, now)` — transitions any `collecting` batch with `freeze_blocked=FALSE` and `now - last_activity_at >= idle_timeout` (or member count `>= max_batch_size`) to `frozen`. A batch with `freeze_blocked=TRUE` is never frozen, regardless of idle/size. Returns the list of frozen batch_ids.
    - `unblock_freezing_for_pending_collecting_batches(db_path)` — when no batch is in `dispatching`, clear `freeze_blocked` / `freeze_blocked_reason` on any `collecting` batch that had been blocked because of `prior_batch_dispatching`. Called after a batch reaches `completed`.
    - `transition_batch(db_path, batch_id, from_status, to_status, *, reason=None)` — guarded transition with audit row; raises if `from_status` does not match current state (used to avoid lost-update races).
    - `mark_dependency_analysis_attempt_started(db_path, batch_id, now)` — increments `dependency_analysis_attempts` and transitions to `dependency_analysis_running`.
    - `mark_dependency_analysis_failed(db_path, batch_id, *, error, now, cooldown_minutes, max_attempts)` — transitions back to `dependency_analysis_failed`, stores `last_dependency_analysis_error`, sets `next_dependency_analysis_retry_at = now + cooldown_minutes` if `attempts < max_attempts`, else leaves `next_dependency_analysis_retry_at = NULL` (terminal).
    - `pick_batches_ready_for_dependency_analysis(db_path, now, max_attempts) -> list[batch_id]` — returns batches in `frozen`, plus batches in `dependency_analysis_failed` with `attempts < max_attempts` and `now >= next_dependency_analysis_retry_at`.
    - `list_batch_tickets(db_path, batch_id) -> list[str]`.
    - `get_batch_status(db_path, batch_id) -> dict` (status, freeze_blocked, attempts, last_error, next_retry_at, counts).

### Schema additions in `tools/agent_runner/runtime_db.py`
- New table `backlog_batches`:
  - `batch_id TEXT PRIMARY KEY`
  - `status TEXT NOT NULL`
  - `created_at TEXT NOT NULL`
  - `frozen_at TEXT NULL`
  - `last_activity_at TEXT NOT NULL`
  - `completed_at TEXT NULL`
  - `freeze_blocked INTEGER NOT NULL DEFAULT 0`
  - `freeze_blocked_reason TEXT NULL`
  - `dependency_analysis_attempts INTEGER NOT NULL DEFAULT 0`
  - `last_dependency_analysis_error TEXT NULL`
  - `next_dependency_analysis_retry_at TEXT NULL`
  - `notes TEXT NULL`
- New table `backlog_batch_tickets`:
  - `batch_id TEXT NOT NULL`
  - `ticket_id TEXT NOT NULL`
  - `added_at TEXT NOT NULL`
  - `PRIMARY KEY (batch_id, ticket_id)`
  - `UNIQUE (ticket_id)` — a ticket belongs to at most one batch.
- New table `ticket_dependency_analysis`:
  - `ticket_id TEXT NOT NULL`
  - `batch_id TEXT NOT NULL`
  - `depends_on_json TEXT NOT NULL`
  - `blocks_json TEXT NOT NULL`
  - `parallel_group TEXT NULL`
  - `conflicting_tickets_json TEXT NOT NULL`
  - `execution_phase TEXT NULL`
  - `relationship_classifications_json TEXT NOT NULL`
  - `analyzed_at TEXT NOT NULL`
  - `PRIMARY KEY (ticket_id, batch_id)`
- Helper functions in `runtime_db.py`: `upsert_dependency_analysis` (UPSERT on `(ticket_id, batch_id)`), `get_dependency_analysis`, plus the batch helpers consumed by `backlog_batch.py`.
- Migrations are additive only: opening an existing DB applies `CREATE TABLE IF NOT EXISTS` plus `ALTER TABLE backlog_batches ADD COLUMN …` guarded by a `PRAGMA table_info` check for each new column.
- Reuse the existing `runtime_events` table to log batch transitions and retry attempts.

### Global Dependency Analyzer
- New file `tools/agent_runner/global_dependency_analyzer.py`:
  - Entry point `run_global_analysis(db_path, runs_dir, batch_id, *, exec_cmd, timeout_seconds) -> AnalysisOutcome` with `AnalysisOutcome` being a dataclass holding `success: bool` and `error: str | None`.
  - Reads `ticket.md` and the persisted `ticket_intelligence.dependency_hints` for every ticket in the batch.
  - Builds a single prompt containing the batch summary (id, title, intelligence summary, hints) and invokes the configured AI command (`exec_cmd`) using the same subprocess pattern as `ticket_intelligence_analyzer.py`.
  - Parses a strict JSON response of the form:
    ```json
    {
      "tickets": [
        { "ticket_id": "T011", "depends_on": ["T010"], "blocks": [], "parallel_group": "foundation", "conflicting_tickets": [], "execution_phase": 1 }
      ],
      "relationships": [
        { "from": "T011", "to": "T010", "type": "HARD_DEPENDENCY" }
      ]
    }
    ```
    with `type ∈ {HARD_DEPENDENCY, SOFT_DEPENDENCY, FOUNDATION_DEPENDENCY, PARALLEL_COMPATIBLE, CONFLICTING_SCOPE}`.
  - Persists results via `upsert_dependency_analysis`, which is idempotent: a retry that re-runs analysis on the same batch overwrites prior rows rather than inserting duplicates. Membership rows are untouched on retry.
  - On failure (timeout, non-zero exit, malformed JSON), returns `AnalysisOutcome(success=False, error=…)` and never raises. The caller (`process_backlog_batches`) is responsible for state transition and retry scheduling.
- New prompt template `prompts/global-dependency-analyzer-prompt.md` with placeholders for `{{batch_tickets}}` and the explicit JSON output schema documented above.

### Dependency union for readiness and eligibility
- Extend `ticket_readiness_evaluator.py` and `ticket_execution_eligibility.py` so the dependency union also includes `ticket_dependency_analysis.depends_on_json` when present, with the same merge semantics already used for intelligence hints (deduplicated union; markdown takes precedence on conflict in metadata, dependency edges are the union).

### Daemon loop integration in `tools/agent_runner/run_daemon.py`
- After `poll_github_issues()` and per-ticket `call_issue_intake()`, attach each newly intaken ticket to the current collecting batch via `get_or_create_collecting_batch` + `add_ticket_to_batch`. This call happens **before** `poll_ticket_pipeline()`.
- Modify `poll_ticket_pipeline()` (or split it) so that:
  - Ticket Intelligence still runs per-ticket continuously, regardless of batch state.
  - Readiness evaluation only runs for tickets whose batch status is `readiness_running` (idempotent for already-evaluated tickets).
- Add a new periodic step `process_backlog_batches(db_path, runs_dir, settings, now)` called once per daemon cycle, just after the pipeline step:
  1. Call `try_freeze_idle_batches`.
  2. For each batch returned by `pick_batches_ready_for_dependency_analysis`:
     - Call `mark_dependency_analysis_attempt_started` (transitions `frozen`/`dependency_analysis_failed` → `dependency_analysis_running`, `attempts += 1`).
     - Invoke `global_dependency_analyzer.run_global_analysis`.
     - On success: transition to `readiness_running`, clear `last_dependency_analysis_error` and `next_dependency_analysis_retry_at`.
     - On failure: call `mark_dependency_analysis_failed` with the configured cooldown and max-attempts; if `attempts >= max_attempts` the batch stays in `dependency_analysis_failed` with `next_dependency_analysis_retry_at = NULL` (terminal until manual intervention by a future ticket).
  3. When all tickets in a `readiness_running` batch have a completed readiness evaluation, transition to `dispatching`.
  4. When all tickets in a `dispatching` batch have reached a terminal state (merged, cancelled, or failed-final), transition to `completed` and call `unblock_freezing_for_pending_collecting_batches`.
- Gate Dispatcher (`ticket_dispatcher.py`) ranking so it only considers tickets whose batch status is `dispatching`. Tickets with no batch (legacy non-dispatcher path) remain handled by the unchanged legacy flow.
- Honour `allow_parallel_batches=false`: this is enforced exclusively via the `freeze_blocked` flag on `collecting` batches; no new status is introduced. Tickets continue to be ingested into a normal `collecting` batch that simply cannot freeze until the prior `dispatching` batch reaches `completed`.

### Configuration in `tools/agent_runner/runtime_settings.py`
- Register the following settings with sane defaults and env-var overrides, exposed through the existing DB-override → env-var → default precedence:
  - `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` (default: existing `--interval`, fallback 60).
  - `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES` (default: 10).
  - `BACKLOG_MAX_BATCH_SIZE` (default: 50).
  - `BACKLOG_ALLOW_PARALLEL_BATCHES` (default: `false`).
  - `BACKLOG_DEPENDENCY_ANALYSIS_MAX_ATTEMPTS` (default: 3).
  - `BACKLOG_DEPENDENCY_ANALYSIS_RETRY_COOLDOWN_MINUTES` (default: 5).

### Logging and observability
- Emit through `runtime_events` at minimum: `batch.created`, `batch.ticket_added`, `batch.freeze_blocked`, `batch.frozen`, `batch.dependency_analysis_started`, `batch.dependency_analysis_completed`, `batch.dependency_analysis_failed` (with `attempt` and `next_retry_at` payload), `batch.dependency_analysis_exhausted` (terminal — emitted once when `attempts == max_attempts` on the failing transition), `batch.readiness_started`, `batch.dispatching`, `batch.completed`, `batch.freeze_unblocked`. Each event carries `batch_id`, ticket counts, and previous/next status when applicable.
- Mirror key transitions to stderr logs in `run_daemon.py`, matching the existing pattern for other periodic steps.

### Tests in `tests/`
- `test_backlog_batch.py`:
  - Creating a collecting batch; adding tickets; idempotency; `UNIQUE(ticket_id)` membership enforcement.
  - Idle freeze: a batch with no activity for `idle_timeout` transitions to `frozen` on the next cycle; an active batch does not.
  - `max_batch_size` triggers an immediate freeze even before idle timeout.
  - `allow_parallel_batches=false`: while Batch A is `dispatching`, newly discovered tickets land in a new `collecting` Batch B with `freeze_blocked=TRUE`; Batch B remains `collecting` even when its idle timeout is exceeded; after Batch A reaches `completed`, `unblock_freezing_for_pending_collecting_batches` clears the flag and Batch B becomes eligible for freeze on the next cycle.
  - Negative test: `BatchStatus` does not contain `pending_collecting`.
- `test_global_dependency_analyzer.py`:
  - Builds the prompt from a batch of fake tickets.
  - Parses a well-formed JSON response and persists `depends_on`, `blocks`, `parallel_group`, `conflicting_tickets`, `execution_phase`.
  - Rejects malformed JSON: returns `AnalysisOutcome(success=False, …)`, no exception bubbled up.
  - Re-running analysis on a batch with pre-existing rows performs an UPSERT (no duplicate rows, no `IntegrityError`).
  - Subprocess invocation is mocked.
- `test_daemon_batch_lifecycle.py`:
  - End-to-end with a stubbed `exec_cmd`: tickets are intaken → intelligence runs → no readiness yet → batch idle → dependency analysis runs → readiness runs → dispatcher sees tickets only after batch reaches `dispatching`.
  - Tickets arriving while a batch is in `dispatching` land in a new batch that is blocked from freezing until the dispatching batch completes.
  - Retry success path: first analysis attempt fails (stub returns malformed JSON), batch transitions to `dependency_analysis_failed` with `attempts=1` and `next_dependency_analysis_retry_at` set; after the cooldown elapses (simulated via injected `now`), the next cycle retries, succeeds, and transitions to `readiness_running` with `attempts=2`.
  - Max-attempts exhaustion: three consecutive failures leave the batch in `dependency_analysis_failed` with `attempts=3` and `next_dependency_analysis_retry_at=NULL`; subsequent cycles do not retry; Dispatcher does not see those tickets; a `batch.dependency_analysis_exhausted` event is emitted exactly once.
  - Idempotency: repeated cycles with no new tickets do not duplicate `runtime_events` rows for already-emitted transitions and do not duplicate `ticket_dependency_analysis` rows.
- Extend `test_ticket_readiness_evaluator.py` with a case where `ticket_dependency_analysis.depends_on_json` provides a dep that is not in markdown or intelligence hints, and verify it is included in the union.
- Extend `test_run_daemon.py` to assert that `process_backlog_batches` is called once per cycle, after the pipeline step.

## Excluded
- Replacing or restructuring the existing per-ticket Ticket Intelligence module — only its scheduling context changes, not the analyzer itself.
- Changing the Dispatcher's ranking algorithm, scoring, or eligibility evaluator beyond gating it on batch status and consuming the new dependency union.
- Any UI, dashboard, CLI inspector, or API endpoint to visualise batches or to manually reset a `dependency_analysis_failed` terminal batch — observability is limited to `runtime_events` and stderr logs.
- Manual reset / human approval flow for exhausted retries — once `attempts == max_attempts`, the batch stays terminal until a future ticket adds an operator-facing tool.
- Backfilling existing tickets (already in `runs/`) into batches: only tickets discovered after the feature is enabled are placed into batches; legacy tickets continue to follow the pre-existing non-batch flow.
- Cross-batch dependency analysis — each batch is analyzed in isolation; dependencies on tickets from previous batches use the existing markdown / intelligence-hint union.
- Persisting the global dependency *graph* as a separate first-class object beyond the per-ticket rows already covered by `ticket_dependency_analysis`.
- Changing GitHub polling semantics other than honouring the new `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` setting; the existing `gh`-based fetch is preserved.
- Migrating settings to a config file format — new settings reuse the current env-var / SQLite override registry.
- Modifying the worker spawn path / `launch_ticket` beyond the indirect effect of the dispatcher gate.
- Introducing a `pending_collecting` status (explicitly forbidden by this plan).

## Acceptance criteria
- Running the daemon on a fresh runtime DB creates the new tables (`backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis`) and applies the additive `ALTER TABLE` migrations on existing DBs without errors.
- `BatchStatus` contains exactly the seven values listed under "New module: backlog batch lifecycle"; no code path produces or expects `pending_collecting`.
- A newly intaken ticket is recorded in a `collecting` batch and receives Ticket Intelligence within the next pipeline cycle; its `ticket_readiness` row is **not** populated while the batch is still `collecting`, `frozen`, `dependency_analysis_running`, or `dependency_analysis_failed`.
- A batch with no new tickets for `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES` transitions to `frozen` on the next daemon cycle; asserted by `test_backlog_batch.py` and observable in `runtime_events`.
- After freeze, `global_dependency_analyzer.run_global_analysis` is invoked at most once per cycle for the batch; on success the batch transitions to `readiness_running` and `ticket_dependency_analysis` rows exist for every ticket in the batch.
- Dependencies returned by the analyzer are merged into the union consumed by the readiness evaluator and the eligibility gate (verified by an integration test that uses an analyzer-only dependency).
- The Dispatcher's ranked recommendations only include tickets whose batch is in status `dispatching`; tickets in batches in `collecting`, `frozen`, `dependency_analysis_running`, `dependency_analysis_failed`, or `readiness_running` are absent from its output.
- With `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, while Batch A is in `dispatching`, any ticket discovered in the meantime is attached to a new `collecting` Batch B with `freeze_blocked=TRUE`; Batch B does not transition to `frozen` even if its idle timeout elapses, until Batch A reaches `completed` and the flag is cleared. Covered by `test_backlog_batch.py`.
- The full batch lifecycle (`collecting → frozen → dependency_analysis_running → readiness_running → dispatching → completed`) is observable through `runtime_events` rows with the documented event types.
- Disabling the dispatcher (`AI_DEV_FACTORY_DISPATCHER_MODE=off`) reproduces the previous legacy non-batched behaviour: existing daemon and pipeline tests in `tests/` continue to pass without modification (except for the targeted additions described above).
- A malformed or timeout AI response for the dependency analyzer:
  - Transitions the batch to `dependency_analysis_failed` without raising out of `process_backlog_batches`.
  - Increments `dependency_analysis_attempts` and records `last_dependency_analysis_error`.
  - Sets `next_dependency_analysis_retry_at = now + BACKLOG_DEPENDENCY_ANALYSIS_RETRY_COOLDOWN_MINUTES` when `attempts < BACKLOG_DEPENDENCY_ANALYSIS_MAX_ATTEMPTS`, otherwise leaves it `NULL` (terminal).
- On the next daemon cycle with `now >= next_dependency_analysis_retry_at` and `attempts < max_attempts`, the batch is automatically retried; a successful retry transitions it to `readiness_running` and clears `last_dependency_analysis_error` / `next_dependency_analysis_retry_at`.
- After `BACKLOG_DEPENDENCY_ANALYSIS_MAX_ATTEMPTS` failed attempts, the batch remains in `dependency_analysis_failed`, is not retried automatically, is not scheduled by the Dispatcher, and emits exactly one `batch.dependency_analysis_exhausted` event.
- Retries are idempotent: `ticket_dependency_analysis` rows are written via UPSERT (no duplicates); membership rows are not re-inserted; partial rows from a prior failed attempt are overwritten by a later successful attempt.
- `pytest tests/test_backlog_batch.py tests/test_global_dependency_analyzer.py tests/test_daemon_batch_lifecycle.py` passes; the full repository test suite still passes after the changes.
