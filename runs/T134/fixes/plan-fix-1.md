# Plan fix — T134 V1

## New objective

Implement a first version of sandbox deployment validation from the Deployer UI.

The system must:

- create an isolated sandbox automatically
- create an isolated git worktree automatically
- execute generated operational scripts inside the sandbox
- execute healthcheck.sh
- capture logs and results
- expose deployment status in the dashboard

This ticket is intentionally limited to deployment validation.

AI auto-fix loops are excluded from this version.

---

# Included

## Deployer UI

Add a new action in Deployer page:

```text
Deploy & Test in Sandbox
```

The user must NOT manually provide:

- ticket id
- sandbox id
- runtime path
- worktree path

The system generates them automatically.

## Sandbox creation

Automatically create:

- isolated sandbox runtime
- isolated worktree
- isolated logs directory

under the runtime tree.

## Script execution flow

Execute in order:

1. bootstrap.sh
2. build.sh
3. start.sh
4. healthcheck.sh

Capture:

- stdout
- stderr
- exit codes
- execution timestamps

## Dashboard state

Expose:

- pending
- running
- success
- failed

with logs visible from the Deployer page.

## Runtime safety

The sandbox execution must NOT modify the main runtime environment.

All execution must occur in:

- isolated worktree
- isolated runtime directory
- isolated logs

## Tests

Add tests for:

- sandbox creation
- worktree creation
- successful deploy validation
- failed healthcheck
- log capture
- deploy state transitions

---

# Excluded

- AI-generated fix loops
- automatic script patching
- automatic commit/push after failures
- retry loops
- PR updates
- remote/cloud deployment
- tester-agent integration
- automatic port allocation
- parallel sandbox orchestration

---

# Acceptance criteria

- Deployer page exposes a Deploy & Test in Sandbox action
- A sandbox is automatically created
- A worktree is automatically created
- Generated scripts execute inside the sandbox
- healthcheck.sh determines success/failure
- Logs are visible in the dashboard
- Main runtime environment remains unaffected
- Failed validations stop cleanly with visible errors
