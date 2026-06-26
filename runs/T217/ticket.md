# T217 — Fallback to legacy daemon scheduling when Dispatcher is disabled

**Source**: GitHub Issue #290

## Description

## Problem

When the Dispatcher feature is disabled, the daemon currently waits for Dispatcher decisions and no tickets are automatically started.

This prevents users from running AI Dev Factory in legacy autonomous mode.

## Goal

Restore the historical behavior:

```text
Dispatcher enabled
→ Dispatcher selects eligible tickets
→ Daemon executes Dispatcher decisions

Dispatcher disabled
→ Daemon directly selects and starts eligible tickets
```

## Expected behavior

The daemon startup loop should detect whether the Dispatcher is enabled.

Pseudo-code:

```text
if dispatcher_enabled:
    use dispatcher queue and decisions
else:
    use legacy daemon scheduling logic
```

## Scope

- Detect Dispatcher enable/disable status.
- Restore legacy ticket acquisition path when Dispatcher is disabled.
- Ensure existing readiness/intelligence checks continue to work as before.
- Ensure workers can still process tickets without Dispatcher.
- Preserve current Dispatcher behavior when enabled.

## Acceptance criteria

- With Dispatcher enabled, behavior is unchanged.
- With Dispatcher disabled, tickets are automatically picked and executed.
- Existing autonomous workflows continue to function.
- No manual intervention is required to start tickets when Dispatcher is disabled.
- Tests cover both Dispatcher enabled and disabled modes.
- Logs clearly indicate which scheduling strategy is active.

## Notes

This ticket preserves backward compatibility and allows users to progressively adopt Dispatcher-based orchestration.
