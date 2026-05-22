# T139 — T139 — Runtime dashboard for sandboxes and proposals

**Source**: GitHub Issue #127

## Description

Create a runtime dashboard to manage sandbox runs, proposal runs, logs and cleanup operations.

Context:
The platform now creates many runtime artifacts such as sandboxes, worktrees, logs, compose projects, pid files and proposal runs. A dedicated operational dashboard is needed.

Scope:
- list sandbox runs with status, timestamps, ports, worktree path and logs
- actions to refresh, rerun validation, stop and cleanup a sandbox
- list proposal runs with proposal id, sandbox id, status and changed files
- actions to open proposal, inspect patches and delete proposals
- runtime health section with supervisor status, active jobs, stale pid files and stale locks
- cleanup tools for stale worktrees, stale sandbox directories and orphan runtime artifacts
- live log refresh and tailing
- generic metadata-driven UI with no project-specific assumptions
- cleanup safety checks preventing deletion of active jobs or main runtime artifacts

Out of scope:
- automatic proposal apply
- automatic merge
- cloud deployment
- tester-agent orchestration

Acceptance:
- dashboard shows sandbox runs and proposal runs
- logs are accessible from the UI
- stale runtime artifacts can be cleaned safely
- runtime health is visible
- cleanup never impacts the main runtime
- active jobs cannot be deleted accidentally
- no project-specific assumptions exist
