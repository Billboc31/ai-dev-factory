## Objective

Make the Global Dependency Analyzer produce an internally consistent dependency graph — foundation tickets are detected, dependency ordering is respected by execution phases, and conflicting tickets are never placed in the same phase — so the Dispatcher can schedule a batch safely. Delivered via a rewritten prompt plus a defensive post-processing/coherence pass around the LLM response.

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
  - Add a `_enforce_coherence(norm_tickets, norm_relationships) -> tuple[list[dict], list[dict], list[str]]` pass invoked after `_normalize_response` and before `_persist`. It fixes the graph deterministically rather than failing:
    - Build a `depends_on` closure and coerce `execution_phase` to integers; if a ticket has no phase or violates `phase(A) > phase(B)`, recompute phases via a topological longest-path pass (phase 1 = tickets with no `depends_on`; each other ticket = 1 + max(phase of deps)). Foundation tickets (those that are only targets of `FOUNDATION_DEPENDENCY` or appear in no `depends_on`) end up in phase 1 naturally.
    - Detect dependency cycles: drop the offending edges (keep the graph acyclic), log a warning, record in the returned notes list.
    - For every unordered pair `(a, b)` where both list each other in `conflicting_tickets` and share the recomputed `execution_phase`, bump the phase of the ticket with the larger `ticket_id` (stable tiebreak) by +1 and cascade downstream phases.
    - Re-serialize `execution_phase` back to string form to match the existing DB schema.
  - Add structured `logger.info` output summarizing coherence adjustments (counts of phase reassignments, cycles broken, conflict-splits) so failures show up in the daemon log.
  - No change to `run_global_analysis` signature, DB schema, or persistence contract.
- `tests/test_global_dependency_analyzer.py`: add tests covering the new coherence pass, using the existing `_configure_stub` pattern:
  - `test_conflicting_pair_gets_split_across_phases`: LLM returns `T001` and `T010` in the same `execution_phase` while listing each other as `conflicting_tickets`; assert persisted phases differ.
  - `test_phase_is_recomputed_when_dependency_ordering_violated`: LLM returns `T011` (depends_on `T010`) with `execution_phase` ≤ `T010`; assert `T011` phase > `T010` phase after persistence.
  - `test_foundation_ticket_lands_in_earliest_phase`: LLM returns a `FOUNDATION_DEPENDENCY` from `T010` → `T001`; assert `T001` ends up in phase 1 and `T010` in phase 2.
  - `test_cycle_is_broken_without_failure`: LLM returns `A depends_on B` and `B depends_on A`; assert `outcome.success is True`, both tickets persisted, no cycle in stored `depends_on` (one direction removed).
  - `test_realistic_test_ai_dev_backlog`: seed a ~6-ticket batch matching the shape of the `test-ai-dev` fixture from the ticket (`T001` vision/architecture, `T002` bootstrap, `T010`/`T011` backend, `T020` frontend, `T030` integration). Stub the LLM with a response representative of the bad case (T001 in phase 1 alongside T010, conflicting pair). Assert: `T001` alone in phase 1, `T010`/`T011` in later phase than `T001`, no conflicting pair shares a phase.
- `runs/T220/`: this plan file. No other artifacts.

## Excluded

- Any change to the Dispatcher, readiness evaluator, execution eligibility, control API, or dashboard components. Consumers keep reading the same `ticket_dependency_analysis` rows.
- Any change to `runtime_db.py`, the SQLite schema, or the Postgres mirror.
- Any change to `backlog_batch.py` (state machine, freezing, retry policy).
- Reworking the AI subprocess invocation, timeouts, retry cooldown, or `AnalysisOutcome` shape.
- Adding new relationship types beyond the existing five.
- Integrating a real `test-ai-dev` repository at runtime — fixtures live inside the test file only.
- Prompt engineering unrelated to foundation detection, implicit dependencies, phases, and conflicts (e.g. reworking intelligence hints, cross-batch reasoning).
- Retroactively rewriting rows for already-analyzed historical batches.

## Acceptance criteria

- `prompts/global-dependency-analyzer-prompt.md` contains explicit sections for foundation detection, implicit dependency archetypes, and the four output invariants (phase ordering, same-phase parallel compatibility, conflict-vs-phase exclusivity, foundation tickets in earliest phases).
- `_INLINE_PROMPT` in `global_dependency_analyzer.py` stays consistent with the file prompt.
- `_enforce_coherence` is invoked inside `run_global_analysis` between `_normalize_response` and `_persist`; the function is unit-testable in isolation.
- For every persisted batch, the DB rows satisfy: if `T_b in T_a.depends_on`, then `int(T_a.execution_phase) > int(T_b.execution_phase)`; no unordered pair `(a, b)` has `b in a.conflicting_tickets` AND `a.execution_phase == b.execution_phase`.
- `pytest tests/test_global_dependency_analyzer.py` passes, including the five new tests listed above; the five pre-existing tests remain green with no signature changes.
- Running the analyzer on the `test-ai-dev`-shaped fixture no longer places `T001` in the same execution phase as `T010` when they are marked as conflicting; a coherence adjustment is logged.
- `run_global_analysis` still never raises and preserves the `AnalysisOutcome(success, error, persisted_ticket_count)` contract.
