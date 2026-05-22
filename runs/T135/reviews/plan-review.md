# Plan review — T135

Decision: PLAN_FIX_REQUIRED

The current plan is directionally correct, but too large for one safe ticket.

It mixes too many concerns at once:

- Docker-to-host path mapping
- isolated analysis worktrees
- isolated script-generation worktrees
- job-scoped runtime directories
- sandbox compose project names and ports
- cleanup endpoints
- dashboard worktree visibility
- multiple new test suites

This is a critical isolation layer. It should be introduced in a smaller V1 before extending it to scripts and deploy sandboxes.

Requested action:

Rewrite T135 as a minimal V1 focused only on host path mapping and isolated analysis worktrees.

See `runs/T135/fixes/plan-fix-1.md` for the requested reduced scope.
