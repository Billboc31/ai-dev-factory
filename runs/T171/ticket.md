# T171 — T171 - Environment deploy should use a fresh runtime checkout of the selected branch

**Source**: GitHub Issue #194

## Description

# T171 - Environment deploy should use a fresh runtime checkout of the selected branch

## Problem

Environment deploy currently appears to reuse an existing local project/worktree instead of building from a fresh checkout of the selected repository branch.

Observed effects:

- a branch is selected in the environment UI;
- deploy logs show scripts executing;
- but the deployed code does not match the selected branch;
- fixes present on ticket branches are missing at runtime;
- stale local worktrees influence deployments unexpectedly.

This makes deployments unreliable because the selected branch is not guaranteed to be the code actually deployed.

---

## Goal

Environment deploy must always use a fresh runtime checkout of the selected repository and branch.

Deployments should no longer depend on arbitrary existing local project folders.

---

## Required behavior

For a selected:

- project
- repository
- branch
- environment

The deploy flow must:

1. create a clean runtime source directory;
2. clone the repository into that runtime directory;
3. checkout the selected branch;
4. verify branch and commit before build/start;
5. run bootstrap/build/start/healthcheck from that runtime checkout.

---

## Suggested runtime structure

Example:

```text
environment/<env-id>/
  source/
  runtime/
```

Where:

- `source/` contains the runtime git checkout;
- `runtime/` contains logs/state/validation artifacts.

Equivalent layouts are acceptable if deployments are isolated and deterministic.

---

## Validation

Before build/start, log:

```bash
pwd
git branch --show-current
git rev-parse --short HEAD
```

If the checked out branch does not match the selected branch, deployment must fail.

---

## Important constraints

Do NOT:

- silently fallback to another branch;
- deploy from main when another branch was selected;
- reuse stale local clones unless explicitly requested;
- infer deployment source from the current shell directory.

---

## Acceptance criteria

- Deploying an environment from T170 actually deploys T170 code
- Runtime scripts executed during deploy come from the selected branch
- Branch verification appears in deployment logs
- Existing unrelated local worktrees no longer affect deployments
- Failed clone/checkout aborts deployment clearly
- Multiple environments can deploy different branches concurrently
