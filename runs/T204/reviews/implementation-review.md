# Implementation Review — T204

## Scope & ticket compliance

The implementation fulfills every acceptance criterion from the ticket and the approved plan:

- `tools/agent_runner/ticket_operations.py:1` defines the `OperationSpec` dataclass, the 12-operation registry (`OPERATIONS` at line 521), `list_operations`, `execute_operation`, plus `VALID_RUNNER_STATES` / `FORBIDDEN_RUNNER_STATES` guardrails. All 12 keys required by the plan are present with the documented `group`, `safety_level`, `requires_reason`, `requires_typed_ticket_id`, `requires_double_confirmation` metadata.
- Runner-state invariant enforced both on write (`_write_state` line 137) and as a post-condition (`execute_operation` line 826). The forbidden values `PLANNING`/`CODING`/`CANCELLED` are explicitly tested (`test_ticket_operations.py:114`, `:251`, `:283`, `:464`).
- `reset_to_planning` archives `plan.md` + reviews/tests/conflict/retry-state and sets `PLAN_FIX_REQUIRED`; `reset_to_coding` preserves `plan.md` and sets `IMPLEMENTATION_FIX_REQUIRED`; both write `reset.json` metadata. Verified by tests.
- `archive_ticket` writes only `archived`/`archived_reason`/`archived_by`/`archived_at` and never touches the runner state (`test_archive_ticket_only_sets_archive_metadata`).
- `delete_worktree` enforces path containment via `target.resolve()` + `relative_to(worktrees_root)`, refuses fresh heartbeats, refuses dirty worktree without `force=true`. Audit records `deleted_path`.
- `clear_stuck_state` refuses fresh heartbeats and otherwise removes the row, recording cleared values.
- `runtime_db.py:169` and `runtime_db_pg.py:207` both add idempotent `ticket_operation_audit` schema with `append_…` / `list_…` helpers and Postgres rebinds at line 1036–1037.
- Every operation attempt — completed, rejected, errored — is double-audited in `ticket_operation_audit` and `runtime_events` (`_audit` line 724). Verified for success and rejection paths.
- Control API routes match the spec, with project-scoped twins delegating to the unscoped handlers. Unknown operation → 404; validation rejection → 400 with audit row. Pydantic schemas in `schemas.py:603-632` match.
- Frontend panel (`TicketOperationsPanel.jsx`) renders four groups, safety badges, modal with reason / typed-id / double-confirm / force, and the "Recommended by diagnostics" chip matching `recommended_actions[].action_key` (consistent with `ticket_diagnostics.py:68`). Mounted in `TicketDetailPage.jsx:285`.
- No scheduler/dispatcher/worker/parallel-execution code is touched.

## Test results

- `tests/test_ticket_operations.py` + `tests/test_control_api_operations.py` → **33/33 pass**.
- `apps/dashboard/tests/TicketOperationsPanel.test.jsx` → **6/6 pass**.

## Observations (non-blocking)

These are quality/UX nits worth tracking; none violates an acceptance criterion or the approved plan.

1. **`_handle_delete_worktree` cwd choice** (`ticket_operations.py:481`). `git worktree remove` is invoked with `cwd=worktrees_root`. In production, `worktrees_root` (e.g. `~/runtime/ai-dev-factory/worktrees/`) is not itself a git repository, so git will exit non-zero and the `shutil.rmtree` fallback (line 484) is what actually removes the directory. The directory does get removed, but the main repo's `.git/worktrees/<ticket_id>/` administrative entry is left behind until a later `git worktree prune`. The existing `worktree_manager.remove_ticket_worktree` (line 211) avoids this by running without an explicit cwd (inheriting the daemon's project-root cwd). The audit row's `git_worktree_remove_ok: false` makes it visible, but switching to `cwd=target` (while it still exists) or to the project root would let git own the cleanup.

2. **`archive_ticket` re-enabled after archiving** (`_compute_availability` line 633-634). When `archived=True`, every operation except `archive_ticket` is correctly disabled — but `archive_ticket` itself stays enabled, so it can be invoked twice (the second call just rewrites the metadata). Harmless, but disabling with a "Ticket is already archived" reason would be cleaner UX.

3. **Best-effort `requested_by`** comes from `X-Operator-Name`/`X-User-Name` headers with no auth (`operations.py:75`). The plan explicitly accepts this as best-effort, so this is by design; flagging it so it's understood that operator identity is unauthenticated in audit rows.

4. **Early-exit on absent worktree** (`_handle_delete_worktree` line 458) returns `completed` with no heartbeat check; harmless but inconsistent with the other gating. Audit row is still written by `_audit`.

## Verdict

The implementation matches the plan exactly: 12-operation registry, runner-state guardrails (with positive and negative tests), full audit logging in both tables, path-traversal and heartbeat guards on destructive ops, four-group panel with safety badges and typed-id gating, no scheduler/worker logic changes. All targeted tests pass. The observations above are quality refinements, not corrections needed for merge.

IMPLEMENTATION_APPROVED
