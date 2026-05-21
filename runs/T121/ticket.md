# T121 — T121 — Reconnect dashboard controls to canonical runtime daemon

**Source**: GitHub Issue #80

## Description

# Objective

Reconnect the dashboard UI controls to the real runtime daemon and canonical runtime root so the web UI becomes the primary runtime control cockpit.

## Included

- Reconnect dashboard actions to the real daemon/runtime used in `~/runtime/ai-dev-factory`.
- Display real daemon status in the dashboard.
- Restore working UI actions for:
  - start daemon
  - stop daemon
  - retry ticket
  - approve plan
  - abort/archive ticket
  - refresh runtime state
- Ensure dashboard actions target the canonical runtime root and not stale local/demo state.
- Expose enough runtime status through the control API for the dashboard to reflect:
  - daemon running/stopped
  - active workers
  - active tickets
  - retry/blocking state
- Ensure live logs come from the active runtime worktrees.
- Add a safe "Pull main" / sync-main action if not already functional.
- Add clear error reporting in the UI when runtime actions fail.

## Excluded

- Multi-project orchestration.
- Guardian regression agent.
- Major dashboard redesign.
- Full mobile responsiveness overhaul.
- Runtime architecture rewrite.
- Replacing Git-based workflow persistence.

## Acceptance criteria

- Dashboard buttons interact with the real daemon/runtime.
- Starting/stopping the daemon from the UI works reliably.
- Approve/retry actions update the actual runtime state.
- Live runtime logs reflect real worker execution.
- Runtime status displayed in the dashboard matches the actual daemon state.
- The dashboard can be used as the primary runtime control surface without requiring terminal commands for normal workflow operations.
- No runtime logs, pycache files, locks, or local runtime garbage are committed during UI-triggered actions.
