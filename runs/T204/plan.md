## Objective

Add a Ticket Operations panel exposing guarded manual recovery actions (advisory re-runs, approval delegation, recovery, archive, destructive deletion) backed by a new `ticket_operations.py` service, a paired Control API endpoint pair, an audit table, and a React panel on the ticket detail page. Every operation must be explicit, audited, safety-gated, and never auto-triggered.

## Included

### 1. Operations service — `tools/agent_runner/ticket_operations.py`

Create a new module that defines, validates, and executes ticket operations. Public API:

- `OPERATIONS: dict[str, OperationSpec]` — registry of operation specs.
- `OperationSpec` dataclass with fields: `key`, `label`, `group` (`advisory` | `approval` | `recovery` | `dangerous`), `safety_level` (`low` | `medium` | `high` | `destructive`), `requires_reason: bool`, `requires_typed_ticket_id: bool`, `requires_double_confirmation: bool`, `handler: Callable`.
- `list_operations(db_path, project_root, ticket_id, project_id=None) -> list[dict]` — returns each spec plus `enabled` and `disabled_reason`, computed from current ticket state, worker heartbeat, and worktree state.
- `execute_operation(db_path, project_root, ticket_id, operation_key, payload, requested_by, project_id=None) -> dict` — validates confirmation payload, runs the handler, audits the attempt, and returns `{status, message, details}`.
- `OperationError` exception carrying an HTTP-friendly status code and message; rejected attempts are still audited.

Implement these handlers (each preconditions-first, no partial mutation):

- **Advisory re-runs (`low`)**: `rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics` — call the existing `ticket_intelligence_analyzer`, `ticket_readiness_evaluator`, `execution_rules_engine`, and `ticket_diagnostics.diagnose_ticket` functions. Never touch ticket execution state.
- **Approval (`medium`)**: `approve_execution`, `reject_execution` — delegate verbatim to `ticket_approval_service.approve_execution` / `reject_execution`. No duplicated logic.
- **`mark_blocked` (`medium`)**: requires `reason`; persists the reason by calling `ticket_readiness_evaluator` blocked-write helpers (or, if absent, by inserting a blocking-reason row through `runtime_db`). Does not cancel runs or touch worktrees.
- **`reset_to_planning` (`high`)**: requires typed ticket id and `reason`. Archives the current `runs/<ticket>/` artifacts to `runs/<ticket>/archive/<timestamp>/` via `shutil.move` of the known artifact files (`plan.md`, `reviews/`, `tests/`, `conflict/`, `retry-state.json`). Writes `archive/<timestamp>/reset.json` with reason, requester, prior state. Updates `state.json` to PLANNING. Never invokes the planner. Never removes the worktree.
- **`reset_to_coding` (`high`)**: same archive pattern but preserves `plan.md`; archives `reviews/`, `tests/`, `conflict/`, `retry-state.json`. Updates `state.json` to CODING. Never invokes the coder.
- **`clear_stuck_state` (`medium` if no worker row, `high` if a stale row exists)**: checks `workers` table via `runtime_db` for an entry with this `ticket_id` and a fresh `heartbeat_at` (configurable threshold, default 120 s). Refuses if the heartbeat is fresh. Otherwise deletes the row and records the cleared values in the audit `details_json`. Never touches artifacts or the worktree.
- **`delete_worktree` (`destructive`)**: requires typed ticket id and `confirm=true`. Resolves worktrees root via `services.control_api.services.runtime_resolver.resolve_worktrees_dir`. Computes the target path and asserts (`Path.resolve().is_relative_to(worktrees_root_resolved)`) — otherwise raises. Refuses if a worker row exists with a fresh heartbeat. Runs `git -C <worktrees_root> worktree list --porcelain` to detect dirty/locked worktrees; refuses unless `force=true`. On success, runs `git worktree remove --force <path>` followed by directory removal as a fallback, and records `deleted_path` in audit details.
- **`archive_ticket` (`medium`)**: requires `reason`. Marks the ticket as archived/cancelled by writing to the existing readiness or board state (set `state.json` to a recognized terminal like `CANCELLED` if already supported, otherwise add a `archived: true` flag in `state.json`). Preserves all artifacts on disk. Records the reason in the audit.

### 2. Audit storage — extend `tools/agent_runner/runtime_db.py`

Add a new SQLite/Postgres table:

