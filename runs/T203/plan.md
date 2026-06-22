## Objective

Introduce a read-only diagnostic capability that explains why a given ticket is stuck and recommends safe recovery actions. The capability spans a new `ticket_diagnostics.py` service, a new `ticket_diagnostics` DB table, two Control API endpoints (with project-scoped variants), and a `TicketDiagnosticsPanel` displayed on the ticket detail page. It must never mutate ticket state, worktrees, branches, PRs, scheduler/worker state, or run any agent — only persist the latest diagnostic per ticket.

## Included

### Diagnostic service — `tools/agent_runner/ticket_diagnostics.py`

- Public entry point `diagnose_ticket(db_path, project_root, ticket_id, *, worktrees_dir=None, timeout_s=5) -> dict`.
- Deterministic, bounded, idempotent. No raise on missing data: every check returns `passed | failed | unknown | skipped` with a human-readable `message`.
- Internal pure helper `build_diagnostic(...)` that takes pre-fetched check results and assembles the final dict (so tests can assemble via fixtures without disk/Git).
- Per-check helpers (one function each, all returning `{"key", "status", "message", "details": {...}}`):
  - `_check_ticket_existence` — uses `services/control_api/services/artifact_reader.get_ticket` semantics replicated against `project_root` + `worktrees_dir` (filesystem only; no API import). Missing ticket short-circuits to `is_stuck=true`, `severity=error`, single check + `manual_investigation` action.
  - `_check_runtime` — `runtime_db.get_ticket_runtime(db_path, ticket_id)`. Surfaces `state`, `last_transition`, `last_error`, `pr_number`, `pr_state`, `worktree_path`, `daemon_archived`. Also fetches `runtime_db.list_ticket_runtime`-equivalent worker row via a new tiny helper or direct SELECT on the `workers` table (read-only) to report `reservation` (pid, status, heartbeat_at).
  - `_check_intelligence` — wraps `runtime_db.get_ticket_intelligence`. Emits `rerun_intelligence` when missing/failed; emits `inspect_logs` when `queued`/`running` and `updated_at` older than a bounded threshold (e.g. 30 min, configurable constant `_STALE_INTELLIGENCE_SECONDS`).
  - `_check_readiness` — wraps `runtime_db.get_ticket_readiness`. Surfaces `blocking_reasons_json` verbatim in `details`. Emits `rerun_readiness` on missing/failed; surfaces blocking reasons when `blocked`.
  - `_check_approval` — calls `ticket_approval_service.compute_execution_eligibility(db_path, ticket_id)`; also reads `runtime_db.get_latest_ticket_approval(db_path, ticket_id, "execution")` to surface rejection reason. Emits `approve_execution` / `reject_execution` when `ready_candidate` and not `ready_to_take`. Does not import any approval mutation function.
  - `_check_rules` — wraps `runtime_db.get_ticket_rule_evaluation`. Surfaces `failed_rules_json`. Emits `rerun_rules` on missing/failed; surfaces failed rules when `blocked`.
  - `_check_worktree` — resolves expected worktree path via the runtime row (`worktree_path`) or `worktrees_dir / ticket_id`. Reports `exists | missing | dirty | clean | unknown`. Dirty is detected by `git status --porcelain` with `timeout=timeout_s` inside the worktree dir; any `subprocess.TimeoutExpired` or `FileNotFoundError` collapses to `unknown` (never raise).
  - `_check_branch` — reads `branch` from `ticket_runtime`; verifies via `git show-ref --verify --quiet refs/heads/<branch>` from `project_root`, bounded. Reports `exists | missing | unknown`.
  - `_check_pr` — uses `pr_number`/`pr_state` already in `ticket_runtime`. Maps to `no_pr | open | merged | closed_unmerged | unknown`. No network call. When PR `merged` but ticket state ≠ `DONE`/`MERGED` family, emits `sync_ticket_state`.
  - `_check_logs` — bounded scan of `runs/<ticket_id>/` (resolved through existing `runtime_resolver.resolve_ticket_run_dir`): returns latest log filename, mtime, last 20 lines of the most recent log if size ≤ 256 KB else only path/mtime; presence flags for `plan.md`, `review.md`, `tests.md`.
  - `_check_context_freshness` — reads `main_sha_when_evaluated` from readiness (if present) and compares to `git rev-parse origin/main` (bounded, falls back to `main`). Reports `fresh | stale | unknown`. Never emits a blocking action; only attaches an advisory note.
