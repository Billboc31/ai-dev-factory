# T191 — T191 - Fix runtime_base_root initialization causing false workspace escape validation

**Source**: GitHub Issue #233

## Description

# Objective

Fix the failure introduced during T190 work:

```text
project_id 'test-ai-dev' would escape the workspace directory: /test-ai-dev
```

This error is misleading and indicates that runtime base resolution is missing or invalid before containment validation runs.

## Root cause

`assert_contained()` is being called with an invalid base path (empty, None, Path(''), or improperly initialized runtime_base_root).

This produces:

```text
/test-ai-dev
```

instead of:

```text
<runtime_base_root>/test-ai-dev
```

and triggers a false workspace escape error.

## Required fixes

### 1. Validate runtime_base_root before containment checks

Before:

```python
assert_contained(runtime_base_root, project_id)
```

ensure:

- runtime_base_root is not None
- runtime_base_root is not empty
- runtime_base_root resolves correctly

Return a configuration error if missing.

### 2. Improve error reporting

Replace misleading workspace escape errors with:

```text
runtime_base_root is not configured
```

or:

```text
invalid runtime_base_root: <value>
```

when configuration is the actual problem.

### 3. Fix tests

Tests must create a valid runtime root:

```python
runtime_base_root = tmp_path / 'runtime'
```

and verify:

```python
assert_contained(runtime_base_root, 'test-ai-dev')
```

returns:

```python
runtime_base_root / 'test-ai-dev'
```

### 4. Add regression coverage

Cover:

- empty runtime_base_root
- None runtime_base_root
- valid runtime_base_root
- project bootstrap path creation

## Acceptance criteria

- No valid project id produces `/test-ai-dev`.
- Missing runtime configuration returns a configuration error.
- assert_contained always receives a valid base root.
- Full test suite passes after T190 merge.
