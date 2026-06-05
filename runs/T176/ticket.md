# T176 — T176 - Redeploy must rehydrate missing sandbox source clone and support advanced runtime path override

**Source**: GitHub Issue #204

## Description

# T176 - Redeploy must rehydrate missing sandbox source clone and support advanced runtime path override

## Problem

Environment redeploy currently fails when the sandbox source clone is missing or incomplete.

Observed failure:

```text
runtime mismatch: scripts directory not found at
/Users/.../sandboxes/.../source/.ai-dev-factory/scripts
— sandbox source clone missing or not initialized
```

This means redeploy assumes the `source/` clone already exists and is fully initialized.

However:

- stopped environments may lose their source clone
- partial/incomplete bootstrap can leave a broken source state
- runtime cleanup may remove source data
- redeploy should be resilient and self-healing

---

## Root cause

Current redeploy flow:

```text
resolve scripts path
→ expect source/.ai-dev-factory/scripts to exist
→ fail hard if missing
```

Expected behavior:

```text
redeploy
→ verify source clone exists
→ if missing/incomplete:
   - recreate sandbox source clone
   - checkout correct branch/ref
   - restore scripts
→ continue bootstrap
```

---

## Goal

Make redeploy self-healing and resilient.

If the sandbox source clone is missing or invalid:

- automatically recreate it
- restore the correct branch/ref
- continue deployment

Additionally:

- expose advanced runtime path override options in the environment creation UI
- while keeping auto-configuration as the default

---

## Required backend behavior

### Redeploy validation

Before resolving script paths:

validate:

- `sandbox_dir/source` exists
- `.git` exists
- `.ai-dev-factory/scripts` exists
- branch/ref is available

If invalid:

- log explicit diagnostics
- recreate source clone automatically
- checkout requested branch/ref
- continue deployment

---

## Required logging

On redeploy:

```text
source clone missing or invalid
rehydrating sandbox source clone
repo=<repo>
branch=<branch>
source_path=<path>
```

After restore:

```text
sandbox source clone restored successfully
```

---

## UI changes

Keep runtime path auto-configuration by default.

Add an optional advanced section:

```text
[ Advanced runtime options ]
```

Allow overriding:

- sandbox root
- runtime root
- source path

Also allow:

- force source clone refresh
- reset/reclone source

---

## Important constraints

Default/simple flow must remain automatic.

Advanced runtime controls:

- hidden by default
- intended for debugging/recovery
- must validate path ownership and consistency

---

## Acceptance criteria

- Redeploy no longer fails when `source/.ai-dev-factory/scripts` is missing
- Missing source clone is automatically recreated
- Correct branch/ref is restored automatically
- Logs clearly indicate clone rehydration
- Advanced runtime options are available but collapsed by default
- Users can force source refresh/reclone
- Runtime validation still prevents cross-runtime path mismatches
