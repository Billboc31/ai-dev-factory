# Required Plan Fix — Project ID Safety and Runtime Isolation

## Problem

The current T181 plan is globally correct, but it needs two mandatory safeguards before implementation:

1. strict `project_id` normalization/validation;
2. explicit per-project runtime isolation diagnostics.

Because `project_id` is used to derive filesystem paths, it must never accept arbitrary user input.

## Required additions to the plan

### 1. Project ID normalization

Add a helper such as:

```text
normalize_project_id(name_or_path) -> project_id
```

Rules:

- lowercase only;
- allowed characters: `a-z`, `0-9`, `-`, `_`;
- reject `/`, `\\`, `.`, `..`, whitespace-only values, empty values;
- collapse unsupported characters to `-` only when auto-generating from a project name;
- for explicit user-provided `project_id`, reject invalid input instead of silently rewriting it;
- enforce a reasonable max length.

### 2. Path containment validation

Before creating runtime directories, validate:

```text
project_runtime_root = {RUNTIME_ROOT}/projects/{project_id}
```

and ensure:

- it is absolute;
- it remains inside `{RUNTIME_ROOT}/projects`;
- it does not escape via symlinks or `..`;
- duplicate project IDs are rejected.

### 3. Runtime isolation logging

Every per-project daemon operation must log:

```text
project_id=<id>
project_root=<repo path>
project_runtime_root=<runtime path>
runs_dir=<...>
logs_dir=<...>
state_dir=<...>
worktrees_dir=<...>
daemon_pid_path=<...>
```

This is required to avoid repeating the previous confusion between global runtime, environment runtime and project runtime.

### 4. Supervisor endpoint validation

The supervisor endpoints:

```text
POST /projects/{id}/daemon/start
GET /projects/{id}/daemon/status
POST /projects/{id}/daemon/stop
```

must validate that the project exists in the workspace registry before starting or stopping any daemon.

They must not accept arbitrary paths from the request body without registry validation.

### 5. Follow-up ticket

Create or mention a follow-up for ticket/worktree collision prevention across projects.

This can stay out of T181 implementation, but the limitation must be documented clearly.

## Acceptance criteria additions

- invalid project IDs are rejected with 4xx;
- project runtime root cannot escape the workspace runtime root;
- importing the same project ID twice returns 4xx;
- per-project daemon logs show all resolved runtime paths;
- supervisor daemon endpoints require a registered project;
- no per-project daemon operation uses the global runtime directories accidentally.