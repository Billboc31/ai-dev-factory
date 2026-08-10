**39/39 pass.** All fixes are verified. Here's the summary of changes made:

---

## Changes

### `services/supervisor/main.py`

**[BLOCKING 1] — MISSING_APPROVAL deadlock fix** (`_prepare_recovery`):  
After `build_recovery_plan()`, if the plan is empty, the session is now removed from `_active_sessions` immediately and a `NEEDS_USER_INPUT` response is returned directly — no proposal stored, no session retained. Subsequent "Unblock this ticket" attempts no longer hit `RECOVERY_IN_PROGRESS`.

**[BLOCKING 2] — PRODUCT_BUG issue creation on failed recovery** (`_execute_recovery`):  
The bug issue creation block was moved out of both the `if advanced:` guard and the `if session.stage not in (FAILED,):` guard. It now runs unconditionally whenever `blocker_class == PRODUCT_BUG`, so diagnostic evidence is always preserved regardless of whether ops succeeded or the ticket advanced.

### `tests/test_workspace_recovery.py`

- **Updated** `test_missing_approval_stops_at_gate` — now asserts `action_id is None`, `stage == NEEDS_USER_INPUT`, and no session in `_active_sessions` (no call to `_execute_recovery` needed).
- **Added** `test_missing_approval_session_not_retained` — explicit guard against the deadlock regression.
- **Added** `test_bug_issue_created_when_recovery_fails_on_product_bug` — verifies issue creation when `advanced=False` and ops fail.

### `tests/test_supervisor_workspace.py`

- **Added** `test_existing_capabilities_route_unaffected` — verifies `restart_daemon`, `rerun_dependency_analysis`, and `resume_execution` still route correctly after `recover_ticket` was registered.

### `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`

- **Updated** `RecoveryConfirmCard` — when the plan is empty, instead of a disabled grey button, a contextual explanation card is shown with blocker-specific text (`MISSING_APPROVAL` shows what to approve and where; `USER_DECISION_REQUIRED` explains why a decision is needed). The Confirm button is hidden entirely for empty plans.
