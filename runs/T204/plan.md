## Objective

Add a Ticket Operations panel that exposes guarded manual recovery actions (advisory re-runs, approval delegation, recovery resets, archive, destructive deletion) backed by a new `ticket_operations.py` service, paired Control API endpoints, an audit table, and a React panel on the ticket detail page. Every operation must be explicit, audited, safety-gated, restricted to existing runner states, and never auto-triggered.

## Included

### 1. Operations service — `tools/agent_runner/ticket_operations.py`

Create a new module that defines, validates, and executes ticket operations. Public API:

- `OPERATIONS: dict[str, OperationSpec]` — registry of operation specs.
- `OperationSpec` dataclass with fields: `key`, `label`, `group` (`advisory` | `approval` | `recovery` | `dangerous`), `safety_level` (`low` | `medium` | `high` | `destructive`), `requires_reason: bool`, `requires_typed_ticket_id: bool`, `requires_double_confirmation: bool`, `handler: Callable`.
- `list_operations(db_path, project_root, ticket_id, project_id=None) -> list[dict]` — returns each spec plus `enabled` and `disabled_reason`, computed from current ticket state, worker heartbeat, and worktree state.
- `execute_operation(db_path, project_root, ticket_id, operation_key, payload, requested_by, project_id=None) -> dict` — validates confirmation payload, runs the handler, audits the attempt, and returns `{status, message, details}`.
- `OperationError` exception carrying an HTTP-friendly status code and message; rejected attempts are still audited.

Runner state invariant (mandatory):

- The service must only write runner state values that already belong to the existing runner state machine: `INIT`, `PLAN_REVIEW_NEEDED`, `PLAN_FIX_REQUIRED`, `PLAN_APPROVED`, `IMPLEMENTATION_REVIEW_NEEDED`, `IMPLEMENTATION_FIX_REQUIRED`, `IMPLEMENTATION_APPROVED`, `TEST_COMPLETE`, `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLVING`, `CONFLICT_RESOLVED_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_FAILED`.
- Forbidden values: `PLANNING`, `CODING`, `CANCELLED`. The service must never write these. A defensive check inside `execute_operation` rejects any handler attempt to set a state outside the allowed set.

Implement these 12 handlers (preconditions-first, no partial mutation):

- **Advisory re-runs (`low`)**: `rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics` — call the existing `ticket_intelligence_analyzer`, `ticket_readiness_evaluator`, `execution_rules_engine`, and `ticket_diagnostics.diagnose_ticket` functions. Never touch ticket execution state.
- **Approval (`medium`)**: `approve_execution`, `reject_execution` — delegate verbatim to `ticket_approval_service.approve_execution` / `reject_execution`. No duplicated logic.
- **`mark_blocked` (`medium`)**: requires `reason`; persists the reason via the existing readiness blocked-write helper, or, if absent, by inserting a blocking-reason row through `runtime_db`. Does not cancel runs or touch worktrees. Does not change runner state.
- **`reset_to_planning` (`high`)**: requires typed ticket id and `reason`. Archives `runs/<ticket_id>/` artifacts (`plan.md`, `reviews/`, `tests/`, `conflict/`, `retry-state.json`) into `runs/<ticket_id>/archive/<timestamp>/` via `shutil.move`. Writes `archive/<timestamp>/reset.json` with `{operation, ticket_id, requested_by, reason, previous_state, new_state, created_at}`. Sets `state.json` runner state to **`PLAN_FIX_REQUIRED`** (an existing state that safely routes the ticket back into the planner path while preserving that a prior plan existed). Never invokes the planner. Never removes the worktree.
- **`reset_to_coding` (`high`)**: requires typed ticket id and `reason`. Same archive pattern but preserves `plan.md`; archives `reviews/`, `tests/`, `conflict/`, `retry-state.json` into `runs/<ticket_id>/archive/<timestamp>/`. Writes `archive/<timestamp>/reset.json` with `{operation, ticket_id, requested_by, reason, previous_state, new_state, created_at}`. Sets `state.json` runner state to **`IMPLEMENTATION_FIX_REQUIRED`** (an existing state that routes the ticket back into the coder path without invalidating the approved plan). Never invokes the coder.
- **`clear_stuck_state` (`medium` if no worker row, `high` if a stale row exists)**: checks the `workers` table via `runtime_db` for an entry with this `ticket_id` and a fresh `heartbeat_at` (configurable threshold, default 120 s). Refuses if the heartbeat is fresh. Otherwise deletes the row and records the cleared values in the audit `details_json`. Never touches artifacts, runner state, or the worktree.
- **`delete_worktree` (`destructive`)**: requires typed ticket id and `confirm=true`. Resolves the worktrees root via `services.control_api.services.runtime_resolver.resolve_worktrees_dir`. Computes the target path and asserts `Path.resolve().is_relative_to(worktrees_root_resolved)` — otherwise raises. Refuses if a worker row exists with a fresh heartbeat. Runs `git -C <worktrees_root> worktree list --porcelain` to detect dirty/locked worktrees; refuses unless `force=true`. On success, runs `git worktree remove --force <path>` followed by directory removal as a fallback, and records `deleted_path` in audit details. Does not change runner state.
- **`archive_ticket` (`medium`)**: requires `reason`. **Does not change the runner state. Does not introduce or write `CANCELLED`.** Writes the following archive metadata into `state.json`:
  ```json
  {
    "archived": true,
    "archived_reason": "...",
    "archived_by": "...",
    "archived_at": "..."
  }
  ```
  Preserves all artifacts on disk. Does not remove the worktree. Does not invoke planner/coder/reviewer/tester. The Ticket Operations panel and API are responsible for hiding execution actions when `archived` is true; no scheduler or worker logic changes.

