Good — the generic prompts follow the same naming convention as the agent roles. Here is the implementation plan:

---

## Objective

Add the conflict resolver agent that runs inside the existing ticket worktree, collects full ticket and conflict context, rebases the branch, invokes the AI resolver to fix conflicts, runs tests, pushes the resolved branch with `--force-with-lease`, and gates resumption of the workflow on a human approve/reject review step exposed in the dashboard.

## Included

### State machine — `tools/agent_runner/run_ticket.py`
- Add `CONFLICT_RESOLVING` and `CONFLICT_RESOLVED_REVIEW_NEEDED` to `VALID_STATES`
- Add transitions:
  - `CONFLICT_RESOLUTION_NEEDED` → (user-triggered) → `CONFLICT_RESOLVING`
  - `CONFLICT_RESOLVING` → (resolver success) → `CONFLICT_RESOLVED_REVIEW_NEEDED`
  - `CONFLICT_RESOLVING` → (resolver failure) → `CONFLICT_RESOLUTION_FAILED`
  - `CONFLICT_RESOLVED_REVIEW_NEEDED` → (approve) → restore `pre_conflict_state`
  - `CONFLICT_RESOLVED_REVIEW_NEEDED` → (reject) → `CONFLICT_RESOLUTION_NEEDED`
- `CONFLICT_RESOLVING` is **not** auto-runnable (spawned explicitly by API)
- `CONFLICT_RESOLVED_REVIEW_NEEDED` is human-gated

### Context collector — `tools/agent_runner/conflict_context_collector.py` (new)
- Read from `state.json`: `conflict_pr_number`, `conflicted_files`, `pre_conflict_state`, `conflict_detected_at`
- Collect: `ticket.md`, `plan.md`, `reviews/*.md`, fixes
- Collect: PR diff via `gh pr diff <pr_number>`
- Collect: merge-base diff via `git diff $(git merge-base main HEAD)..HEAD` inside the worktree
- Collect: latest main changes since conflict detection via `git log main --oneline --since=<conflict_detected_at>`
- Collect: full content of each conflicted file (with conflict markers)
- Write assembled context to `runs/{TXXX}/conflict/context.md`

### Resolver role — `ai/roles/conflict-resolver.md` (new)
- Role instructions: read context.md, edit conflicted files in-place, preserve both ticket intent and main behavior
- Safety rules embedded: no blind ours/theirs, no reset, no merge to main
- Output: `conflict/resolution.md` summarising each conflict decision

### Generic prompt — `prompts/generic/conflict-resolver.md` (new)
- Task template passed to the AI runtime via stdin
- References `conflict/context.md` and instructs writing `conflict/resolution.md`

### Resolver executor — `tools/agent_runner/run_conflict_resolver.py` (new)
- Guard: abort if current branch is `main`
- `git fetch origin && git rebase origin/main` inside the ticket worktree
- On rebase conflict: run context collector, then invoke AI agent via `run_step.execute_external_command` with composed prompt
- After AI edits: `git add` resolved files, `git rebase --continue`
- Run test suite (via existing tester pattern or `run_step` with `tester` step), write `conflict/test-report.md`
- Commit all resolution artifacts with message `conflict(T{id}): resolve conflicts against main`
- `git push --force-with-lease origin <branch>`
- On success: transition state → `CONFLICT_RESOLVED_REVIEW_NEEDED`
- On any failure: transition state → `CONFLICT_RESOLUTION_FAILED`, persist stderr to `conflict/error.log`

### API endpoints — `services/control_api/routes/tickets.py`
- `POST /tickets/{ticket_id}/resolve-conflicts` — validates state is `CONFLICT_RESOLUTION_NEEDED`, transitions to `CONFLICT_RESOLVING`, spawns resolver as background subprocess
- `POST /tickets/{ticket_id}/approve-conflict-resolution` — validates state is `CONFLICT_RESOLVED_REVIEW_NEEDED`, transitions to `pre_conflict_state` from `state.json`
- `POST /tickets/{ticket_id}/reject-conflict-resolution` — validates state is `CONFLICT_RESOLVED_REVIEW_NEEDED`, transitions back to `CONFLICT_RESOLUTION_NEEDED`
- Project-scoped variants (`/projects/{project_id}/tickets/{ticket_id}/...`) for all three
- Return `ActionResult` (existing model) for all endpoints

