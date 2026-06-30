## Objective
Introduce a batch-oriented backlog ingestion layer in the daemon so that newly discovered tickets are first analyzed individually by Ticket Intelligence, then grouped into a backlog batch that, once idle, is frozen and submitted to a new Global Dependency Analysis step. Readiness evaluation and Dispatcher scheduling will only run on tickets belonging to a finalized batch, while tickets arriving during execution are queued into the next batch.

## Included

### New module: backlog batch lifecycle
- New file `tools/agent_runner/backlog_batch.py`:
  - Defines `BatchStatus` enum with values: `collecting`, `frozen`, `dependency_analysis_running`, `dependency_analysis_failed`, `readiness_running`, `dispatching`, `completed`.
  - Functions:
    - `get_or_create_collecting_batch(db_path) -> batch_id` — returns the current open batch, creating one only if none exists or if existing collecting batch is full / parallel batches forbidden while a previous batch is `dispatching`.
    - `add_ticket_to_batch(db_path, batch_id, ticket_id)` — idempotent membership insert; bumps `last_activity_at`.
    - `try_freeze_idle_batches(db_path, idle_timeout_minutes, max_batch_size, now)` — transitions any `collecting` batch with `now - last_activity_at >= idle_timeout` (or size >= `max_batch_size`) to `frozen`. Returns list of frozen batch_ids.
    - `transition_batch(db_path, batch_id, from_status, to_status, *, reason=None)` — guarded transition with audit row.
    - `list_batch_tickets(db_path, batch_id) -> list[str]`.
    - `get_batch_status(db_path, batch_id)`.

### Schema additions in `tools/agent_runner/runtime_db.py`
- New table `backlog_batches`:
  - `batch_id TEXT PRIMARY KEY`, `status TEXT`, `created_at`, `frozen_at`, `last_activity_at`, `completed_at`, `notes TEXT NULL`.
- New table `backlog_batch_tickets`:
  - `batch_id TEXT`, `ticket_id TEXT`, `added_at`, PRIMARY KEY `(batch_id, ticket_id)`, UNIQUE `(ticket_id)` (a ticket belongs to at most one batch).
- New table `ticket_dependency_analysis`:
  - `ticket_id TEXT`, `batch_id TEXT`, `depends_on_json`, `blocks_json`, `parallel_group TEXT NULL`, `conflicting_tickets_json`, `execution_phase TEXT NULL`, `relationship_classifications_json`, `analyzed_at`, PRIMARY KEY `(ticket_id, batch_id)`.
- Helper functions: `upsert_dependency_analysis`, `get_dependency_analysis`, plus the batch helpers consumed by `backlog_batch.py`.
- Reuse the existing `runtime_events` table to log batch transitions (new `event_type`: `batch.transition`).

### Global Dependency Analyzer
- New file `tools/agent_runner/global_dependency_analyzer.py`:
  - Entry point `run_global_analysis(db_path, runs_dir, batch_id, *, exec_cmd, timeout_seconds)`.
  - Reads ticket.md + existing `ticket_intelligence.dependency_hints` for every ticket in the batch.
  - Builds a single prompt containing the batch summary (id, title, intelligence summary, hints) and calls the configured AI command (`exec_cmd`) using the same subprocess pattern as `ticket_intelligence_analyzer.py`.
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
    where `type ∈ {HARD_DEPENDENCY, SOFT_DEPENDENCY, FOUNDATION_DEPENDENCY, PARALLEL_COMPATIBLE, CONFLICTING_SCOPE}`.
  - Persists results via `upsert_dependency_analysis` and merges `depends_on` into the union consumed by readiness (the union of markdown deps, intelligence hints, and now batch-analysis deps).
  - On failure (timeout, malformed JSON), marks batch `dependency_analysis_failed`, logs the failure, and never raises.
- New prompt template `prompts/global-dependency-analyzer-prompt.md` with placeholders for `{{batch_tickets}}` and explicit JSON output schema.

### Integration in the union of dependencies
- Extend `ticket_readiness_evaluator.py` and `ticket_execution_eligibility.py` so the dependency union also includes `ticket_dependency_analysis.depends_on_json` when present, with the same merge semantics already used for intelligence hints.

### Daemon loop integration in `tools/agent_runner/run_daemon.py`
- After `poll_github_issues()` and per-ticket `call_issue_intake()`, attach each newly intaken ticket to the current collecting batch via `add_ticket_to_batch`. This call happens **before** `poll_ticket_pipeline()`.
- Modify `poll_ticket_pipeline()` (or split it) so that:
  - Ticket Intelligence still runs per-ticket continuously, regardless of batch state.
  - Readiness evaluation only runs for tickets whose batch status is `readiness_running` (and afterwards, kept idempotent for already-evaluated tickets).
- Add a new periodic step `process_backlog_batches(db_path, runs_dir, settings)` called once per daemon cycle, just after the pipeline step:
  - Call `try_freeze_idle_batches`.
  - For each newly-frozen batch (or batch in `frozen`): transition to `dependency_analysis_running`, run `global_dependency_analyzer.run_global_analysis`, then transition to `readiness_running` on success.
  - When all tickets in `readiness_running` batches have a completed readiness evaluation, transition to `dispatching`.
  - When all tickets in `dispatching` have reached a terminal state (merged, cancelled, or failed final), transition to `completed`.
- Gate Dispatcher (`ticket_dispatcher.py`) ranking so it only considers tickets whose batch status is `dispatching` (legacy non-dispatcher path remains untouched).
- Honour `allow_parallel_batches`: when `false`, refuse to create a new collecting batch while another batch is in `dispatching` — the next batch creation is deferred until completion; tickets ingested in the meantime still land in *a* new collecting batch (`pending_collecting`), but it never transitions to `frozen` until the previous batch is `completed`.