### 2. Audit storage — extend `tools/agent_runner/runtime_db.py`

Add a new table:

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

- `OperationDescriptor` — `operation_key`, `label`, `safety_level`, `group`, `enabled`, `disabled_reason`, `requires_reason`, `requires_typed_ticket_id`, `requires_double_confirmation`.
- `OperationListResponse` — `ticket_id`, `operations: list[OperationDescriptor]`.
- `OperationRequest` — `reason: str | None`, `typed_ticket_id: str | None`, `confirm: bool = False`, `force: bool = False`.
- `OperationResult` — `ticket_id`, `operation_key`, `status` (`completed` | `rejected` | `error`), `message`, `details: dict`.

Behaviour:

- The `GET` handler calls `ticket_operations.list_operations` and returns `OperationListResponse`.
- The `POST` handler validates `operation_key` against `OPERATIONS`, validates the request payload against the spec (typed id match, reason presence, double confirmation, etc.), calls `execute_operation`, and returns `OperationResult`. Validation failures return HTTP 400 and are still audited as `status="rejected"`. Unknown operation keys return HTTP 404. Server errors return HTTP 500 with audit `status="error"`.
- `requested_by` is sourced from existing auth headers if available; otherwise defaults to `"operator"`.

### 4. Frontend — `apps/dashboard/src/components/TicketOperationsPanel.jsx`

Create a new panel component following the conventions of `HumanApprovalPanel.jsx` and `TicketDiagnosticsPanel.jsx`:

- Polls `GET .../operations` via the existing axios client and `usePolling`.
- Renders four sections sourced from `group`: **Advisory re-runs**, **Approval actions**, **Recovery actions**, **Dangerous actions**.
- Each operation row: label, safety-level badge (color-coded by level), enabled state, `disabled_reason` tooltip, trigger button.
- Confirmation modal:
  - `low` — single confirm click.
  - `medium` — modal with optional reason field (required if `requires_reason`).
  - `high` — modal with reason field plus a typed-ticket-id input that must equal the ticket id.
  - `destructive` — modal with typed ticket id, an explicit second confirmation checkbox, and a `force` toggle when applicable.
- After submission, surface `OperationResult.message` inline (success or rejection).
- If T203 diagnostics are present, render a `Recommended by diagnostics` chip next to operations whose `operation_key` matches `recommended_actions`.

Wire the panel into `apps/dashboard/src/pages/TicketDetailPage.jsx` next to existing panels, passing the ticket id / project id.

Add API client functions in `apps/dashboard/src/api/tickets.js`:

- `listTicketOperations(ticketId, projectId)`.
- `executeTicketOperation(ticketId, projectId, operationKey, payload)`.

### 5. Tests

Backend, in `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py`:

- `OPERATIONS` registry contains exactly these 12 keys: `rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics`, `approve_execution`, `reject_execution`, `mark_blocked`, `reset_to_planning`, `reset_to_coding`, `clear_stuck_state`, `delete_worktree`, `archive_ticket`.
- `list_operations` returns expected entries with correct `enabled`/`disabled_reason` across representative ticket states.
- Confirmation payload validation: missing `reason` rejects when required; mismatched `typed_ticket_id` rejects; missing `confirm` rejects destructive operations.
- `rerun_diagnostics` calls `ticket_diagnostics.diagnose_ticket` (verified via patched function) and persists nothing else.
- `approve_execution` and `reject_execution` delegate to `ticket_approval_service` (verified via patch / inserted approval row).
- `reset_to_planning` moves `plan.md` and related artifacts into `runs/<ticket>/archive/<ts>/`, writes a `reset.json` with the documented metadata, and sets `state.json` runner state to exactly `"PLAN_FIX_REQUIRED"`. A negative test asserts that no test or handler ever writes `"PLANNING"`.
- `reset_to_coding` preserves `plan.md`, archives implementation/review/test/conflict/retry artifacts, writes a `reset.json` with the documented metadata, and sets `state.json` runner state to exactly `"IMPLEMENTATION_FIX_REQUIRED"`. A negative test asserts that no test or handler ever writes `"CODING"`.
- A registry-level test asserts that the only runner state values any handler is allowed to set are members of the existing runner state set, and explicitly that the forbidden values `"PLANNING"`, `"CODING"`, `"CANCELLED"` are never written by any operation.
- `archive_ticket` writes only `archived`, `archived_reason`, `archived_by`, `archived_at` into `state.json`, leaves the runner state field unchanged, and preserves all artifact files on disk.
- `clear_stuck_state` refuses when a fresh heartbeat exists and clears the row when stale.
- `delete_worktree` refuses paths outside the worktrees root (path traversal guard), refuses dirty worktree without `force`, succeeds with `force=true` on a constructed fixture worktree, and refuses when a worker heartbeat is fresh.
- Audit log records both successful and rejected attempts (one row per call in `ticket_operation_audit` and one matching `runtime_events` entry).

