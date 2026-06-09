# T179 — T179 - Environment logs UI must expose full lifecycle logs and runtime diagnostics

**Source**: GitHub Issue #210

## Description

## Problem

The new environment logs UI only shows a short step summary:

- bootstrap
- build
- start
- healthcheck

This hides the most important runtime diagnostics needed to debug deployment/runtime issues.

Recent deploy failures became extremely difficult to debug because the UI no longer exposes:

- runtime_root
- sandbox_root
- source_path
- project_root
- resolved script path
- proxy diagnostics
- runtime mismatch details
- healthcheck output
- deploy lifecycle logs

The deployer heavily relies on runtime/path orchestration, so hiding these logs removes the ability to understand what actually happened.

---

## Goal

Keep the step summary UI, but restore access to the full lifecycle logs.

Users must be able to:

- inspect the full deploy lifecycle
- view runtime diagnostics
- understand runtime/path resolution
- inspect healthcheck failures
- copy/download the raw logs

---

## Required UI behavior

### Keep the current summary

The step summary is useful and should remain.

### Add full logs access

Add:

- "Full logs" tab/button
- expandable runtime diagnostics section
- raw log viewer
- copy logs button
- download logs button

---

## Required diagnostics visibility

The full logs must expose:

```text
runtime_root
sandbox_root
source_path
project_root
resolved script path
runtime_root_source
proxy diagnostics
healthcheck details
```

and all deploy lifecycle events.

---

## Required backend behavior

The backend must preserve:

- full run.log
- stdout/stderr for all steps
- runtime diagnostics logs

The UI must not truncate or discard them.

---

## Acceptance criteria

- Step summary still exists
- Full lifecycle logs are accessible from the UI
- Runtime/path diagnostics are visible again
- Healthcheck failures expose detailed logs
- Users can copy/download logs
- Raw deploy logs are no longer hidden
