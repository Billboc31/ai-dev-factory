## Objective

Add a `recover_ticket` Workspace capability so a user can say "Unblock this ticket" and have Claude autonomously diagnose the blocking stage through a four-phase Prepare → Confirm → Revalidate → Execute protocol, execute only allowlisted ticket-scoped fixes after explicit confirmation, and file a deduplicated GitHub issue when a reproducible product bug is identified.

## Included

### New file — `services/supervisor/recovery.py`

#### Enumerations and constants

- `BlockerClass` enum — 11 values: `MISSING_ARTIFACT`, `STALE_READINESS`, `MISSING_APPROVAL`, `FAILED_STAGE`, `BRANCH_DIVERGENCE`, `WORKING_TREE_CONFLICT`, `TRANSIENT_FAILURE`, `INVALID_CONFIG`, `INCONSISTENT_STATE`, `PRODUCT_BUG`, `USER_DECISION_REQUIRED`.
- `RecoveryStage` enum — 10 values: `DIAGNOSING`, `PLAN_READY`, `AWAITING_CONFIRMATION`, `APPLYING_FIX`, `RETRYING_STAGE`, `VERIFYING`, `RECOVERED`, `NEEDS_USER_INPUT`, `BUG_REPORTED`, `FAILED`.
- `ProposalStatus` enum — 4 values: `AWAITING_CONFIRMATION`, `EXECUTING`, `COMPLETED`, `INVALIDATED`.
- `MAX_RECOVERY_ITERATIONS = 3` — module-level constant; recovery halts once reached.

#### Data structures

- `ArtifactType` — closed enum for regeneratable artifacts: `PLAN`, `PLAN_REVIEW`, `STATE`, `FIX_CONTEXT`, `CONTEXT`.
- `ServiceId` — closed enum for restartable services: `DAEMON`, `RUNNER`.
- `RecoveryOp` dataclass — closed structure:
  - `name: str` — must be a key in `ALLOWLISTED_RECOVERY_OPS`
  - `description: str`
  - `risk_level: Literal["LOW", "MEDIUM", "HIGH"]`
  - `params: dict` — validated against per-op param schema before storage
- `StateFingerprint` dataclass:
  - `ticket_id: str`
  - `ticket_state: str` — value of `state.json` `.state` field at prepare time
  - `blocked_stage: str | None`
  - `artifact_hashes: dict[str, str]` — sha256 of each artifact file relevant to the planned ops, keyed by relative path
  - `version: str` — deterministic hex digest of the above fields
- `RecoveryProposal` dataclass:
  - `proposal_id: str` — uuid4
  - `project_id: str`
  - `ticket_id: str`
  - `blocker_class: BlockerClass`
  - `operations: list[RecoveryOp]` — frozen after creation
  - `state_fingerprint: StateFingerprint`
  - `created_at: datetime`
  - `status: ProposalStatus`
- `RecoverySession` dataclass:
  - `session_id: str`
  - `proposal_id: str | None`
  - `ticket_id: str`
  - `stage: RecoveryStage`
  - `iteration_count: int`
  - `operations_log: list[dict]`
- `OpResult` dataclass: `op_name`, `success: bool`, `detail: str`, `mutated: bool`.
- `RecoveryResult` dataclass: stored in result registry after terminal state; fields: `session_id`, `proposal_id`, `ticket_id`, `stage`, `root_cause`, `ops_performed`, `new_ticket_state`, `bug_issue_url: str | None`, `error: str | None`.

#### Allowlist