- `_derive_summary_and_severity(checks, runtime_row)` — first failed check in declared priority order (existence → runtime → readiness → approval → rules → worktree → branch → pr → intelligence → logs → freshness) sets `summary`, `severity` (`info | warning | error`), `is_stuck`. Healthy path returns `is_stuck=false`, `severity=info`, summary `Ticket has no detected blockers`.
- `_dedupe_actions(actions)` — preserve insertion order, drop duplicates by `action_key`.
- `recommended_actions` use the catalog defined below; each as `{"action_key", "label", "risk", "reason"}`.
- Module-level `RECOMMENDED_ACTION_CATALOG: dict[str, dict]` with the 15 keys from the ticket and their static `label` + `risk`; helpers construct the per-call object by injecting `reason`.
- `_persist_result(db_path, ticket_id, project_id, result)` calls a new `runtime_db.upsert_ticket_diagnostics(...)` (see below). `project_id` resolved by caller via `services/project_id`.
- `_now_iso()` reused via `runtime_db._now_iso` import.

### DB schema — `tools/agent_runner/runtime_db.py`

- Add to `_SCHEMA`:
  ```sql
  CREATE TABLE IF NOT EXISTS ticket_diagnostics (
      ticket_id                TEXT PRIMARY KEY,
      project_id               TEXT,
      diagnostic_status        TEXT NOT NULL DEFAULT 'completed',
      is_stuck                 INTEGER NOT NULL DEFAULT 0,
      severity                 TEXT NOT NULL DEFAULT 'info',
      summary                  TEXT,
      current_state            TEXT,
      last_known_step          TEXT,
      last_error               TEXT,
      checks_json              TEXT NOT NULL DEFAULT '[]',
      recommended_actions_json TEXT NOT NULL DEFAULT '[]',
      generated_at             TEXT NOT NULL,
      created_at               TEXT NOT NULL,
      updated_at               TEXT NOT NULL
  );
  ```
- Add CRUD helpers next to the readiness helpers, following the same pattern:
  - `upsert_ticket_diagnostics(db_path, ticket_id, **fields)` — sets `created_at` only on first insert; serializes `checks_json` / `recommended_actions_json` when callers pass lists.
  - `get_ticket_diagnostics(db_path, ticket_id) -> dict | None` — returns parsed `checks` and `recommended_actions` lists.
- Mirror the new functions in the Postgres backend stub block (the `_pg.xxx` assignments at the bottom of the file) so SQLite/Postgres parity is preserved. The actual Postgres implementation in `runtime_db_pg.py` gets the equivalent CREATE TABLE and two helper functions.

### Control API — `services/control_api/`

- New route module `services/control_api/routes/diagnostics.py`:
  - `router = APIRouter(prefix="/tickets", tags=["diagnostics"])`
  - `project_router = APIRouter(prefix="/projects", tags=["diagnostics"])`
  - `GET /tickets/{ticket_id}/diagnostics` → returns persisted row or 404.
  - `POST /tickets/{ticket_id}/diagnostics/run` → runs synchronously (bounded), persists, returns result. 404 if ticket missing in DB and filesystem.
  - Project-scoped variants delegate to the bare-router handlers (same pattern as `readiness.py`).
- Pydantic models added to `services/control_api/models/schemas.py`:
  - `DiagnosticCheck`, `DiagnosticRecommendedAction`, `TicketDiagnostics` (matches DB columns + parsed lists), `TicketDiagnosticsRun` (response of POST).
- Wire both routers in `services/control_api/main.py` next to the existing `readiness`/`approvals`/`rules` includes.
- The endpoint resolves `project_id` via `services/control_api/services/project_id.normalize_project_id` from `request.app.state.project_root` (mirrors how rules/readiness obtain it where needed).

### Frontend

- New API client functions in `apps/dashboard/src/api/tickets.js`:
  ```js
  export const getTicketDiagnostics = (id, projectId) =>
    client.get(`${_pfx(projectId)}/tickets/${id}/diagnostics`)
  export const runTicketDiagnostics = (id, projectId) =>
    client.post(`${_pfx(projectId)}/tickets/${id}/diagnostics/run`)
  ```
- New component `apps/dashboard/src/components/TicketDiagnosticsPanel.jsx`:
  - Props: `ticketId`, `projectId`, `onRefresh`.
  - On mount: `GET /diagnostics`; 404 → show empty state with a `Run diagnostics` button.
  - Displays: stuck/healthy badge (red/green), severity pill, summary, current state, last known step, last error, checks list (key, status pill, message, optional `details` block), recommended actions list, generated date.
  - Each recommended action rendered as a disabled button labelled with `label` and a small `Action not wired yet` badge; risk shown via colored pill (`low`/`medium`/`high`/`destructive`).
  - `Run diagnostics` button calls POST then refetches GET.
- Mount the panel in `apps/dashboard/src/pages/TicketDetailPage.jsx` alongside the existing `TicketReadinessPanel` / `TicketRuleEvaluationPanel` panels.