### Configuration in `tools/agent_runner/runtime_settings.py`
- Register four new settings with sane defaults and env-var overrides:
  - `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` (default: existing `--interval`, fallback 60).
  - `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES` (default: 10).
  - `BACKLOG_MAX_BATCH_SIZE` (default: 50).
  - `BACKLOG_ALLOW_PARALLEL_BATCHES` (default: `false`).
- Expose them via the existing DB-override → env-var → default precedence used by the other settings.

### Logging and observability
- Use `runtime_events` to emit at minimum: `batch.created`, `batch.ticket_added`, `batch.frozen`, `batch.dependency_analysis_started`, `batch.dependency_analysis_completed`, `batch.dependency_analysis_failed`, `batch.readiness_started`, `batch.dispatching`, `batch.completed`. Each event carries `batch_id`, ticket counts, and the previous/next status.
- Mirror key transitions to stderr logs in `run_daemon.py` (already the existing pattern for other periodic steps).

### Tests in `tests/`
- `test_backlog_batch.py`:
  - Creating a collecting batch; adding tickets; idempotency; UNIQUE membership.
  - Idle freeze: a batch with no activity for `idle_timeout` transitions to `frozen`; an active batch does not.
  - `max_batch_size` triggers an immediate freeze even before idle timeout.
  - `allow_parallel_batches=false`: while a prior batch is `dispatching`, a new ticket goes into a new `collecting` batch that does not freeze until the prior reaches `completed`.
- `test_global_dependency_analyzer.py`:
  - Builds the prompt from a batch of fake tickets.
  - Parses a well-formed JSON response and persists `depends_on`, `blocks`, `parallel_group`, `conflicting_tickets`, `execution_phase`.
  - Rejects malformed JSON (status → `dependency_analysis_failed`, no exception bubbled up).
  - Subprocess invocation is mocked.
- `test_daemon_batch_lifecycle.py`:
  - End-to-end with a stubbed `exec_cmd`: tickets are intaken → intelligence runs → no readiness yet → batch idle → dependency analysis runs → readiness runs → dispatcher sees tickets only after batch reaches `dispatching`.
  - Tickets arriving while a batch is in `dispatching` land in a new batch and do not affect the executing batch.
- Extend `test_ticket_readiness_evaluator.py` with a case where `ticket_dependency_analysis.depends_on_json` provides a dep that is not in markdown or intelligence hints.
- Extend `test_run_daemon.py` to assert the new `process_backlog_batches` call site exists in the cycle.

## Excluded
- Replacing or restructuring the existing per-ticket Ticket Intelligence module — only its scheduling context changes, not its analyzer.
- Changing the Dispatcher's ranking algorithm, scoring, or eligibility evaluator beyond gating it on batch status and consuming the new dependency union.
- Any UI, dashboard, CLI inspector, or API endpoint to visualise batches — observability is limited to `runtime_events` and stderr logs.
- Backfilling existing tickets (already in `runs/`) into batches: only tickets discovered after the feature is enabled are placed into batches; legacy tickets continue to follow the pre-existing non-batch flow.
- Cross-batch dependency analysis (each batch is analyzed in isolation; dependencies on tickets from previous batches use the existing markdown / intelligence-hint union).
- Persisting the global dependency *graph* as a separate first-class object beyond the per-ticket rows already covered by `ticket_dependency_analysis`.
- Changing GitHub polling semantics other than honouring the new `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` setting; the existing `gh`-based fetch is preserved.
- Migrating settings to a config file format; new settings reuse the current env-var / SQLite override registry.
- Modifying the worker spawn path / `launch_ticket` beyond the indirect effect of the dispatcher gate.

## Acceptance criteria
- Running the daemon on a fresh runtime DB creates the four new tables (`backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis`, plus migrations applied to existing DBs) without errors.
- A newly intaken ticket is recorded in a `collecting` batch and receives Ticket Intelligence within the next pipeline cycle; its `ticket_readiness` row is **not** populated while the batch is still `collecting` or `frozen`.
- A batch with no new tickets for `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES` transitions to `frozen` on the next daemon cycle; this is asserted by `test_backlog_batch.py` and observable in `runtime_events`.
- After freeze, `global_dependency_analyzer.run_global_analysis` is invoked exactly once for the batch; on success the batch transitions to `readiness_running`, and `ticket_dependency_analysis` rows exist for every ticket in the batch.
- Dependencies returned by the analyzer are merged into the union consumed by the readiness evaluator and the eligibility gate (verified by an integration test that uses an analyzer-only dependency).
- The Dispatcher's ranked recommendations only include tickets whose batch is in status `dispatching`; tickets in batches still in `collecting`, `frozen`, `dependency_analysis_running`, or `readiness_running` are absent from its output.
- With `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, while a batch is in `dispatching`, any ticket discovered in the meantime is attached to a new `collecting` batch that does not transition to `frozen` until the prior batch reaches `completed`; covered by `test_backlog_batch.py`.
- The full batch lifecycle (`collecting → frozen → dependency_analysis_running → readiness_running → dispatching → completed`) is observable through `runtime_events` rows with the documented event types.
- Disabling the dispatcher (`AI_DEV_FACTORY_DISPATCHER_MODE=off`) reproduces the previous legacy non-batched behaviour: existing daemon and pipeline tests in `tests/` continue to pass without modification (except for the targeted additions described above).
- `pytest tests/test_backlog_batch.py tests/test_global_dependency_analyzer.py tests/test_daemon_batch_lifecycle.py` passes; the full repository test suite still passes after the changes.
- A malformed or timeout AI response for the dependency analyzer leaves the batch in `dependency_analysis_failed`, never raises out of `process_backlog_batches`, and is retried on the next cycle without duplicating already-persisted rows.
