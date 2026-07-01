## Objective

Make the Global Dependency Analyzer produce an internally consistent dependency graph — foundation tickets are detected, dependency ordering is respected by execution phases, and conflicting tickets are never placed in the same phase — so the Dispatcher can schedule a batch safely. Delivered via a rewritten prompt plus a defensive post-processing/coherence pass around the LLM response, where same-phase conflicts are resolved by dependency direction, then architectural role, then original LLM phase intent, and only then ticket ID as a deterministic fallback.

## Included

- `prompts/global-dependency-analyzer-prompt.md`: rewrite to steer the model toward a two-step reasoning process:
  1. Build a conceptual implementation plan for the whole backlog (identify foundation/bootstrap tickets first, then infrastructure, then features, then integration/testing).
  2. Derive `depends_on` / `blocks` / `parallel_group` / `conflicting_tickets` / `execution_phase` and the `relationships` array from that plan.
  Add:
  - A dedicated "Foundation tickets" section listing signals to detect (project vision, architecture, tech stack, conventions, bootstrap/scaffolding).
  - A dedicated "Implicit dependencies" section with the archetype rules from the ticket (architecture → bootstrap, bootstrap → backend/frontend foundations, backend API → frontend, infra → features, features → integration, implementation → testing).
  - Explicit invariants the output MUST satisfy: `phase(A) > phase(B)` when `A depends_on B`; tickets sharing a phase must be parallel-compatible; a pair listed as `conflicting_tickets` must not share `execution_phase`; foundation tickets occupy the earliest phase(s).
  - Instruction to prefer a `FOUNDATION_DEPENDENCY` classification when the target is a detected foundation ticket.
- `tools/agent_runner/global_dependency_analyzer.py`:
  - Update `_INLINE_PROMPT` to mirror the new file prompt (same invariants, condensed).
  - Add a role inference helper `_infer_ticket_role(ticket, relationships) -> str` that returns one of: `FOUNDATION`, `BOOTSTRAP`, `INFRASTRUCTURE`, `BACKEND_API`, `FRONTEND_UI`, `FEATURE`, `INTEGRATION`, `QUALITY_TESTING`, `DOCS_MISC`, `UNKNOWN`. Signals:
    - `FOUNDATION`: ticket is the target of a `FOUNDATION_DEPENDENCY` relationship, or title/body matches `architecture|vision|stack|conventions|foundation|global context`.
    - `BOOTSTRAP`: title/body matches `bootstrap|scaffold|initial setup|project foundation`.
    - `BACKEND_API`: title/body matches `backend|api|endpoint|route|service`.
    - `FRONTEND_UI`: title/body matches `frontend|ui|page|react|dashboard|component`.
    - `QUALITY_TESTING`: title/body matches `test|playwright|regression|coverage|qa`.
    - `INTEGRATION`: title/body matches `integration|wiring|end-to-end|connect`.
    - `INFRASTRUCTURE`: title/body matches `infra|infrastructure|deployment|ci|cd|pipeline`.
    - `DOCS_MISC`: title/body matches `docs|documentation|readme|typo`.
    - Otherwise `FEATURE` when at least one dependency signal exists, else `UNKNOWN`.
    - Matching is case-insensitive on concatenated `title + body` string; ticket-level fields already normalized upstream are used.
  - Add a role precedence tuple:
    ```
    ROLE_ORDER = (
        "FOUNDATION", "BOOTSTRAP", "INFRASTRUCTURE",
        "BACKEND_API", "FRONTEND_UI", "FEATURE",
        "INTEGRATION", "QUALITY_TESTING", "DOCS_MISC", "UNKNOWN",
    )
    ```
    exposed for tests.
  - Add a `_enforce_coherence(norm_tickets, norm_relationships, original_phases) -> tuple[list[dict], list[dict], list[str]]` pass invoked after `_normalize_response` and before `_persist`. `original_phases` is a `dict[str, int]` snapshot of the LLM-reported `execution_phase` per ticket (before recomputation), used later as the tertiary tiebreaker. The pass fixes the graph deterministically rather than failing:
    - Build a `depends_on` closure and coerce `execution_phase` to integers; if a ticket has no phase or violates `phase(A) > phase(B)`, recompute phases via a topological longest-path pass (phase 1 = tickets with no `depends_on`; each other ticket = 1 + max(phase of deps)). Foundation tickets (those that are only targets of `FOUNDATION_DEPENDENCY` or appear in no `depends_on`) end up in phase 1 naturally.
    - Detect dependency cycles: drop the offending edges (keep the graph acyclic), log a warning, record in the returned notes list.
    - For every unordered pair `(a, b)` where both list each other in `conflicting_tickets` and share the recomputed `execution_phase`, resolve via a priority ladder implemented in a helper `_resolve_conflict_pair(a, b, deps_closure, roles, original_phases) -> str` that returns the id of the ticket to bump later:
      1. **Dependency direction** — if `a` transitively depends on `b`, bump `a`; if `b` transitively depends on `a`, bump `b`.
      2. **Role ordering** — otherwise compare `ROLE_ORDER.index(roles[a])` vs `ROLE_ORDER.index(roles[b])`; the ticket whose role appears later in the precedence list is bumped. Ties on role fall through.
      3. **Original LLM phase intent** — if roles are equal, prefer the ordering that minimally changes the LLM's original intent: bump the ticket that had the higher `original_phases[id]`; if still tied, fall through.
      4. **Ticket ID fallback** — as the final deterministic tiebreaker only, bump the ticket with the larger `ticket_id`.
      After selecting the ticket to bump, increment its phase by +1 and cascade downstream phases via the topological pass so `phase(A) > phase(B)` invariants remain intact.
    - Re-serialize `execution_phase` back to string form to match the existing DB schema.
  - Add structured `logger.info` output summarizing coherence adjustments (counts of phase reassignments, cycles broken, conflict-splits, and — for each conflict split — which resolver step fired: `dependency|role|original_phase|ticket_id`) so failures show up in the daemon log.
  - No change to `run_global_analysis` signature, DB schema, or persistence contract.
