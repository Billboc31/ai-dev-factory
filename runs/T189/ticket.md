# T189 — T189 - Project bootstrap must create a dedicated runtime root per project instead of using /runtime

**Source**: GitHub Issue #229

## Description

# Objective

Project import currently reaches the supervisor, but bootstrap fails because the runtime root is resolved as:

```text
/runtime/projects/<project_id>
```

This path does not exist on the host and is often read-only.

The architecture must support one dedicated runtime root per managed project.

---

# Current problem

Importing a project such as:

```text
/Users/pierrebocquet/test-ai-dev
```

causes bootstrap to attempt:

```text
/runtime/projects/test-ai-dev
```

and fails with:

```text
OSError: [Errno 30] Read-only file system: '/runtime'
```

The runtime location model is incorrect.

---

# Target architecture

Each project owns an independent runtime root.

Example:

```text
/Users/pierrebocquet/runtime/
├── ai-dev-factory/
│   ├── clones/
│   ├── worktrees/
│   ├── runs/
│   ├── state/
│   └── logs/
│
└── test-ai-dev/
    ├── clones/
    ├── worktrees/
    ├── runs/
    ├── state/
    └── logs/
```

The AI Dev Factory runtime must not become the parent runtime of every imported project.

---

# Required changes

- Introduce a runtime base root concept.
- Compute project runtime root as:

```text
<runtime_base_root>/<project_id>
```

- Remove hardcoded `/runtime` usage.
- Remove assumptions that all projects live under the AI Dev Factory runtime.
- Bootstrap must create:
  - clones/
  - worktrees/
  - runs/
  - state/
  - logs/

inside the project runtime root.

---

# Supervisor responsibilities

Supervisor determines and creates the runtime root.

Control API must receive the resolved runtime root from supervisor and persist it.

---

# Acceptance criteria

- Importing `/Users/pierrebocquet/test-ai-dev` succeeds.
- Runtime root becomes something like:

```text
/Users/pierrebocquet/runtime/test-ai-dev
```

- No code writes to `/runtime/projects/...`.
- Bootstrap creates all runtime directories.
- AI Dev Factory runtime remains isolated from imported project runtimes.
- Multiple projects can coexist with independent runtimes.
