# T135 — T135 — Isolated analysis and deploy worktrees

**Source**: GitHub Issue #108

## Description

Add isolated worktree and runtime environments for AI analysis, deploy generation and deploy validation workflows.

Scope:
- create dedicated analysis/deploy worktrees per ticket or job
- map Docker container paths to host worktree paths correctly
- isolated runtime roots
- isolated compose project names
- isolated env files and ports
- cleanup of completed/failed worktrees
- dashboard visibility for sandbox/worktree state
- tests for worktree isolation and host path mapping

Out of scope:
- deploy/test/fix retry loop
- tester agent
- production deployment
- remote/cloud deployment

Acceptance:
- analysis jobs never run against the main runtime worktree
- supervisor always receives valid host paths
- generated files are committed from isolated worktrees
- sandbox deploys cannot impact the main runtime
- cleanup works correctly
- existing daemon/runtime workflows continue to work
