# T190 — T190 - Fix supervisor runtime base resolution for project bootstrap

**Source**: GitHub Issue #230

## Description

# Objective

T189 is still failing because the running supervisor continues to bootstrap imported projects under an absolute container-style path:

```text
/runtime/projects/<project_id>/...
```

This is wrong for the local host runtime model.

The supervisor must resolve the runtime base explicitly and must never fall back to `/runtime/projects/...` silently.

---

# Current failure

When importing:

```text
/Users/pierrebocquet/test-ai-dev
```

Supervisor receives:

```text
POST /projects/validate-path -> 200 OK
POST /projects/bootstrap -> 500
```

and tries to create:

```text
/runtime/projects/test-ai-dev/runs
```

which fails with:

```text
OSError: [Errno 30] Read-only file system: '/runtime'
```

This proves that path validation now goes through supervisor, but runtime root resolution is still incorrect.

---

# Expected runtime model

The runtime base root is the parent folder containing one runtime per managed project.

Example:

```text
/Users/pierrebocquet/runtime/
├── ai-dev-factory/
│   ├── clones/ai-dev-factory
│   ├── worktrees/
│   ├── runs/
│   ├── state/
│   └── logs/
│
└── test-ai-dev/
    ├── clones/test-ai-dev
    ├── worktrees/
    ├── runs/
    ├── state/
    └── logs/
```

So for project id `test-ai-dev`, bootstrap must create:

```text
/Users/pierrebocquet/runtime/test-ai-dev/{clones,worktrees,runs,state,logs}
```

not:

```text
/runtime/projects/test-ai-dev/...
```

and not:

```text
/Users/pierrebocquet/runtime/ai-dev-factory/projects/test-ai-dev/...
```

---

# Required fix

## 1. Introduce explicit runtime base root resolution

Supervisor must resolve runtime base root in this order:

1. `RUNTIME_BASE_ROOT`
2. parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. safe local fallback such as `~/runtime`

It must not default to `/runtime` unless explicitly configured.

## 2. Bootstrap under runtime base root

Project runtime root must be:

```text
<RUNTIME_BASE_ROOT>/<project_id>
```

Bootstrap creates:

```text
clones/
worktrees/
runs/
state/
logs/
```

inside that root.

## 3. Fail loudly on unsafe root

If the resolved runtime base root is `/runtime` and it is not writable, return a structured 400/422 error instead of crashing with 500.

## 4. Add diagnostics

Supervisor bootstrap logs must include:

```text
runtime_base_root=<...>
project_runtime_root=<...>
project_id=<...>
project_root=<...>
```

This must make path mistakes obvious.

---

# Acceptance criteria

- Importing `/Users/pierrebocquet/test-ai-dev` does not attempt to create anything under `/runtime/projects`.
- Runtime dirs are created under `/Users/pierrebocquet/runtime/test-ai-dev/` when `RUNTIME_BASE_ROOT=/Users/pierrebocquet/runtime`.
- Supervisor returns a structured error if runtime base root is missing or not writable.
- No unhandled `OSError: Read-only file system: '/runtime'` reaches the user.
- Logs clearly show the resolved runtime base root and project runtime root.
- Existing `ai-dev-factory` runtime remains at `/Users/pierrebocquet/runtime/ai-dev-factory`.