```sql
CREATE TABLE IF NOT EXISTS ticket_operation_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id       TEXT NOT NULL,
    project_id      TEXT,
    operation_key   TEXT NOT NULL,
    status          TEXT NOT NULL,
    reason          TEXT,
    requested_by    TEXT,
    details_json    TEXT,
    created_at      TEXT NOT NULL
);
```

Add helpers in `runtime_db.py`:

- `append_ticket_operation_audit(db_path, ticket_id, project_id, operation_key, status, reason, requested_by, details)`.
- `list_ticket_operation_audit(db_path, ticket_id, limit=50)`.

Mirror the schema for the Postgres branch in `runtime_db_pg.py`. Schema creation must be idempotent and run inside the existing init path used by other tables.

Also append a `runtime_events` entry per operation attempt (`event_type=f"operation:{operation_key}"`) to keep existing audit timelines coherent.

### 3. Control API — new route module `services/control_api/routes/operations.py`

Register the module in `services/control_api/main.py` alongside the other route files. Implement both global and project-scoped variants:

- `GET /tickets/{ticket_id}/operations`
- `POST /tickets/{ticket_id}/operations/{operation_key}`
- `GET /projects/{project_id}/tickets/{ticket_id}/operations`
- `POST /projects/{project_id}/tickets/{ticket_id}/operations/{operation_key}`

Pydantic models in `services/control_api/models/schemas.py`:

- `OperationDescriptor` — fields from the ticket description (`operation_key`, `label`, `safety_level`, `group`, `enabled`, `disabled_reason`, `requires_reason`, `requires_typed_ticket_id`, `requires_double_confirmation`).
- `OperationListResponse` — `ticket_id`, `operations: list[OperationDescriptor]`.
- `OperationRequest` — `reason: str | None`, `typed_ticket_id: str | None`, `confirm: bool = False`, `force: bool = False`.
- `OperationResult` — `ticket_id`, `operation_key`, `status` (`completed` | `rejected` | `error`), `message`, `details: dict`.

Behaviour:

- The `GET` handler calls `ticket_operations.list_operations` and returns `OperationListResponse`.
- The `POST` handler validates `operation_key` against `OPERATIONS`, validates the request payload against the spec (typed id matches, reason present, double confirmation, etc.), calls `execute_operation`, and returns `OperationResult`. Validation failures return HTTP 400 and are still audited as `status="rejected"`. Unknown operation keys return HTTP 404. Server errors return HTTP 500 with audit `status="error"`.
- `requested_by` is sourced from existing auth headers if the project already exposes one; otherwise default to `"operator"`.

### 4. Frontend — `apps/dashboard/src/components/TicketOperationsPanel.jsx`

Create a new panel component following the conventions in `HumanApprovalPanel.jsx` and `TicketDiagnosticsPanel.jsx`:

- Polls `GET .../operations` via the existing axios client and `usePolling`.
- Renders four sections: **Advisory re-runs**, **Approval actions**, **Recovery actions**, **Dangerous actions**, sourced from `group`.
- Each operation row: label, safety-level badge (color-coded by level), enabled state, `disabled_reason` tooltip, and a trigger button.
- Confirmation modal:
  - `low` — click confirm only.
  - `medium` — modal with optional reason field (required if `requires_reason`).
  - `high` — modal with reason field plus a typed-ticket-id input that must equal the ticket id.
  - `destructive` — modal with typed ticket id, an explicit second confirmation checkbox, and a `force` toggle when applicable.
- After action submission, surface the `OperationResult.message` inline (success or rejection).
- If T203 diagnostics are present in props or fetched alongside, display a `Recommended by diagnostics` chip next to operations whose `operation_key` matches `recommended_actions`.

Wire the panel in `apps/dashboard/src/pages/TicketDetailPage.jsx` next to the existing panels and pass the ticket id / project id.

Add API client functions in `apps/dashboard/src/api/tickets.js`:

- `listTicketOperations(ticketId, projectId)`.
- `executeTicketOperation(ticketId, projectId, operationKey, payload)`.

### 5. Tests

Backend (`tests/`, pytest), one file per service: `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py`.

- `list_operations` returns expected entries with correct `enabled`/`disabled_reason` for representative ticket states.
- Confirmation payload validation:
  - missing `reason` rejects when required.
  - mismatched `typed_ticket_id` rejects.
  - missing `confirm` rejects destructive operations.
