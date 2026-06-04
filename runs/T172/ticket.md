# T172 — T172 - Environment runtime must fully originate from the selected project branch, including supervisor and daemon

**Source**: GitHub Issue #197

## Description

# T172 - Environment runtime must fully originate from the selected project branch, including supervisor and daemon

## Problem

T171 introduces fresh runtime cloning per environment so deployments use the selected branch instead of stale local worktrees.

However, there is still architectural ambiguity about runtime ownership.

Currently the system still appears partially coupled to the global `ai-dev-factory` control plane runtime:

- supervisor
- daemon/worker
- runtime scripts
- deployment orchestration

This creates a hybrid model where:

- application code comes from the selected branch;
- but runtime orchestration may still come from the host ai-dev-factory instance.

That prevents the environment system from becoming truly generic and repository-driven.

---

## Goal

An environment deployment must behave as a self-contained runtime instance of the selected project branch.

The selected repository + branch must become the authoritative source for:

- bootstrap
- build
- start
- healthcheck
- supervisor
- daemon/worker
- compose files
- runtime configuration
- project-specific orchestration logic

The global control plane should only orchestrate:

```text
clone → checkout → bootstrap → build → start → monitor → cleanup
```

but should not substitute its own local runtime implementation for the deployed project.

---

## Required behavior

When deploying:

```text
project = X
branch = Y
environment = Z
```

The system must:

1. clone the selected repository branch fresh into the environment runtime;
2. execute project runtime scripts from that clone;
3. start supervisor/daemon components from the cloned project if the project defines them;
4. isolate runtime behavior per environment;
5. avoid hidden dependency on the host ai-dev-factory checkout.

---

## Required architecture clarification

The following distinction must be explicit:

### Global control plane responsibilities

Allowed:

- environment orchestration
- lifecycle management
- environment registry/state
- UI/API management
- monitoring
- environment cleanup
- infra bootstrap

### Project runtime responsibilities

Must come from cloned project source:

- bootstrap.sh
- build.sh
- start.sh
- healthcheck.sh
- supervisor implementation
- daemon/worker implementation
- compose configuration
- project runtime logic

---

## Important constraints

Do NOT:

- execute runtime scripts from the host ai-dev-factory checkout;
- mix runtime files from different branches/projects;
- silently fallback to global runtime scripts;
- assume ai-dev-factory-specific paths/layouts inside generic environments.

---

## Acceptance criteria

- Deploying branch T170 uses the T170 supervisor/runtime implementation
- Runtime scripts executed during deployment originate from the cloned project branch
- Different environments can run different runtime implementations simultaneously
- Environment behavior no longer depends on the host ai-dev-factory checkout state
- Deploying another repository works without ai-dev-factory-specific assumptions
- Supervisor/daemon isolation works correctly per environment
