# Plan fix — T143 V1

## New objective

Implement safe conflict detection and visibility for ticket branches and PRs.

The system should:

- detect conflicting ticket branches
- preserve workflow state before conflict
- expose conflict status in the dashboard
- expose conflicted files and metadata

The system must NOT automatically rewrite branches yet.

This ticket intentionally focuses on:

- workflow safety
- observability
- dashboard visibility
- conflict state transitions

before introducing AI-driven conflict resolution.

---

# Included

## Workflow states

Add:

- CONFLICT_RESOLUTION_NEEDED
- CONFLICT_RESOLUTION_FAILED

Persist:

- pre_conflict_state

in state.json.

## Conflict detection

Detect:

- PR merge conflicts (`gh pr view --json mergeable`)
- failed branch sync/rebase situations

Do NOT attempt automatic conflict resolution.

## Conflict metadata

Collect and persist:

- conflicted files
- PR number
- branch name
- detection timestamp
- previous workflow state

## Dashboard visibility

Expose in dashboard:

- conflict badge
- conflict status
- conflicted files
- previous workflow state
- manual action required

## API additions

Expose conflict state and metadata through ticket endpoints.

## Tests

Add tests for:

- conflict state transitions
- pre_conflict_state persistence
- conflict detection mocks
- dashboard serialization
- conflict metadata persistence

---

# Excluded

Do NOT implement in this ticket:

- AI conflict resolver agent
- automatic rebases
- branch rewriting
- force-with-lease pushes
- automatic conflict fixes
- automatic workflow resume
- approve-conflict-resolution endpoint
- automatic test execution after conflicts

These should be handled in a later dedicated resolver ticket.

---

# Acceptance criteria

- conflicting PRs or branches enter CONFLICT_RESOLUTION_NEEDED
- pre_conflict_state is persisted safely
- conflicted files are visible in the dashboard
- conflict metadata is exposed through the API
- no automatic branch rewriting occurs
- no automatic pushes occur
- manual review/action is required after conflict detection
