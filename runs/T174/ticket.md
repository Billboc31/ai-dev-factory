# T174 — T174 - Redesign environment creation popup with project-context defaults and autocomplete

**Source**: GitHub Issue #200

## Description

# T174 - Redesign environment creation popup with project-context defaults and autocomplete

## Problem

The current environment creation popup asks for project/app root information even when the user is already inside a project context.

This creates confusion and causes frequent deployment/runtime issues:

- wrong repository selected
- wrong project root
- wrong runtime clone
- app not found errors
- deploy started from the wrong cwd/runtime
- duplicate runtime confusion

The current UX is too low-level and exposes implementation details (`project root`) that should not be user-facing.

---

## Goal

Redesign the environment creation popup to be project-context aware.

When creating an environment from inside a project page/context:

- automatically reuse the current project metadata
- remove the manual `project root` field
- provide autocomplete/selectors for branch/environment inputs
- simplify the flow to make environment creation feel lightweight and safe

---

## Required UX behavior

### From a project context

If the user is currently inside a project:

- automatically use the current project/repository
- do NOT ask for project root
- do NOT ask for repository path
- do NOT ask for application root

The popup should focus only on:

- environment name
- branch/ref
- optional runtime settings

---

## Autocomplete requirements

### Branch autocomplete

The branch selector should:

- autocomplete from local + remote git branches
- support typing/filtering
- prioritize:
  - current branch
  - recent branches
  - `ticket/TXXX-*`

### Environment name suggestions

Suggest names such as:

- `main`
- current ticket id
- sanitized branch name
- recent environment names

---

## Runtime/project validation

Before environment creation:

log:

```text
project_id=<resolved project>
repo_url=<resolved repository>
branch=<selected branch>
environment=<env name>
runtime_root=<resolved runtime root>
```

If project metadata cannot be resolved from context:

fail clearly with:

```text
project context missing
```

not:

```text
app not found
```

---

## Important constraints

Do NOT:

- expose filesystem paths in the UI
- ask users for project root manually
- derive repository from current shell cwd
- silently fallback to another repository
- allow runtime/project mismatch

---

## Acceptance criteria

- Creating an environment from a project page does not ask for project root
- Current project metadata is reused automatically
- Branch field supports autocomplete/filtering
- Environment name supports suggestions/autocomplete
- Deploy logs clearly show resolved project/repository/runtime metadata
- Wrong local cwd cannot affect environment creation
- Environment creation flow is simpler and project-centric
