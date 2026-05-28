# T157 — T157 - Ensure deployer fetches and checks out the requested branch before deployment

**Source**: GitHub Issue #164

## Description

## Objective

Ensure the deployer always deploys the exact requested ref/branch, not a stale local checkout or an outdated main branch.

## Context

Recent runtime UI changes were pushed to a ticket branch, but the deployed sandbox did not visually reflect them. A likely cause is that the deployer creates or reuses a worktree without first fetching the remote and checking out the requested branch/ref at the latest remote commit.

This breaks confidence in runtime validation: a sandbox URL may be healthy while serving old code.

## Problem

The deployer must make the deployed code identity explicit and deterministic.

Current risks:

- deploying stale `main`
- deploying a stale local branch
- deploying a branch before fetching recent remote pushes
- not showing clearly which commit/ref was deployed
- validating the wrong code while healthcheck/smoke tests still pass

## Expected behavior

Before deploying a sandbox, the deployer must:

1. Resolve the requested ref/branch explicitly.
2. Fetch the remote branch before checkout.
3. Create/update the sandbox worktree from the fetched remote ref.
4. Record the deployed ref, branch, and commit SHA in sandbox state/metadata.
5. Fail early with a clear error if the requested ref cannot be fetched or resolved.

For a ticket branch such as:

```text
ticket/T156-t156-improve-runtime-tab-with-running-environments
```

The deployer should fetch and deploy the latest remote commit for that exact branch.

## Included

- Update deployer/sandbox bootstrap logic so requested branch/ref is fetched before worktree creation or reuse.
- Prefer deterministic remote refs such as `origin/<branch>` when deploying ticket branches.
- Ensure worktree checkout points to the latest fetched commit for the requested branch.
- Persist deployed identity in sandbox state, including:
  - requested_ref
  - resolved_ref
  - branch name when applicable
  - commit SHA
- Add logs showing:
  - requested ref
  - fetched remote ref
  - resolved commit SHA
  - worktree path
- Add/adjust tests for stale branch prevention.

## Excluded

- No changes to Traefik routing.
- No changes to port allocation.
- No changes to smoke test semantics.
- No automatic merge/rebase behavior.
- No mutation of the main production clone beyond safe `git fetch`.
- No persistent environment management changes.

## Constraints

- Never mutate the main clone working tree.
- Work must happen in sandbox worktrees.
- `git fetch` is allowed on the source clone, but deployment checkout must remain isolated.
- If the branch does not exist remotely, fail loudly instead of silently falling back to `main`.
- Do not infer GitHub issue number from ticket id.

## Acceptance criteria

- Deploying a ticket branch fetches the latest remote commit before sandbox creation.
- The sandbox worktree HEAD equals the fetched remote branch HEAD.
- If a new commit is pushed to a ticket branch, a subsequent deploy uses that new commit.
- If the requested branch/ref does not exist, deployment fails with a clear error and does not deploy `main` silently.
- Sandbox state/metadata exposes the deployed ref and commit SHA.
- Runtime UI can display the deployed commit/ref from sandbox metadata.
- Existing deploys from `main` still work.
- Existing sandbox isolation guarantees remain intact.
