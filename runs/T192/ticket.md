# T192 — T192 - Fix runtime_base_root resolving to filesystem root '/' causing false workspace escape errors

**Source**: GitHub Issue #235

## Description

# Objective

T191 did not fix the actual failure.

The error remains:

```text
project_id 'test-ai-dev' would escape the workspace directory: /test-ai-dev
```

This strongly suggests that `runtime_base_root` is resolving to:

```text
/
```

rather than being None or Path('').

## Root cause hypothesis

Current guards only cover:

- None
- Path('')
- Path('.')

But the real caller is likely producing:

```python
Path('/')
```

which leads to:

```python
Path('/') / 'test-ai-dev'
```

and therefore:

```text
/test-ai-dev
```

triggering the workspace escape error.

## Required investigation

Identify exactly where `runtime_base_root` is resolved.

Trace:

- project import flow
- bootstrap flow
- runtime resolver
- supervisor bootstrap endpoint
- project registry loading

Add temporary diagnostics if necessary.

## Required fix

### 1. Detect invalid filesystem-root runtime base

If:

```python
runtime_base_root == Path('/')
```

and that value was not explicitly configured by the user,
raise a configuration error.

### 2. Fix the caller

The preferred solution is not another guard.

Find why runtime base resolution falls back to `/` and correct the source.

### 3. Add regression coverage

Tests for:

- None
- Path('')
- Path('.')
- Path('/')
- valid runtime base root

## Acceptance criteria

- Importing `test-ai-dev` never produces `/test-ai-dev`.
- Runtime base resolution is correctly initialized.
- Path('/') is either rejected or only allowed when explicitly configured.
- Full test suite passes.
- Import/bootstrap flow succeeds with the intended runtime root.
