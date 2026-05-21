# T123 — T123 — Persistent daemon/runtime status streaming in dashboard

**Source**: GitHub Issue #85

## Description

# Objective

Turn the dashboard into a real-time runtime cockpit by exposing persistent daemon and worker status streaming directly in the UI.

## Included

- Add live daemon ONLINE/OFFLINE status.
- Display active workers and currently running tickets.
- Show retry/cooldown state for tickets.
- Stream runtime logs live in the dashboard.
- Add automatic refresh/polling for runtime state.
- Expose queue/intake state from the control API.
- Display last runtime action and latest daemon error.
- Add backend endpoints/services required for runtime streaming/state aggregation.
- Add frontend components for runtime status visualization.
- Add tests for runtime status endpoints and UI rendering.

## Excluded

- Multi-project orchestration.
- Authentication/permissions.
- Full websocket/event-bus architecture rewrite.
- Mobile redesign.
- Remote daemon execution.

## Acceptance criteria

- Dashboard shows daemon ONLINE/OFFLINE state in near real-time.
- Active workers and running tickets are visible.
- Runtime log stream updates without manual page reload.
- Retry/cooldown state is visible for blocked tickets.
- Queue/intake state is visible from the UI.
- Runtime/API failures are surfaced clearly in the dashboard.
- Existing workflow operations continue to function.
- Runtime garbage files are not committed during runtime status refresh operations.