### Tests

Add Python tests under `tests/`:

- `tests/test_ticket_diagnostics_db.py` — upsert/get round-trip, JSON columns parsed correctly, `created_at` immutable on update.
- `tests/test_ticket_diagnostics_service.py` — covers:
  - missing ticket → `is_stuck=true`, severity `error`, `manual_investigation` recommended.
  - missing intelligence row → `rerun_intelligence` in actions.
  - readiness `blocked` with blocking reasons → reasons surfaced; `manual_investigation` only if no more specific action applies.
  - readiness `ready_candidate` + no approval → both `approve_execution` and `reject_execution` recommended.
  - rule evaluation `blocked` with failed rules → failed rules surfaced in check details.
  - runtime row says worktree expected at path X but filesystem missing → `recreate_worktree` and `reset_to_planning` recommended.
  - PR `merged` + ticket state ≠ done → `sync_ticket_state` recommended.
  - happy path (all checks pass) → `is_stuck=false`, `severity=info`, empty recommended actions list (or only advisory ones).
  - calling `diagnose_ticket` twice yields identical structural output (except `generated_at`).
- `tests/test_ticket_diagnostics_api.py` — FastAPI TestClient: GET 404 before POST, POST persists, GET returns the persisted result, project-scoped routes return same payload.
- `tests/test_ticket_diagnostics_safety.py` — import the service module and assert that it does not import any of the known mutating helpers: `worktree_manager.remove_*`, `runtime_checkpoint.reset_*`, `ticket_approval_service.approve_*`, `ticket_approval_service.reject_*`, `run_ticket.*`, `run_step.*`, `run_daemon.*` (use `inspect.getsource(...)` regex / `importlib` symbol table inspection).

Frontend test (Vitest, matching the existing pattern of other panels):

- `apps/dashboard/src/components/__tests__/TicketDiagnosticsPanel.test.jsx` — renders healthy state, renders stuck state with recommended actions disabled, `Run diagnostics` triggers POST then GET refetch (mocked axios).

## Excluded

- Executing any recommended action. All actions are advisory only; buttons render disabled with an `Action not wired yet` badge.
- Mutating ticket state, approvals, rule evaluation rows, worktrees, branches, PRs, scheduler reservations, daemon state, worker rows.
- Historical diagnostic timeline (only the latest row per ticket is stored).
- Background/async execution of diagnostics — endpoint is synchronous and bounded.
- Enforcing stale-context blocking. `context_freshness` is reported only, never gates anything.
- Touching the supervisor, daemon, scheduler, or any agent runner.
- Aggregated dashboard or board-wide views (per-ticket panel only).
- GitHub API calls for PR status — only locally-cached `pr_state`/`pr_number` from `ticket_runtime` is used.
- Postgres migration tooling beyond mirroring the new schema and helper signatures; no data backfill is required.

## Acceptance criteria

- `runtime_db.init_runtime_db` creates the `ticket_diagnostics` table; `upsert_ticket_diagnostics` and `get_ticket_diagnostics` round-trip a row including JSON columns, with `created_at` immutable across updates.
- `tools/agent_runner/ticket_diagnostics.py:diagnose_ticket` returns a dict matching the documented JSON shape (`ticket_id`, `diagnostic_status`, `is_stuck`, `severity`, `summary`, `current_state`, `last_known_step`, `last_error`, `checks`, `recommended_actions`, `generated_at`) on every supported scenario and never raises.
- Each check returns one of `passed | failed | unknown | skipped`; unknowns never propagate as an exception. All Git subprocess calls use `timeout=timeout_s`.
- Recommended actions are well-formed (`action_key`, `label`, `risk`, `reason`) and limited to the catalog listed in the ticket. Duplicate `action_key`s are deduplicated.
- `GET /tickets/{id}/diagnostics` returns 200 with the persisted row when present, 404 otherwise.
- `POST /tickets/{id}/diagnostics/run` runs synchronously, persists, and returns the result with the same payload shape as GET.
- Project-scoped routes `/projects/{project_id}/tickets/{id}/diagnostics[/run]` return the same payload as the bare routes.
- The ticket detail page renders a `Ticket Diagnostics` panel showing badge, severity, summary, current state, last known step, last error, checks list, recommended actions list (all disabled), generated date, and a working `Run diagnostics` button.
- All new tests (`test_ticket_diagnostics_db.py`, `test_ticket_diagnostics_service.py`, `test_ticket_diagnostics_api.py`, `test_ticket_diagnostics_safety.py`, the new Vitest spec) pass.
- The safety test asserts that `ticket_diagnostics` does not reference or import any state-mutating helpers from the agent runner.
- Existing test suite (`pytest tests/` and the dashboard tests) continues to pass with no regressions.