- `ALLOWLISTED_RECOVERY_OPS: dict[str, OpSpec]` — mapping from op name to `OpSpec`. Each `OpSpec` contains:
  - `risk_level`
  - `param_schema` — closed dict; only enumerated keys with enumerated or pattern-validated values are accepted; free filesystem paths, service names, shell commands, and repository URLs are never accepted as param values
  - `internal_fn` — Python callable reference (not a string, not user-supplied)
  - `preconditions: list[str]`
  - `mutation_description: str`
  - `success_condition: str`
  - `retry_policy: dict` — `max_attempts` and `backoff_seconds`

  Seven entries:
  1. `regenerate_artifact` — `artifact_type: ArtifactType` (enum, not path); regenerates missing derived artifact using repository convention; LOW risk.
  2. `refresh_readiness` — no params; re-evaluates readiness rules; LOW risk.
  3. `retry_stage` — `stage_name: str` constrained to known pipeline stage names (closed enum); retries the failed pipeline stage; MEDIUM risk.
  4. `fetch_branch` — no free params; fetches the ticket's configured branch using the approved strategy from project config; MEDIUM risk.
  5. `restart_service` — `service_id: ServiceId` (closed enum); restarts an approved local service; HIGH risk.
  6. `run_diagnostics` — no params; runs ticket-scoped diagnostic suite; LOW risk, read-only.
  7. `create_bug_issue` — no params; builds sanitized issue body server-side from session context; MEDIUM risk.

#### Functions

- `compute_state_fingerprint(ticket_id: str, project_root: Path, ops: list[RecoveryOp]) -> StateFingerprint` — reads `state.json` and relevant artifact files; computes sha256 per file; derives deterministic `version` hex digest; never mutates.
- `classify_blocker(state_data: dict, artifacts: dict, logs: str) -> BlockerClass` — pure function; matches against structured error patterns and state values; never calls an LLM; returns single `BlockerClass`.
- `build_recovery_plan(blocker: BlockerClass, state_data: dict) -> list[RecoveryOp]` — deterministic mapping from blocker class to an ordered list of allowlisted ops; validates each op's params against `ALLOWLISTED_RECOVERY_OPS[name].param_schema`; raises `ValueError` on unknown op name or invalid params.
- `compute_bug_signature(project_id: str, blocker_class: BlockerClass, failed_stage: str | None, error_code: str | None, affected_component: str | None) -> str` — builds a deterministic deduplication key from structured fields only; never uses free-form LLM text.
- `search_existing_bug_issues(repo: str, signature: str) -> str | None` — searches open GitHub issues for signature string in body; returns URL or `None`.
- `create_bug_issue(repo: str, session: RecoverySession, proposal: RecoveryProposal, error_summary: str) -> str` — assembles sanitized issue body (no secrets, no private paths, no unrestricted logs); only called when `search_existing_bug_issues` returned `None`; returns issue URL.
- `apply_recovery_op(op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str) -> OpResult` — resolves `internal_fn` from `ALLOWLISTED_RECOVERY_OPS`; revalidates `op.name` against allowlist and `op.params` against `param_schema`; never accepts op definition from frontend; appends to session log; returns `OpResult`.
- `verify_ticket_progress(ticket_id: str, project_root: Path, expected_next_state: str) -> tuple[bool, str]` — reads `state.json`; returns `(True, new_state)` if state advanced, `(False, current_state)` otherwise; read-only.

### Modified — `services/supervisor/main.py`

#### State registries

- `_active_sessions: dict[str, RecoverySession]` — keyed by `ticket_id`.
- `_proposals: dict[str, RecoveryProposal]` — keyed by `proposal_id`.
- `_results: dict[str, RecoveryResult]` — keyed by `session_id`; TTL of 30 minutes enforced by a cleanup task.
- `_session_lock: threading.Lock` — protects atomic check-and-create for both `_active_sessions` and `_proposals`.

#### Preparation phase — `_prepare_recovery(project_id: str, project_root: Path) -> dict`