### Data model — `services/control_api/models/schemas.py`
- Add to `TicketSummary`: `resolution_summary: str | None`, `conflict_test_result: str | None`

### Artifact reader — `services/control_api/services/artifact_reader.py`
- Read `conflict/resolution.md` → populate `resolution_summary`
- Read `conflict/test-report.md` → populate `conflict_test_result`
- Read `conflict/context.md` for changed-files list (parse header section)

### Dashboard — `apps/dashboard/src/pages/TicketDetailPage.jsx`
- Add conflict resolution panel, shown when state ∈ `{CONFLICT_RESOLUTION_NEEDED, CONFLICT_RESOLVING, CONFLICT_RESOLVED_REVIEW_NEEDED, CONFLICT_RESOLUTION_FAILED}`:
  - `CONFLICT_RESOLUTION_NEEDED`: "Resolve Conflicts" button → calls `POST /resolve-conflicts`
  - `CONFLICT_RESOLVING`: spinner + live log polling
  - `CONFLICT_RESOLVED_REVIEW_NEEDED`: resolution summary, changed files, test results, Approve / Reject buttons
  - `CONFLICT_RESOLUTION_FAILED`: error log display
- Wire Approve → `POST /approve-conflict-resolution`, Reject → `POST /reject-conflict-resolution`

### Dashboard — `apps/dashboard/src/pages/TicketsPage.jsx`
- Add badge styles for `CONFLICT_RESOLVING` (yellow) and `CONFLICT_RESOLVED_REVIEW_NEEDED` (blue)

## Excluded

- Global multi-branch dependency planning
- Automatic merge to main
- Production deployment conflict handling
- Semantic ticket tree planning
- Retry count limits or backoff for repeated conflict resolution failures
- Conflict resolution for branches other than the active ticket branch

## Acceptance criteria

- `VALID_STATES` and `TRANSITIONS` in `run_ticket.py` include both new states with correct edges
- `POST /resolve-conflicts` returns 409 if ticket is not in `CONFLICT_RESOLUTION_NEEDED`
- `POST /resolve-conflicts` transitions state to `CONFLICT_RESOLVING` and spawns the resolver
- Resolver aborts and logs an error if the target branch is `main`
- `conflict/context.md` is present in the run directory after context collection, containing ticket.md, plan.md, PR diff, conflicted file contents, and latest main log
- AI agent receives the composed prompt (role + context) via stdin following the `run_step` pattern
- `conflict/resolution.md` and `conflict/test-report.md` are committed to the ticket branch
- Branch is pushed with `--force-with-lease`; push fails gracefully if lease is broken (transitions to `CONFLICT_RESOLUTION_FAILED`)
- On success, state transitions to `CONFLICT_RESOLVED_REVIEW_NEEDED`
- On any failure, state transitions to `CONFLICT_RESOLUTION_FAILED` and `conflict/error.log` is written
- `POST /approve-conflict-resolution` restores `pre_conflict_state` from `state.json` (returns 409 if wrong state)
- `POST /reject-conflict-resolution` transitions back to `CONFLICT_RESOLUTION_NEEDED` (returns 409 if wrong state)
- Dashboard detail page shows "Resolve Conflicts" button in `CONFLICT_RESOLUTION_NEEDED`
- Dashboard detail page shows resolution summary, changed files, and test results in `CONFLICT_RESOLVED_REVIEW_NEEDED`
- Dashboard detail page shows Approve and Reject buttons in `CONFLICT_RESOLVED_REVIEW_NEEDED`
- `TicketSummary` API response includes `resolution_summary` and `conflict_test_result` fields when artifacts are present
- Badge styles for `CONFLICT_RESOLVING` and `CONFLICT_RESOLVED_REVIEW_NEEDED` render in the tickets list
