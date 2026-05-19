# T117 — T117 — Restore fully autonomous daemon workflow after runtime migration

**Source**: GitHub Issue #71

## Description

## Context

T115 and T116 migrated ai-dev-factory toward a canonical runtime architecture with Docker API/dashboard and runtime-root ownership.

The core runtime model now works:
- canonical runtime root
- Docker dashboard/API
- GitHub intake
- runtime worktrees
- daemon host-side execution
- populated board

However the autonomous daemon workflow is still fragile.

---

## Objective

Restore a stable end-to-end autonomous workflow with only one mandatory human gate:

PLAN_REVIEW_NEEDED

Everything after plan approval should run automatically until TEST_COMPLETE.

---

## Expected workflow

GitHub issue (ai-ready)
→ intake
→ worktree creation
→ planner
→ PLAN_REVIEW_NEEDED
→ human approve plan
→ coder auto
→ reviewer auto
→ tester auto
→ TEST_COMPLETE

No terminal commands should be required for the normal workflow.

---

## Problems observed

### Daemon UI button not reliable
The dashboard daemon start/restart actions do not reliably launch the correct host-side daemon runtime.

### _intake worktree fragility
_intake may remain on ticket branches.
Branch restoration may fail because runtime.log changes block checkout.

### runtime.log conflicts
runtime.log should never participate in git conflicts/rebases/checkpoints.

### Missing auto checkpoint lifecycle
Some workflow transitions do not auto-commit/push runtime artifacts.

### Legacy fallback still triggered
Worktree creation failures still trigger legacy fallback behavior.

### Detached HEAD/rebase friction
Auto-generated runtime commits frequently create non-fast-forward or rebase conflicts.

---

## Deliverables

- stable daemon start/restart from dashboard
- reliable _intake lifecycle
- runtime.log excluded from git lifecycle conflicts
- automatic checkpoint/commit/push after workflow transitions
- remove unnecessary legacy fallbacks
- stable worktree ownership
- stable autonomous execution after plan approval
- documentation of expected daemon lifecycle

---

## Constraints

- keep daemon host-side for now
- preserve canonical runtime architecture from T116
- do not regress Docker API/dashboard
- do not reintroduce repo-local runtime ownership