1. Resolve active ticket id via `_resolve_active_ticket_id(project_id)`.
2. Acquire `_session_lock`; if `ticket_id` already in `_active_sessions`, release lock and return `{"error": "RECOVERY_IN_PROGRESS", "session_id": …}`.
3. Create session in `DIAGNOSING` stage; insert into `_active_sessions` under lock; release lock.
4. Read `state.json`, existing artifacts, and current logs — **no mutation**.
5. Call `classify_blocker(...)` → `BlockerClass`.
6. Call `build_recovery_plan(...)` → `list[RecoveryOp]`.
7. Call `compute_state_fingerprint(...)` → `StateFingerprint`.
8. Instantiate `RecoveryProposal` with `status=AWAITING_CONFIRMATION`; store in `_proposals`.
9. Advance session to `PLAN_READY`, set `session.proposal_id`.
10. Return `proposed_action`: `{ "capability": "recover_ticket", "action_id": proposal_id, "ticket_id": …, "blocker_class": …, "operations": [{"name", "description", "risk_level", "params"}, …], "current_state": …, "blocked_stage": … }`.

#### Confirmation (frontend-only step, no server mutation)

- The confirmation card renders from `proposed_action` exactly as returned by prepare.
- Frontend sends only `{ "action_id": proposal_id }` to confirm; no operation definitions or parameters may be resent.

#### Revalidation + execution phase — `_execute_recovery(proposal_id: str, project_root: Path) -> dict`

1. Look up `proposal = _proposals[proposal_id]`; verify `proposal.status == AWAITING_CONFIRMATION`; return `{"error": "PROPOSAL_NOT_FOUND"}` if missing.
2. Recompute `StateFingerprint` from current disk state.
3. If `new_fingerprint.version != proposal.state_fingerprint.version`, set `proposal.status = INVALIDATED`, advance session to `FAILED`, return HTTP 409 `{"error": "PROPOSAL_STALE", "detail": "Ticket state changed after preparation. Re-run diagnosis."}`.
4. Acquire `_session_lock`; recheck session still active; set `proposal.status = EXECUTING`; release lock.
5. Advance session to `APPLYING_FIX`.
6. For each `op` in `proposal.operations` (immutable list from store, never re-read from request):
   a. Revalidate `op.name` in `ALLOWLISTED_RECOVERY_OPS`; raise `ValueError` and halt if not found.
   b. Revalidate `op.params` against `ALLOWLISTED_RECOVERY_OPS[op.name].param_schema`; raise `ValueError` and halt if invalid.
   c. Call `apply_recovery_op(op, …)`; log `OpResult` to session.
   d. On failure, increment `session.iteration_count`; if `>= MAX_RECOVERY_ITERATIONS`, advance to `FAILED` and stop.
7. Advance session to `RETRYING_STAGE` if a retry op is in plan.
8. Advance session to `VERIFYING`; call `verify_ticket_progress(...)`.
9. On success: advance to `RECOVERED`; if `PRODUCT_BUG` detected, call `search_existing_bug_issues`; call `create_bug_issue` only if no duplicate found; advance to `BUG_REPORTED`.
10. On persistent failure: advance to `FAILED` or `NEEDS_USER_INPUT`.
11. `finally`: set `proposal.status` to `COMPLETED` or `INVALIDATED`; remove `ticket_id` from `_active_sessions` under `_session_lock`; store `RecoveryResult` in `_results`.
12. Return `recovery_report`: root cause, ops performed, new ticket state, bug issue URL.

#### Additional changes

- `_resolve_active_ticket_id(project_id: str) -> str | None` — thin wrapper around `daemon_manager._current_ticket()`; returns `None` when no ticket is running.
- `recover_ticket` added to `_WORKSPACE_CAPABILITIES` with `confirmation_required: True`.
- `_workspace_project_context()` extended to include `active_ticket_id`, current `state`, and `blocked_stage`.
- `_execute_workspace_capability()` dispatches `recover_ticket` to `_prepare_recovery()` for first call; dispatches confirmed `action_id` to `_execute_recovery()` for second call.
- Workspace chat system prompt extended to recognise "unblock", "stuck", "blocked ticket" as `recover_ticket` intents.
- New `GET /api/recovery/{session_id}` polling endpoint reads from `_results`; returns 404 while session is in progress, 200 with `RecoveryResult` when terminal.