- `tests/test_global_dependency_analyzer.py`: add tests covering the new coherence pass, using the existing `_configure_stub` pattern:
  - `test_conflicting_pair_gets_split_across_phases`: LLM returns `T001` and `T010` in the same `execution_phase` while listing each other as `conflicting_tickets`; assert persisted phases differ.
  - `test_phase_is_recomputed_when_dependency_ordering_violated`: LLM returns `T011` (depends_on `T010`) with `execution_phase` ≤ `T010`; assert `T011` phase > `T010` phase after persistence.
  - `test_foundation_ticket_lands_in_earliest_phase`: LLM returns a `FOUNDATION_DEPENDENCY` from `T010` → `T001`; assert `T001` ends up in phase 1 and `T010` in phase 2.
  - `test_cycle_is_broken_without_failure`: LLM returns `A depends_on B` and `B depends_on A`; assert `outcome.success is True`, both tickets persisted, no cycle in stored `depends_on` (one direction removed).
  - `test_conflict_foundation_vs_bootstrap_bumps_bootstrap`: two conflicting tickets in the same phase with no direct dependency edge, roles `FOUNDATION` (T001) and `BOOTSTRAP` (T002); assert T002 phase becomes greater than T001 phase and T001 phase stays 1.
  - `test_conflict_backend_vs_frontend_bumps_frontend_when_frontend_consumes_backend`: conflicting `T010` (backend API) and `T020` (frontend page consuming API), same phase; assert T020 lands in a later phase than T010 regardless of numeric ID order.
  - `test_conflict_ticket_id_fallback_only_when_ties`: two conflicting tickets with identical inferred role (`UNKNOWN`), no dependency edge, and identical original LLM phase; assert the ticket with the larger `ticket_id` is bumped, and that swapping the ids swaps the bump direction (proves the fallback is stable and only fires last).
  - `test_realistic_test_ai_dev_backlog`: seed a ~6-ticket batch matching the shape of the `test-ai-dev` fixture from the ticket (`T001` vision/architecture, `T002` bootstrap, `T010`/`T011` backend, `T020` frontend, `T030` integration). Stub the LLM with a response representative of the bad case (T001 in phase 1 alongside T010, conflicting pair). Assert: `T001` alone in phase 1, `T010`/`T011` in later phase than `T001`, no conflicting pair shares a phase, and the T001↔T010 split was recorded as resolved by the `role` step (not `ticket_id`).
- `runs/T220/`: this plan file. No other artifacts.

## Excluded

- Any change to the Dispatcher, readiness evaluator, execution eligibility, control API, or dashboard components. Consumers keep reading the same `ticket_dependency_analysis` rows.
- Any change to `runtime_db.py`, the SQLite schema, or the Postgres mirror.
- Any change to `backlog_batch.py` (state machine, freezing, retry policy).
- Reworking the AI subprocess invocation, timeouts, retry cooldown, or `AnalysisOutcome` shape.
- Adding new relationship types beyond the existing five.
- Persisting the inferred role on the DB row — it is derived on the fly inside the coherence pass only.
- Integrating a real `test-ai-dev` repository at runtime — fixtures live inside the test file only.
- Prompt engineering unrelated to foundation detection, implicit dependencies, phases, and conflicts (e.g. reworking intelligence hints, cross-batch reasoning).
- Retroactively rewriting rows for already-analyzed historical batches.

## Acceptance criteria

- `prompts/global-dependency-analyzer-prompt.md` contains explicit sections for foundation detection, implicit dependency archetypes, and the four output invariants (phase ordering, same-phase parallel compatibility, conflict-vs-phase exclusivity, foundation tickets in earliest phases).
- `_INLINE_PROMPT` in `global_dependency_analyzer.py` stays consistent with the file prompt.
- `_enforce_coherence` is invoked inside `run_global_analysis` between `_normalize_response` and `_persist`; the function is unit-testable in isolation.
- For every persisted batch, the DB rows satisfy: if `T_b in T_a.depends_on`, then `int(T_a.execution_phase) > int(T_b.execution_phase)`; no unordered pair `(a, b)` has `b in a.conflicting_tickets` AND `a.execution_phase == b.execution_phase`.
- Same-phase conflict resolution never uses `ticket_id` as the primary ordering signal — the resolver applies dependency direction, then role ordering, then original LLM phase intent before falling back to `ticket_id`.
- Foundation/bootstrap role ordering is respected when splitting conflicts: a `FOUNDATION` ticket in a same-phase conflict with a `BOOTSTRAP` ticket keeps the earlier phase; a `BACKEND_API` ticket keeps the earlier phase relative to a conflicting `FRONTEND_UI` ticket.
- `ticket_id` ordering is only used as a final stable fallback, and this is verified by a dedicated test that swaps IDs and confirms the bump direction swaps accordingly.
- `pytest tests/test_global_dependency_analyzer.py` passes, including the new tests listed above; the pre-existing tests remain green with no signature changes.
- Running the analyzer on the `test-ai-dev`-shaped fixture no longer places `T001` in the same execution phase as `T010` when they are marked as conflicting; a coherence adjustment is logged with the resolver step that fired.
- `run_global_analysis` still never raises and preserves the `AnalysisOutcome(success, error, persisted_ticket_count)` contract.