- `rerun_diagnostics` calls `ticket_diagnostics.diagnose_ticket` and persists nothing else (verify via patched function).
- `approve_execution` and `reject_execution` delegate to `ticket_approval_service` (verify via patch / inserted approval row).
- `reset_to_planning` moves `plan.md` and related artifacts under `runs/<ticket>/archive/<ts>/`, records a `reset.json`, and sets `state.json` state to `PLANNING`. A separate test asserts a clear error when the run directory cannot be archived.
- `clear_stuck_state` refuses when a fresh heartbeat exists and clears when stale.
- `delete_worktree` refuses paths outside the worktrees root (path traversal guard), refuses dirty worktree without `force`, and succeeds with `force=true` on a constructed fixture worktree.
- `archive_ticket` preserves artifacts on disk.
- Audit log records both successful and rejected attempts (assert one row per call in `ticket_operation_audit`).

Frontend (`apps/dashboard/tests/TicketOperationsPanel.test.jsx`):

- Renders all four operation groups when API returns operations from each group.
- Disabled operations show their `disabled_reason`.
- High/destructive operations gate submission on typed ticket id matching.
- Calling an operation shows the API result message.
- Diagnostics hint appears for operations listed in `recommended_actions`.

## Excluded

- Any automatic, scheduled, or worker-driven triggering of operations.
- New dispatcher, scheduler, parallel-execution, or reservation logic.
- New automatic PR merging, auto-approval, or bypassing the human approval workflow.
- Re-implementing approval, readiness, intelligence, rules, or diagnostics logic (only delegate).
- Adding new artifact types or rearranging existing run-directory layout beyond the `archive/<timestamp>/` subfolder.
- Authentication / authorization changes; `requested_by` is best-effort from existing context.
- Bulk or multi-ticket operations.
- Real-time websocket updates (the panel polls).
- Migration tooling for existing deployments beyond the idempotent `CREATE TABLE IF NOT EXISTS` at startup.

## Acceptance criteria

- `tools/agent_runner/ticket_operations.py` exists with the documented `OperationSpec` registry, `list_operations`, and `execute_operation`, covering all ten operation keys (`rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics`, `approve_execution`, `reject_execution`, `mark_blocked`, `reset_to_planning`, `reset_to_coding`, `clear_stuck_state`, `delete_worktree`, `archive_ticket`).
- `runtime_db.py` (SQLite) and `runtime_db_pg.py` (Postgres) both create `ticket_operation_audit` idempotently and expose `append_ticket_operation_audit` / `list_ticket_operation_audit`.
- `GET /tickets/{ticket_id}/operations` and `GET /projects/{project_id}/tickets/{ticket_id}/operations` return the documented JSON shape with safety metadata for every registered operation.
- `POST /tickets/{ticket_id}/operations/{operation_key}` (and its project-scoped twin) validates the confirmation payload before executing; invalid payloads return HTTP 4xx and are still recorded in `ticket_operation_audit` with `status="rejected"`.
- Approval operations route through `ticket_approval_service.approve_execution` / `reject_execution` and do not duplicate readiness logic.
- `reset_to_planning` and `reset_to_coding` move prior artifacts into `runs/<ticket_id>/archive/<timestamp>/` and write a metadata file describing the reset; neither operation invokes the planner or the coder.
- `clear_stuck_state` refuses to execute when a worker heartbeat is fresh and clears stale rows otherwise.
- `delete_worktree` refuses any target path not strictly under the resolved worktrees root, refuses dirty worktrees unless `force=true`, and refuses when a worker heartbeat is fresh.
- `archive_ticket` does not delete any artifact on disk.
- Every operation attempt — accepted, rejected, or errored — appears as a row in `ticket_operation_audit` and as a `runtime_events` entry with type `operation:<key>`.
- `TicketOperationsPanel.jsx` is mounted on the ticket detail page, displays the four operation groups with safety-level badges, enforces typed-ticket-id input for `high`/`destructive` actions, surfaces the API result message, and shows the diagnostics hint for operations matching `recommended_actions`.
- All new backend tests in `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py` pass; the new frontend test `TicketOperationsPanel.test.jsx` passes; the existing test suite continues to pass.
- No change is made to the scheduler, dispatcher, worker allocation, worker reservation, or any code path that runs without an explicit operator click.