### Modified — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`

- `RecoveryStageIndicator` sub-component: renders badge per `recovery_stage`; colours: `DIAGNOSING` → grey, `PLAN_READY` → blue, `AWAITING_CONFIRMATION` → yellow, `APPLYING_FIX`/`RETRYING_STAGE` → orange, `VERIFYING` → blue, `RECOVERED` → green, `NEEDS_USER_INPUT` → yellow, `BUG_REPORTED` → purple, `FAILED` → red.
- Badge rendered inside assistant message bubble when message carries `recovery_stage`.
- Confirmation card rendered when message carries `proposed_action`; displays `ticket_id`, `blocker_class`, and table of operations (`name`, `description`, `risk_level`, `params`); confirm button sends only `{ "action_id": proposed_action.action_id }`.
- "Unblock ticket" suggested-action button appears when last workspace message has `recovery_stage === 'NEEDS_USER_INPUT'` or `recovery_stage === 'FAILED'`; submits literal message `"Unblock this ticket"`.
- Collapsible `RecoveryReportCard` rendered from `recovery_report` field: root cause, ops list, new ticket state, bug issue link.

### New file — `tests/test_workspace_recovery.py`

- `test_prepare_performs_no_mutation` — calls `_prepare_recovery`; asserts `state.json` and all artifacts unchanged on disk; asserts one entry in `_proposals`.
- `test_confirmation_card_receives_stored_operations` — asserts `proposed_action.operations` equals `_proposals[proposal_id].operations` field-for-field.
- `test_frontend_cannot_alter_operations` — calls `_execute_recovery` while extra operations are present in request body; asserts only stored ops executed (mocked `apply_recovery_op` call count matches stored plan length).
- `test_stale_proposal_rejected_with_409` — mutates `state.json` after prepare; calls `_execute_recovery`; asserts HTTP 409 and `PROPOSAL_STALE`; asserts no ops applied.
- `test_only_stored_proposal_executed` — verifies via mock call args that the ops list used during execution matches the list stored at prepare time, not any post-preparation mutation.
- `test_concurrent_session_rejected_atomically` — two threads call `_prepare_recovery` for the same ticket simultaneously; exactly one succeeds, one receives `RECOVERY_IN_PROGRESS`; `len(_active_sessions) == 1`.
- `test_lock_released_on_exception` — `classify_blocker` raises inside prepare; asserts `_active_sessions` is empty after the call.
- `test_iteration_limit_enforced` — `apply_recovery_op` patched to always fail; asserts session reaches `FAILED` after `MAX_RECOVERY_ITERATIONS` attempts.
- `test_blocker_classification` — parametrised over all 11 `BlockerClass` values with corresponding fixture state/artifact combinations; pure function, no side-effects.
- `test_arbitrary_op_name_rejected` — unknown op name injected into stored proposal before execution; asserts `ValueError` and no mutation.
- `test_arbitrary_path_param_rejected` — `artifact_type: "/etc/passwd"` injected into stored proposal params; asserts `ValueError` during param schema validation.
- `test_arbitrary_service_name_rejected` — `service_id: "arbitrary_service"` injected into `restart_service` params; asserts `ValueError`.
- `test_missing_approval_stops_at_gate` — blocker classified as `MISSING_APPROVAL`; asserts plan contains no mutating ops; asserts session terminates with `NEEDS_USER_INPUT`; asserts `apply_recovery_op` not called.
- `test_bug_deduplication_prevents_duplicate_issue` — `search_existing_bug_issues` returns URL; asserts `create_bug_issue` not called; asserts returned URL in recovery report.
- `test_bug_signature_is_deterministic` — same structured inputs produce identical signature; different `failed_stage` produces different signature.
- `test_polling_endpoint_returns_result` — terminal `RecoveryResult` stored in `_results`; GET `/api/recovery/{session_id}` returns 200 with result; in-progress session returns 404.
- `test_recover_ticket_in_workspace_capabilities` — asserts `recover_ticket` in `_WORKSPACE_CAPABILITIES` with `confirmation_required: True`.
- `test_workspace_chat_unblock_intent` — chat message "Unblock this ticket" produces `proposed_action.capability == "recover_ticket"`.
- `test_active_ticket_resolution` — `_resolve_active_ticket_id` returns `ticket_id` whose `state.json` contains `"RUNNING"`; returns `None` when no running ticket.
- `test_recovery_verification_step` — `verify_ticket_progress` returns `(False, original_state)` when state unchanged; `(True, new_state)` when advanced.

