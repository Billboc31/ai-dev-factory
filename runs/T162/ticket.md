# T162 — T162 - Repair existing PR conflict reviewer detection and state sync

**Source**: GitHub Issue #175

## Description

# T162 - Repair existing PR conflict reviewer detection and state sync

## Problem

The PR conflict reviewer workflow already exists (T143/T144), but a real GitHub PR conflict was not surfaced correctly in the dashboard/runtime workflow.

Observed behavior:

- auto-merge detects the conflict:

```text
PR #78 has conflicts — skipping
```

- but the ticket does not reliably enter:

```text
CONFLICT_RESOLUTION_NEEDED
```

- the dashboard does not expose the expected Resolve Conflicts action
- the existing conflict resolver flow becomes unusable unless state is manually manipulated

The core issue is likely synchronization/mapping between:

- GitHub PR conflict detection
- runtime ticket state
- conflict metadata persistence
- dashboard visibility

---

# Important

Do NOT redesign or rewrite the PR conflict reviewer system.

The existing architecture from T143/T144 already exists.

This ticket is about repairing the integration and state propagation.

---

# Goal

Ensure that when the existing auto-merge/conflict detector identifies a real GitHub PR conflict:

```text
PR has conflicts
```

the runtime workflow automatically transitions into the existing conflict resolution flow.

---

# Included

## Audit existing T143/T144 implementation

Audit:

- conflict detection flow
- auto-merge skip path
- runtime state propagation
- dashboard conflict visibility
- PR ↔ ticket mapping
- conflict metadata persistence
- Resolve Conflicts button visibility conditions

---

## Fix state propagation

When auto-merge detects:

```text
PR has conflicts
```

ensure the workflow:

- records conflict metadata
- transitions the ticket into:

```text
CONFLICT_RESOLUTION_NEEDED
```

- persists the state correctly
- exposes the existing conflict resolution action in the dashboard

---

## Repair PR ↔ ticket mapping

Audit how the system maps:

- PR
- ticket
- issue
- branch
- runtime state

Ensure renamed issues/branches still resolve correctly.

Examples observed during debugging:

- issue renaming
- branch rename mismatch
- PR exists but runtime state not updated

---

## Improve observability

Add clearer logs when a conflict is detected but state propagation fails.

Examples:

```text
PR conflict detected but no runtime ticket mapping found
```

```text
Failed to transition ticket T155 to CONFLICT_RESOLUTION_NEEDED
```

---

## Dashboard integration

Ensure the existing dashboard logic displays the Resolve Conflicts action whenever:

- a mapped PR is conflicted
- or runtime state is already `CONFLICT_RESOLUTION_NEEDED`

The dashboard should not require manual SQLite edits.

---

# Excluded

- No rewrite of the conflict resolver agent
- No new conflict resolution architecture
- No replacement of T143/T144
- No new merge engine
- No new GitHub synchronization system

---

# Suggested files to audit

- auto-merge flow
- PR polling/sync logic
- runtime state transitions
- conflict metadata persistence
- dashboard conflict rendering
- ticket/branch/PR mapping helpers
- SQLite runtime sync logic

---

# Acceptance criteria

- A real GitHub PR conflict automatically transitions the ticket into `CONFLICT_RESOLUTION_NEEDED`
- Existing Resolve Conflicts UI becomes visible automatically
- No manual SQLite manipulation is required
- Conflict metadata is persisted correctly
- Renamed issues/branches still map correctly
- Logs clearly explain failed mapping/state propagation
- Existing T143/T144 flows continue functioning
