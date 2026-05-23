# T144 — T144 — Conflict resolver agent and review UI

**Source**: GitHub Issue #138

## Description

Goal: add the conflict resolver agent that resolves detected PR conflicts inside the existing ticket worktree, then exposes the result through a dedicated dashboard review flow.

Context:
T143 detects PR conflicts, persists conflict metadata, and surfaces conflict state in the dashboard.

T144 is the next step: run a resolver agent with full ticket context, update the conflicted branch safely, and require human review before the workflow resumes.

Target workflow:
- ticket is in CONFLICT_RESOLUTION_NEEDED
- user clicks Resolve Conflicts in the dashboard
- resolver runs in the existing ticket worktree
- resolver collects ticket context
- resolver rebases or merges latest main into the ticket branch
- resolver fixes conflicts
- relevant tests run
- branch is pushed with force-with-lease
- ticket moves to CONFLICT_RESOLVED_REVIEW_NEEDED
- dashboard shows resolution summary, logs, changed files, tests and review actions

Scope:
- add workflow states:
  - CONFLICT_RESOLVING
  - CONFLICT_RESOLVED_REVIEW_NEEDED
- add resolver execution step in the ticket worktree
- collect context for the resolver:
  - ticket.md
  - plan.md
  - reviews
  - fixes
  - conflict metadata
  - PR diff
  - merge-base diff
  - conflicted files
  - latest main changes
- add dedicated resolver role/prompt
- run resolver via existing configured AI runtime
- resolve conflicts by editing files in the ticket worktree
- run relevant tests after resolution
- write resolver artifacts:
  - conflict/context.md
  - conflict/resolution.md
  - conflict/test-report.md
- commit resolution changes and artifacts
- push the PR branch with force-with-lease
- add dashboard UI:
  - Resolve Conflicts button
  - resolving status
  - resolver logs
  - conflicted files
  - changed files
  - test result
  - resolution summary
  - approve/reject review gate
- add API endpoints for starting resolver and approving/rejecting resolution

Safety rules:
- do not resolve conflicts in main
- do not reset the branch
- do not blindly choose ours/theirs
- do not auto-merge to main
- require human review after resolution
- preserve both ticket intent and latest main behavior when possible
- all changes happen inside the ticket worktree

Out of scope:
- global multi-branch dependency planning
- automatic merge to main
- production deployment conflict handling
- semantic ticket tree planning

Acceptance:
- user can launch conflict resolution from dashboard
- resolver runs in the existing ticket worktree
- resolver receives full ticket and conflict context
- resolved branch is pushed with force-with-lease
- resolver artifacts are persisted
- dashboard shows status, summary, changed files and tests
- human approve/reject gate is required before workflow resumes
- failure ends in CONFLICT_RESOLUTION_FAILED with logs