## Excluded

- Streaming or SSE protocol changes — `recovery_stage` is a field in the existing JSON response; no new transport layer.
- Automatic resolution of ambiguous merge conflicts.
- Unrestricted shell or filesystem access beyond the current Supervisor subprocess model.
- Recovery spanning multiple projects or multiple tickets in one session.
- Bypassing human approval gates — `MISSING_APPROVAL` blocker class always terminates with `NEEDS_USER_INPUT`.
- Destructive git operations (`reset --hard`, force-push).
- Direct modification of `plan.md` outside the normal plan/plan-review artifact convention.
- Changes to existing capabilities (`restart_daemon`, `resume_execution`, `rerun_dependency_analysis`).
- LLM-generated free-form text as bug deduplication key — signature is always structural.

## Acceptance criteria

- `_prepare_recovery` reads state, artifacts, and logs but performs zero disk mutations; verified by `test_prepare_performs_no_mutation`.
- `proposed_action.operations` returned to the frontend matches the immutable `RecoveryProposal.operations` stored server-side; verified by `test_confirmation_card_receives_stored_operations`.
- Frontend-supplied operation changes at confirmation time are ignored; only the stored proposal is executed; verified by `test_frontend_cannot_alter_operations` and `test_only_stored_proposal_executed`.
- If ticket state or artifacts change between prepare and execute, execution returns HTTP 409 and no ops are applied; verified by `test_stale_proposal_rejected_with_409`.
- Two concurrent prepare calls for the same ticket result in exactly one active session and one structured `RECOVERY_IN_PROGRESS` error, without race conditions; verified by `test_concurrent_session_rejected_atomically`.
- `_session_lock` is released even when prepare raises an exception; verified by `test_lock_released_on_exception`.
- Recovery stops with `FAILED` after `MAX_RECOVERY_ITERATIONS` attempts; verified by `test_iteration_limit_enforced`.
- All 11 `BlockerClass` values are produced correctly by `classify_blocker` from matching fixture inputs; verified by parametrised `test_blocker_classification`.
- Unknown op names and invalid param values (free paths, free service names, arbitrary commands) raise `ValueError` and halt execution; verified by `test_arbitrary_op_name_rejected`, `test_arbitrary_path_param_rejected`, `test_arbitrary_service_name_rejected`.
- `MISSING_APPROVAL` blocker never triggers any mutating op; session terminates with `NEEDS_USER_INPUT`; verified by `test_missing_approval_stops_at_gate`.
- `create_bug_issue` is never called when `search_existing_bug_issues` returns a URL; existing issue URL appears in recovery report; verified by `test_bug_deduplication_prevents_duplicate_issue`.
- Bug signature is deterministic over identical structured inputs and differs when any structural field changes; verified by `test_bug_signature_is_deterministic`.
- Terminal `RecoveryResult` is accessible via `GET /api/recovery/{session_id}` (200) after session ends; in-progress sessions return 404; verified by `test_polling_endpoint_returns_result`.
- `recover_ticket` is present in `_WORKSPACE_CAPABILITIES` with `confirmation_required: True`; verified by `test_recover_ticket_in_workspace_capabilities`.
- Chat message "Unblock this ticket" maps to `proposed_action.capability == "recover_ticket"`; verified by `test_workspace_chat_unblock_intent`.
- Existing workspace capability tests in `test_supervisor_workspace.py` remain green after all changes.
