# T118 — T118 — Add daemon runtime heartbeat endpoint

**Source**: GitHub Issue #75

## Description

## Context

T117 stabilized the runtime architecture and autonomous daemon workflow.

We now need a very small end-to-end validation ticket to confirm that the full autonomous lifecycle works correctly:

- issue intake
- worktree creation
- planner
- human plan approval
- coder
- reviewer
- tester
- automatic commit/push
- PR update

The implementation itself should remain intentionally trivial.

---

## Objective

Add a lightweight daemon heartbeat endpoint.

---

## Requirements

Create a new endpoint:

```text
GET /daemon/heartbeat
```

Response JSON:

```json
{
  "timestamp_utc": "2026-05-19T22:00:00Z",
  "runtime_root": "/runtime",
  "daemon_running": true
}
```

---

## Constraints

- minimal implementation
- no new dependencies
- no refactor
- no architecture changes
- keep implementation intentionally small

---

## Validation goal

The main goal of T118 is NOT the endpoint itself.

It is validating that the autonomous workflow can now complete successfully with:

- automatic checkpoint commits
- automatic pushes
- stable worktree lifecycle
- stable daemon execution
- stable PR lifecycle
