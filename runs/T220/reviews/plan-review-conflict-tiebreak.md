# Plan review — conflict phase split tiebreak

The T220 plan is strong overall.

The prompt rewrite plus `_enforce_coherence()` post-processing is the right direction. It makes the Global Dependency Analyzer more robust by enforcing important invariants before the Dispatcher consumes the graph:

```text
- dependencies must be ordered by phase
- cycles must be removed
- conflicting tickets cannot stay in the same execution phase
- foundation tickets should be placed early
```

However, the proposed conflict-splitting heuristic is too weak:

```text
For every conflicting pair in the same phase, bump the ticket with the larger ticket_id.
```

## Why this is a problem

Ticket IDs are not architectural ordering signals.

They often correlate with creation time, but not necessarily with implementation priority or dependency direction.

Examples:

```text
T001  Architecture
T010  Bootstrap
```

Here ticket ID ordering happens to work.

But later cases may not:

```text
T150  Refactor auth foundation
T151  Add login page
```

or:

```text
T500  Introduce event bus
T499  Fix README
```

A numeric ticket ID should only be a final deterministic tie-breaker, not the primary decision rule.

## Required change

Replace the conflict split rule with a priority-based resolver.

Preferred order:

```text
1. Existing dependency direction
2. Ticket role / architectural category
3. Execution phase intent from LLM
4. Ticket ID as final deterministic tie-breaker only
```

Suggested role ordering:

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
```

If two conflicting tickets are in the same phase:

```text
- If A depends on B directly or indirectly, move A later.
- Else if B depends on A directly or indirectly, move B later.
- Else if role(A) should precede role(B), move B later.
- Else if role(B) should precede role(A), move A later.
- Else use ticket_id as the final stable tie-breaker.
```

## Verdict

PLAN_FIX_REQUIRED until the same-phase conflict resolver stops using `larger ticket_id` as the primary ordering rule.
