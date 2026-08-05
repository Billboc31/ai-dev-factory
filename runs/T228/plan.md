## Objective

Add a `recover_ticket` workspace capability so a user can say "Unblock this ticket" and have Claude autonomously diagnose the blocking stage, present a constrained recovery plan, execute allowlisted fixes after confirmation, verify the ticket progresses, and file a deduplicated GitHub issue when a product bug is identified.

## Included

### New file — `services/supervisor/recovery.py`

- `BlockerClass` enum with all 11 categories from the ticket (missing artifact, stale readiness, missing approval, failed stage, branch divergence, working-tree conflict, transient failure, invalid config, inconsistent state, product bug, user decision required).
- `RecoverySession` dataclass: `session_id`, `ticket_id`, `project_id`, `stage` (one of `DIAGNOSING / PLAN_READY / AWAITING_CONFIRMATION / APPLYING_FIX / RETRYING_STAGE / VERIFYING / RECOVERED / NEEDS_USER_INPUT / BUG_REPORTED / FAILED`), `iteration_count`, `max_iterations` (constant `MAX_RECOVERY_ITERATIONS = 3`), `operations_log`.
- `ALLOWLISTED_RECOVERY_OPS` mapping: keys are op names (`regenerate_artifact`, `refresh_readiness`, `retry_stage`, `fetch_branch`, `restart_service`, `run_diagnostics`, `create_bug_issue`); values carry risk level and required params.
- `classify_blocker(state_data: dict, artifacts: dict, logs: str) -> BlockerClass` — pure function, reads existing diagnostic output from `ticket_diagnostics.diagnose_ticket()`.
- `build_recovery_plan(blocker: BlockerClass, state_data: dict) -> list[RecoveryOp]` — returns ordered list of allowlisted ops, never includes destructive ops.
- `apply_recovery_op(op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str) -> OpResult` — executes one op, appends to session log; refuses any op not in `ALLOWLISTED_RECOVERY_OPS`.
- `verify_ticket_progress(ticket_id: str, project_root: Path, expected_next_state: str) -> tuple[bool, str]` — reads `state.json`, returns `(progressed, new_state)`.
- `search_existing_bug_issues(repo: str, bug_signature: str) -> str | None` — calls GitHub search API; returns URL of matching issue or `None`.
- `create_bug_issue(repo: str, bug_data: dict) -> str` — builds sanitized issue body (no secrets, no private paths), creates issue, returns URL. Only called when `search_existing_bug_issues` returns `None`.

### Modified — `services/supervisor/main.py`

- Add `recover_ticket` to `_WORKSPACE_CAPABILITIES` (lines ~2876–2889) with `confirmation_required: True`.
- Add module-level `_active_recovery_sessions: dict[str, RecoverySession]` keyed by `ticket_id`; prevents concurrent recovery by returning a structured error when a session already exists.
- Add `_resolve_active_ticket_id(project_id: str) -> str | None` — thin wrapper around the logic already in `daemon_manager._current_ticket()`, exposed for use within the supervisor.
- Add `_execute_recover_ticket(project_id: str, project_root: Path) -> dict` — orchestrates the full recovery flow using `recovery.py`; enforces `MAX_RECOVERY_ITERATIONS`; records diagnostics, confirmation point, mutations, retries, and result in session log; cleans up session on terminal state.
- Extend `_workspace_project_context()` (lines ~2944–2971) to include active ticket id, current `state` field, and blocked stage when the ticket is not progressing.
- Extend `_execute_workspace_capability()` (line ~3042) to dispatch `recover_ticket` to `_execute_recover_ticket()`.
- Extend workspace chat system prompt to recognise "unblock", "stuck", and "blocked ticket" as `recover_ticket` intents.
- Response for `recover_ticket` includes `recovery_report` field: root cause, ops performed, retry result, new ticket state, bug issue URL (if any).

### Modified — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`

