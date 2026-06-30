## Summary

T218 is implemented end-to-end, with all targeted tests green. Changes already committed to the branch by the daemon's auto-checkpoint as `2a7d88db`.

### What was built

**Schema (`tools/agent_runner/runtime_db.py`)**
- New tables: `backlog_batches`, `backlog_batch_tickets` (with `UNIQUE(ticket_id)`), `ticket_dependency_analysis` (PK `(ticket_id, batch_id)`, UPSERT-safe).
- Additive `ALTER TABLE` migration for `backlog_batches` columns guarded by `PRAGMA table_info`.
- Helpers: `insert/get/list_backlog_batches`, `update_backlog_batch`, `insert_backlog_batch_ticket`, `list_backlog_batch_ticket_ids`, `get_batch_for_ticket`, `upsert_dependency_analysis`, `get_dependency_analysis`.

**Lifecycle (`tools/agent_runner/backlog_batch.py`)**
- `BatchStatus` enum with exactly the 7 plan-mandated values; explicit test that `pending_collecting` is not present.
- `get_or_create_collecting_batch`, `add_ticket_to_batch`, `try_freeze_idle_batches`, `unblock_freezing_for_pending_collecting_batches`, `transition_batch` (guarded), `mark_dependency_analysis_attempt_started/succeeded/failed`, `pick_batches_ready_for_dependency_analysis`, `get_batch_status`, `get_ticket_batch_status`.
- Emits all required runtime events (`batch.created`, `batch.frozen`, `batch.freeze_blocked`, `batch.freeze_unblocked`, `batch.dependency_analysis_started/completed/failed/exhausted`, `batch.readiness_started`, status_changed, etc.). `exhausted` emitted exactly once.

**Analyzer (`tools/agent_runner/global_dependency_analyzer.py` + `prompts/global-dependency-analyzer-prompt.md`)**
- `AnalysisOutcome` dataclass; `run_global_analysis(db_path, runs_dir, batch_id, exec_cmd, …)` never raises.
- Builds the prompt from the batch ticket markdown + persisted intelligence summary/hints, runs `exec_cmd` with timeout, parses strict JSON, validates relationship types, persists per-ticket rows via UPSERT.

**Dependency union**
- `ticket_readiness_evaluator.collect_dependency_ticket_ids` now also unions `ticket_dependency_analysis.depends_on`.
- `ticket_execution_eligibility.evaluate_eligibility` reads + passes the analyzer row to `_eval_dependencies`.

**Daemon integration (`run_daemon.py`)**
- After successful issue intake, the new ticket is attached to the current collecting batch via `_attach_ticket_to_collecting_batch`.
- New `process_backlog_batches(db, runs_dir, exec_cmd)` runs once per cycle (`--once` and the main loop), driving: freeze → analyze → readiness_running → dispatching → completed, with retry/cooldown/exhaustion as per plan.
- Readiness pipeline (`ticket_pipeline.find_next_ticket`, `process_ticket`, `maybe_run_readiness_after_intelligence`) now gates on batch status — tickets without a batch keep legacy behaviour.
- Dispatcher (`ticket_dispatcher.get_recommended_tickets`) filters out tickets whose batch is not `dispatching`.

**Settings (`runtime_settings.py`)**
- `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS`, `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES`, `BACKLOG_MAX_BATCH_SIZE`, `BACKLOG_ALLOW_PARALLEL_BATCHES`, `BACKLOG_DEPENDENCY_ANALYSIS_MAX_ATTEMPTS`, `BACKLOG_DEPENDENCY_ANALYSIS_RETRY_COOLDOWN_MINUTES`.

### Tests (43 new tests, all green under `RUNTIME_DB_BACKEND=sqlite`)
- `tests/test_backlog_batch.py` — enum closedness, creation, idempotent membership, idle/size freeze, `allow_parallel_batches=False` lifecycle, retry scheduling, exhaustion terminal, transition guard.
- `tests/test_global_dependency_analyzer.py` — well-formed → persisted, malformed → failure (no raise), non-zero rc → failure, UPSERT no duplicates, invalid relationship type dropped.
- `tests/test_daemon_batch_lifecycle.py` — pipeline gated on batch, dispatcher gated on batch, ticket arriving during dispatch lands in blocked batch, retry success path, exhaustion event emitted once.
- `tests/test_ticket_readiness_evaluator.py` — new test: analyzer-only dep is included in union and blocks.
- `tests/test_run_daemon.py` — new test: `main --once` calls `process_backlog_batches` exactly once.

### Limits known
- The 4 remaining pre-existing failures (`test_main_once_returns_zero`, `test_main_returns_2_when_runs_dir_missing`, `test_main_calls_poll_ticket_pipeline_each_cycle`, `test_run_once_calls_launch_for_auto_runnable_state`) are not caused by this change — they fail on the unmodified branch because a real daemon process is already holding the singleton lock locally (and, when not, because the host DB has `DISPATCHER_ENABLED=advisory`).
- Only one batch is freeze-blocked at a time via the `prior_batch_dispatching` flag; the plan explicitly leaves cross-batch dependency analysis, batch UI/CLI, and operator-driven retry reset out of scope.
