# T175 — T175 - Environment creation UI must expose and validate runtime/deployment target

**Source**: GitHub Issue #202

## Description

# T175 - Environment creation UI must expose and validate runtime/deployment target

## Problem

The current environment creation flow hides important runtime/deployment target information.

During recent environment deploy testing:

- scripts were correctly executed from the fresh sandbox clone
- but the runtime/project context remained ambiguous
- the UI never clearly indicated where the environment would actually be deployed
- logs still referenced mixed runtime/project paths

This creates confusion about:

- which runtime is active
- where the sandbox is deployed
- which runtime root owns the environment
- whether deployment uses the fresh runtime or host runtime
- whether multiple runtime roots are conflicting

---

## Current confusing behavior

Example:

```text
source_path=/Users/.../sandboxes/.../source
```

but:

```text
project_root=/Users/.../runtime/ai-dev-factory/clones/ai-dev-factory
```

The deployment technically works, but the runtime ownership and deployment target remain unclear.

---

## Goal

The environment creation popup and deployment flow must:

- clearly expose the deployment/runtime target
- make runtime ownership explicit
- validate runtime consistency before deploy
- eliminate ambiguity between:
  - source clone
  - project root
  - runtime root
  - sandbox root

---

## Required UI changes

The popup must clearly display:

- current project
- repository
- selected branch
- runtime root
- sandbox destination path
- environment name

Example:

```text
Project: ai-dev-factory
Branch: main
Runtime root: /Users/.../sandboxes/ai-dev-factory
Environment path: /Users/.../sandboxes/ai-dev-factory/<sandbox-id>
```

The user must understand exactly where the environment will run.

---

## Required validation

Before deploy:

validate:

- runtime_root is consistent
- source_path belongs to runtime_root
- worktree/sandbox ownership is correct
- deploy scripts come from the sandbox source clone
- project_root and source_path are not silently mixed

If inconsistent:

fail clearly with explicit runtime mismatch diagnostics.

---

## Required logging

Before bootstrap:

```text
runtime_root=<runtime root>
sandbox_root=<sandbox root>
source_path=<source clone>
project_root=<project root>
script_source=<resolved scripts directory>
```

---

## Acceptance criteria

- Environment popup clearly shows deployment target/runtime
- Runtime ownership is understandable from the UI
- Logs clearly distinguish project_root vs source_path vs runtime_root
- Runtime mismatch situations fail explicitly
- Users can verify deploy destination before launching
- Sandbox deploy always uses scripts from sandbox source clone
- No hidden fallback to another runtime root
