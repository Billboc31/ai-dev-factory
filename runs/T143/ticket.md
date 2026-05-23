# T143 — T143 — Conflict resolver agent for PR branch rebases

**Source**: GitHub Issue #134

## Description

Goal: add a conflict resolver agent that detects PR/branch conflicts, resolves them in the ticket worktree with full ticket context, and updates the PR safely.

Context:
As the system starts coding multiple tickets in parallel, PR branches will regularly conflict with main. Conflict resolution must be handled with context, not by blindly choosing ours/theirs.

Target workflow:
- PR or ticket branch conflict detected
- ticket state moves to CONFLICT_RESOLUTION_NEEDED
- conflict resolver agent runs in the existing ticket worktree
- agent rebases the ticket branch on latest main
- agent resolves conflicts using ticket context
- tests run
- branch is pushed with force-with-lease
- ticket state moves to CONFLICT_RESOLVED_REVIEW_NEEDED
- dashboard shows resolver summary and review gate

Scope:
- add conflict detection for PR branches or failed branch sync/rebase
- add new workflow states:
  - CONFLICT_RESOLUTION_NEEDED
  - CONFLICT_RESOLVING
  - CONFLICT_RESOLVED_REVIEW_NEEDED
  - CONFLICT_RESOLUTION_FAILED
- run resolver inside the ticket worktree, not main
- collect context for the resolver:
  - ticket.md
  - plan.md
  - reviews
  - fixes
  - PR diff
  - merge-base diff
  - conflicted files
  - latest main changes
- compose a dedicated resolver prompt
- resolve conflicts by editing files in the ticket worktree
- run relevant tests after resolution
- commit resolution artifacts and code changes
- push branch with force-with-lease
- dashboard must display:
  - conflicted files
  - resolver status
  - resolver summary
  - tests result
  - review gate after resolution

Safety rules:
- do not resolve conflicts in main
- do not reset the branch
- do not overwrite main behavior blindly
- preserve both ticket intent and latest main behavior when possible
- do not auto-merge after resolution
- require human review after conflict resolution

Out of scope:
- resolving production deployment conflicts
- automatic merge to main
- multi-branch global planning
- semantic dependency graph construction

Acceptance:
- a conflicting ticket branch can enter CONFLICT_RESOLUTION_NEEDED
- resolver runs in the ticket worktree
- resolver receives ticket context and conflicted file list
- resolved branch is pushed safely
- dashboard exposes conflict status and summary
- human review is required before continuing
- failures end in CONFLICT_RESOLUTION_FAILED with logs