Frontend (`apps/dashboard/tests/TicketOperationsPanel.test.jsx`):

- Renders all four operation groups when the API returns operations from each group.
- Disabled operations display their `disabled_reason`.
- High and destructive operations gate submission on the typed ticket id matching.
- Calling an operation displays the API result message.
- The `Recommended by diagnostics` hint appears for operations listed in `recommended_actions`.

## Excluded

- Any automatic, scheduled, or worker-driven triggering of operations.
- New runner states. The runner state machine is unchanged; no operation invents `PLANNING`, `CODING`, or `CANCELLED`.
- New dispatcher, scheduler, parallel-execution, worker-allocation, or worker-reservation logic.
- New automatic PR merging, auto-approval, or bypassing the human approval workflow.
- Re-implementing approval, readiness, intelligence, rules, or diagnostics logic (only delegate to the existing services).
- Adding new artifact types or rearranging existing run-directory layout beyond the `archive/<timestamp>/` subfolder.
- Authentication/authorization changes; `requested_by` is best-effort from existing context.
- Bulk or multi-ticket operations.
- Real-time websocket updates (the panel polls).
- Migration tooling beyond the idempotent `CREATE TABLE IF NOT EXISTS` at startup.

## Acceptance criteria

- `tools/agent_runner/ticket_operations.py` exists with the documented `OperationSpec` registry, `list_operations`, and `execute_operation`, covering all 12 operation keys: `rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics`, `approve_execution`, `reject_execution`, `mark_blocked`, `reset_to_planning`, `reset_to_coding`, `clear_stuck_state`, `delete_worktree`, `archive_ticket`.
- The service writes only runner state values that exist in the current runner state machine. The values `PLANNING`, `CODING`, and `CANCELLED` are never written by any operation, and tests explicitly assert this.
- `reset_to_planning` sets `state.json` runner state to `PLAN_FIX_REQUIRED` and archives prior artifacts into `runs/<ticket_id>/archive/<timestamp>/` with a `reset.json` metadata file. The planner is not invoked.
- `reset_to_coding` sets `state.json` runner state to `IMPLEMENTATION_FIX_REQUIRED`, preserves `plan.md`, and archives implementation/review/test/conflict/retry artifacts into `runs/<ticket_id>/archive/<timestamp>/` with a `reset.json` metadata file. The coder is not invoked.
- `archive_ticket` writes `archived`, `archived_reason`, `archived_by`, `archived_at` into `state.json`, does not change the runner state, does not introduce `CANCELLED`, and preserves all artifacts on disk.
- `runtime_db.py` (SQLite) and `runtime_db_pg.py` (Postgres) both create `ticket_operation_audit` idempotently and expose `append_ticket_operation_audit` / `list_ticket_operation_audit`.
- `GET /tickets/{ticket_id}/operations` and `GET /projects/{project_id}/tickets/{ticket_id}/operations` return the documented JSON shape with safety metadata for every registered operation.
- `POST /tickets/{ticket_id}/operations/{operation_key}` (and its project-scoped twin) validates the confirmation payload before executing; invalid payloads return HTTP 4xx and are still recorded in `ticket_operation_audit` with `status="rejected"`.
- Approval operations route through `ticket_approval_service.approve_execution` / `reject_execution` and do not duplicate readiness logic.
- `clear_stuck_state` refuses to execute when a worker heartbeat is fresh and clears stale rows otherwise.
- `delete_worktree` refuses any target path not strictly under the resolved worktrees root, refuses dirty worktrees unless `force=true`, and refuses when a worker heartbeat is fresh.
- Every operation attempt — accepted, rejected, or errored — appears as a row in `ticket_operation_audit` and as a `runtime_events` entry with type `operation:<key>`.
- `TicketOperationsPanel.jsx` is mounted on the ticket detail page, displays the four operation groups with safety-level badges, enforces typed-ticket-id input for `high`/`destructive` actions, surfaces the API result message, and shows the diagnostics hint for operations matching `recommended_actions`.
- All new backend tests in `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py` pass; the new frontend test `TicketOperationsPanel.test.jsx` passes; the existing test suite continues to pass.
- No change is made to the scheduler, dispatcher, worker allocation, worker reservation, or any code path that runs without an explicit operator click.
