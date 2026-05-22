# Plan fix request — T135

Please reduce T135 to a minimal isolation V1.

## T135 V1 objective

Introduce safe isolated analysis worktrees and correct Docker-to-host path mapping for supervisor analysis jobs.

The goal of V1 is only:

- analysis jobs never run directly in the main runtime worktree
- supervisor never receives invalid Docker container paths like `/app`

## Include in V1

### Docker → host path mapping

- Add a small path-mapping utility.
- Translate container paths to host paths before supervisor subprocess execution.
- Add tests for path translation.
- Add clear logs showing:
  - container path
  - mapped host path

### Isolated analysis worktrees

- `run_analysis.py` creates a dedicated isolated worktree.
- Analysis, file generation and git operations run only inside the isolated worktree.
- Worktree cleanup runs in `finally` blocks.
- Add tests ensuring analysis jobs never write directly into the main runtime worktree.

### Minimal dashboard visibility

- Expose worktree path in analysis status.
- Display worktree isolation status in the dashboard.

## Exclude from V1

- `run_scripts.py`
- deploy sandbox runtime
- compose project isolation
- dynamic ports
- isolated env files
- cleanup endpoints
- full job runtime layout redesign
- deploy/test/fix loop
- tester agent

## Acceptance criteria

- Supervisor receives valid host filesystem paths instead of `/app`.
- Analysis jobs create isolated worktrees.
- Generated files and commits occur only inside isolated worktrees.
- Worktrees are cleaned after job completion.
- Dashboard displays analysis worktree path.
- Existing daemon/runtime workflows continue to work.
