# Plan fix — replace ticket-id conflict tiebreak with role-aware ordering

Update `runs/T220/plan.md` before implementation.

The plan currently says that if two conflicting tickets share the same execution phase, the coherence pass should:

```text
bump the phase of the ticket with the larger ticket_id
```

This must be changed.

## Required behavior

The conflict resolver must be deterministic, but it should not primarily rely on ticket ID order.

Ticket ID order is only allowed as the final fallback.

## Proposed resolver

When two tickets `A` and `B` are listed as conflicting and share the same `execution_phase`, resolve as follows:

```text
1. Dependency direction

If A depends on B directly or indirectly:
  move A to a later phase

If B depends on A directly or indirectly:
  move B to a later phase

2. Role ordering

If no dependency path exists, compare the inferred role/category of each ticket.

Earlier roles should stay earlier.
Later roles should move later.

3. LLM phase intent

If the normalized LLM output had a useful original phase hint before recomputation, prefer the ordering that minimally changes the original plan while preserving invariants.

4. Ticket ID fallback

Only if all previous checks are tied, move the ticket with the larger ticket_id.
```

## Role ordering

Introduce an internal role ranking helper.

Suggested roles:

```text
FOUNDATION
BOOTSTRAP
INFRASTRUCTURE
BACKEND_API
FRONTEND_UI
FEATURE
INTEGRATION
QUALITY_TESTING
DOCS_MISC
UNKNOWN
```

Suggested precedence:

```text
FOUNDATION < BOOTSTRAP < INFRASTRUCTURE < BACKEND_API < FRONTEND_UI < FEATURE < INTEGRATION < QUALITY_TESTING < DOCS_MISC < UNKNOWN
```

## Role inference

Role can be inferred from available analyzer data.

Signals:

```text
FOUNDATION:
- relationship type FOUNDATION_DEPENDENCY targets this ticket
- title/body contains architecture, vision, stack, conventions, foundation, global context

BOOTSTRAP:
- title/body contains bootstrap, scaffold, initial setup, project foundation

BACKEND_API:
- title/body contains backend, API, endpoint, route, service

FRONTEND_UI:
- title/body contains frontend, UI, page, React, dashboard, component

QUALITY_TESTING:
- title/body contains test, Playwright, regression, coverage, QA

INTEGRATION:
- title/body contains integration, wiring, end-to-end, connect
```

If role cannot be inferred, use `UNKNOWN`.

## Plan edits required

Replace the current line:

```text
bump the phase of the ticket with the larger ticket_id
```

with:

```text
split same-phase conflicts using dependency direction first, then role ordering, then original LLM phase intent, and only then ticket_id as deterministic fallback.
```

Add tests:

```text
- conflict between FOUNDATION and BOOTSTRAP in same phase moves BOOTSTRAP later
- conflict between BACKEND_API and FRONTEND_UI moves FRONTEND_UI later when frontend consumes backend
- ticket_id fallback is used only when roles and dependencies are tied
```

## Acceptance criteria update

Add:

```text
- Same-phase conflict resolution never uses ticket_id as the primary ordering signal.
- Foundation/bootstrap role ordering is respected when splitting conflicts.
- Ticket ID ordering is only used as a final stable fallback.
```
