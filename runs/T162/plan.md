The audit reveals the root cause clearly. Now I can produce the plan.

---

## Objective

Repair the broken state propagation between GitHub PR conflict detection and the runtime ticket workflow, so that when `auto_merge_pr()` detects a conflicting PR and skips the merge, the ticket automatically transitions to the existing `CONFLICT_RESOLUTION_NEEDED` state and exposes the existing Resolve Conflicts dashboard action — without any manual SQLite intervention.

## Included

**1. `tools/agent_runner/run_daemon.py` — Fix `handle_test_complete()` (primary bug)**

After `auto_merge_pr()` returns `False` due to a conflicting PR, the state stays `TEST_COMPLETE`, which is in `_CONFLICT_SKIP_STATES`. The daemon loop therefore never calls `detect_pr_conflict()`, and the ticket is stuck.

Fix: in `handle_test_complete()`, after `auto_merge_pr()` returns `False`, immediately call `detect_pr_conflict()` (which already exists and handles the full transition — writes `pre_conflict_state`, `conflict_detected_at`, `conflict_pr_number`, `conflicted_files`, and sets `state = CONFLICT_RESOLUTION_NEEDED` in `state.json` + runtime DB).

**2. `tools/agent_runner/run_daemon.py` — Audit `_CONFLICT_SKIP_STATES`**

Verify whether `TEST_COMPLETE` is listed in `_CONFLICT_SKIP_STATES`. If it is, either:
- Remove it from the skip set (if safe), or
- Confirm the fix in point 1 is sufficient and leave it in the skip set (conflict detection is called explicitly before the skip check runs).

**3. `tools/agent_runner/run_daemon.py` — Improve observability logs**

Add explicit log lines in the conflict propagation path:
- When `auto_merge_pr()` detects CONFLICTING but `state.json` has no `pr_number` → log `PR conflict detected but no PR number in state.json for ticket {ticket_id}`.
- When `detect_pr_conflict()` is called but fails to transition → log `Failed to transition ticket {ticket_id} to CONFLICT_RESOLUTION_NEEDED`.
- When the ticket is already in `CONFLICT_RESOLUTION_NEEDED` on next cycle → log `Ticket {ticket_id} already in CONFLICT_RESOLUTION_NEEDED, skipping re-detection`.

**4. `tools/agent_runner/run_daemon.py` — Audit PR ↔ ticket mapping for renamed issues/branches**

Inspect the dispatch loop's mapping function to confirm the lookup path:
- Ticket found via `issue_number` (integer, stable) or branch name (mutable)?
- If a branch is renamed, does `state.json` still carry the correct `pr_number`?
- If `gh pr view` uses the branch name as a key, a renamed branch will break the lookup.

Fix: ensure the mapping uses `pr_number` (already persisted in `state.json`) rather than branch name as the primary lookup key.

**5. Verification (no code change expected)**

Confirm that the existing `TicketDetailPage.jsx` `ConflictResolutionPanel` already renders the "Resolve Conflicts" button when `ticket.state === "CONFLICT_RESOLUTION_NEEDED"`. Per the audit this is already wired correctly — no dashboard change needed.

## Excluded

- Rewriting `run_conflict_resolver.py` or the resolver agent.
- New conflict resolution architecture or agents.
- Replacing or extending T143/T144 resolver flows.
- Adding new SQLite columns for conflict metadata (state.json is the designated store, by existing design).
- New GitHub synchronization system or merge engine.
- Any change to `TicketDetailPage.jsx` or API routes (they already handle conflict states correctly).

## Acceptance criteria

- When `auto_merge_pr()` logs "PR has conflicts — skipping", the ticket transitions to `CONFLICT_RESOLUTION_NEEDED` within the same daemon handler call (not deferred to next cycle).
- `state.json` for the affected ticket contains `pre_conflict_state`, `conflict_detected_at`, `conflict_pr_number`, and `conflicted_files` after the transition.
- The dashboard "Resolve Conflicts" button becomes visible without any manual SQLite edits.
- A ticket whose branch was renamed still resolves correctly because the lookup uses `pr_number` from `state.json`.
- Runtime log contains an explicit line identifying failed mapping or failed transition (e.g. `Failed to transition ticket T155 to CONFLICT_RESOLUTION_NEEDED`).
- Existing T143/T144 flows — `CONFLICT_RESOLVING → CONFLICT_RESOLVED_REVIEW_NEEDED` and the approve/reject cycle — continue to function after the state is entered via this repaired path.
