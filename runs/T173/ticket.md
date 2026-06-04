# T173 — T173 - Environment runtime must use committed project scripts from selected branch

**Source**: GitHub Issue #198

## Description

# T173 - Environment runtime must use committed project scripts from selected branch

## Problem

T172 was closed and needs to be recreated with the same intent in a clearer form.

Environment deploy must be generic and repository-driven.

The selected repository branch already contains generated deployment/runtime scripts committed under:

```text
.ai-dev-factory/scripts/
```

The environment runtime must execute those committed scripts from the selected branch clone.

It must not execute scripts from the host/global ai-dev-factory checkout.

---

## Goal

For an environment deployment, the selected repository + branch must be the authoritative runtime source.

Deployment must execute scripts from:

```text
<environment>/source/.ai-dev-factory/scripts/
```

Never from:

```text
<host-ai-dev-factory>/.ai-dev-factory/scripts/
```

---

## Required behavior

When deploying:

```text
project = X
branch = Y
environment = Z
```

The system must:

1. clone the selected repo/branch into the environment source directory;
2. use the committed scripts from that clone;
3. run bootstrap/build/start/healthcheck from that cloned project source;
4. use supervisor/daemon/runtime behavior provided by the cloned project when present;
5. avoid hidden fallback to host/global ai-dev-factory runtime files.

---

## Important clarification

Do not regenerate scripts during deploy.

Scripts are generated once, committed to the project branch, and consumed as-is by environment deploy.

---

## Required checks

Before running any script, log the resolved path:

```text
resolved script path: <environment>/source/.ai-dev-factory/scripts/<script>.sh
```

If the resolved path points outside the environment source directory, fail immediately.

---

## Important constraints

Do NOT:

- use host/global ai-dev-factory scripts;
- regenerate scripts during deploy;
- silently fallback to another script path;
- mix runtime scripts from different branches;
- assume the deployed project is ai-dev-factory itself.

---

## Acceptance criteria

- Deploying branch T170 executes T170 committed scripts
- `resolved script path` points under `<environment>/source/.ai-dev-factory/scripts/`
- Host ai-dev-factory scripts are never used for project environment deploy
- Different environments can run different committed runtime scripts concurrently
- If a required script is missing from the selected branch, deploy fails clearly
- Deploying another repository works without ai-dev-factory-specific script path assumptions
