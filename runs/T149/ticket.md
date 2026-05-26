# T149 — T149 — Sandbox lifecycle modes and stale running cleanup

**Source**: GitHub Issue #146

## Description

Goal: separate ephemeral sandbox validation from persistent sandbox environments, and fix stale running states after cleanup.

Context:
Current sandbox validation can deploy, test, stop and cleanup. But after a completed or deleted sandbox, clicking again may still return `already running`, meaning stale locks/state remain.

There is also a product need for two different sandbox modes:
- Deploy & Test: ephemeral validation that runs scripts, healthcheck, then undeploys/cleans up
- Start Environment: persistent sandbox environment that stays running until the user stops or deletes it

Scope:
- fix stale `already running` after deploy/test/cleanup
- ensure locks, pid files and running markers are always released after terminal states
- introduce explicit sandbox lifecycle modes: validation and environment
- validation mode should deploy, healthcheck, undeploy and cleanup
- environment mode should deploy and stay running
- environment mode must be visible in the dashboard with explicit Stop and Delete actions
- state model should distinguish running, validating, validated, failed, stopped and cleaned states
- UI should expose separate actions: Deploy & Test and Start Environment
- cleanup must remain idempotent and safe
- persistent environments must still use isolated ports, runtime root, compose project and supervisor/daemon context

Tests:
- validation mode releases running locks after completion
- cleanup clears stale running state
- clicking Deploy & Test again after cleanup starts a new validation
- Start Environment keeps sandbox running after healthcheck
- Stop Environment stops services but preserves useful logs/state
- Delete Environment removes runtime/worktree safely
- validation and environment modes do not conflict

Out of scope:
- AI auto-fix loops
- production deployment
- cloud deployment
- distributed sandbox scheduling

Acceptance:
- after a completed validation, starting another validation never incorrectly returns `already running`
- after deleting a sandbox, starting a new one never incorrectly returns `already running`
- user can choose between ephemeral validation and persistent environment
- persistent environments stay alive until explicitly stopped/deleted
- dashboard clearly shows lifecycle mode and state
- cleanup remains safe and idempotent