- Add `RecoveryStageIndicator` sub-component: renders a coloured badge for each `recovery_stage` value (`DIAGNOSING` → grey, `PLAN_READY` → blue, `AWAITING_CONFIRMATION` → yellow, `APPLYING_FIX` → orange, `RETRYING_STAGE` → orange, `VERIFYING` → blue, `RECOVERED` → green, `NEEDS_USER_INPUT` → yellow, `BUG_REPORTED` → purple, `FAILED` → red).
- Show the badge inside the assistant message bubble when the message carries a `recovery_stage` field.
- Add an "Unblock ticket" suggested-action button that appears in the chat input area when the last workspace message indicates the ticket is blocked (detected by `recovery_stage === 'NEEDS_USER_INPUT'` or `recovery_stage === 'FAILED'`); clicking it submits the literal message `"Unblock this ticket"`.
- On `recovery_report` in message payload: render a collapsible summary card listing root cause, ops performed, and bug issue link when present.

### New file — `tests/test_workspace_recovery.py`

- `test_recover_ticket_in_allowlist` — verifies `recover_ticket` is in `_WORKSPACE_CAPABILITIES`.
- `test_concurrent_recovery_rejected` — starting a second session for the same ticket while one is active returns a structured error (not 500).
- `test_iteration_limit_enforced` — after `MAX_RECOVERY_ITERATIONS` retries, session reaches `FAILED` and stops.
- `test_blocker_classification` — parametrised over each `BlockerClass` variant with fixture state/artifact combinations.
- `test_only_allowlisted_ops_execute` — passing an op name not in `ALLOWLISTED_RECOVERY_OPS` to `apply_recovery_op` raises `ValueError`.
- `test_active_ticket_resolution` — `_resolve_active_ticket_id` returns the ticket whose `state.json` contains `"RUNNING"`.
- `test_bug_issue_deduplication` — when `search_existing_bug_issues` returns a URL, `create_bug_issue` is not called.
- `test_recovery_verification_step` — `verify_ticket_progress` returns `(False, original_state)` when state is unchanged, `(True, new_state)` when it advances.
- `test_workspace_chat_unblock_intent` — chat message "Unblock this ticket" produces `proposed_action.capability == "recover_ticket"`.

## Excluded

- Streaming/SSE protocol changes — uses existing request-response flow; recovery stage is a field in the JSON response.
- Automatic resolution of ambiguous merge conflicts.
- Unrestricted shell or filesystem access beyond current supervisor subprocess model.
- Recovery spanning multiple projects or multiple tickets in a single session.
- Bypassing human approval gates; `missing_approval` blocker class terminates with `NEEDS_USER_INPUT` and explains what must be approved.
- Destructive git operations (`reset --hard`, force-push).
- Changes to `plan.md` outside the normal plan/plan-review artifact convention.
- Changes to existing capabilities (`restart_daemon`, `resume_execution`, `rerun_dependency_analysis`).

## Acceptance criteria

- Sending "Unblock this ticket" in the Workspace chat resolves the active ticket id without requiring the user to specify it; confirmed via `test_workspace_chat_unblock_intent`.
- Diagnostics phase reads only existing artifacts and logs; no state mutation occurs before confirmation; confirmed by `test_blocker_classification`.
- Root cause classification covers all 11 categories defined in the ticket; confirmed by parametrised `test_blocker_classification`.
- The action confirmation card shows the exact ops to be executed before the user clicks confirm; recovery_report field present in response.
- Only op names present in `ALLOWLISTED_RECOVERY_OPS` can be executed; confirmed by `test_only_allowlisted_ops_execute`.
- A second "Unblock" request while a session is active for the same ticket returns a non-500 structured error; confirmed by `test_concurrent_recovery_rejected`.
- Recovery halts and returns `FAILED` after `MAX_RECOVERY_ITERATIONS` attempts; confirmed by `test_iteration_limit_enforced`.
- `search_existing_bug_issues` is always called before `create_bug_issue`; duplicate bugs link to the existing issue; confirmed by `test_bug_issue_deduplication`.
- Recovery report in the final chat message includes root cause, list of ops performed, new ticket state, and bug issue URL when applicable; field schema enforced in `test_workspace_chat_unblock_intent`.
- `RecoveryStageIndicator` renders the correct badge colour for each `recovery_stage` value; existing workspace capability tests (`test_supervisor_workspace.py`) remain green.
