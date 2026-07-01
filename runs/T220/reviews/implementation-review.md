The supervisor test failure exists on main and is unrelated to T220. Let me write the review now.

---

# Implementation review — T220

## Summary

The implementation delivers both parts of the plan: (1) a rewritten global-dependency-analyzer prompt that steers the model toward a two-step "conceptual plan → derive graph" reasoning process with explicit invariants, and (2) a deterministic post-processing coherence pass in `tools/agent_runner/global_dependency_analyzer.py` that fixes the graph rather than failing. All 13 tests in `tests/test_global_dependency_analyzer.py` pass, including the realistic `test-ai-dev`-shaped fixture.

## Correctness vs. acceptance criteria

| Acceptance criterion | Status |
|---|---|
| Foundation tickets detected reliably | ✓ `_infer_ticket_role` combines FOUNDATION_DEPENDENCY relationship targeting + text patterns (`architecture|vision|stack|conventions|foundation|global context`) |
| Execution phases respect dependency ordering | ✓ `_compute_phases` implements topological longest-path (`phase(A) = 1 + max(phase of deps)`), verified by `test_phase_is_recomputed_when_dependency_ordering_violated` |
| No conflicting tickets in same phase | ✓ Iterative resolver + `_resolve_conflict_pair` bumps until fixed point; verified by `test_conflicting_pair_gets_split_across_phases` and the realistic backlog test |
| Implicit architectural dependencies inferred | ✓ Prompt-side only (rules 1‑6 in the "Implicit dependencies" section) — matches the plan (Excluded: adding new relationship types) |
| Graph internally consistent for Dispatcher | ✓ `phase(A) > phase(B)` invariant + acyclic `depends_on` are guaranteed |
| Tests updated + realistic project scenario | ✓ 8 new tests including `test_realistic_test_ai_dev_backlog` reproducing the exact `test-ai-dev` bad case |

Priority ladder implemented correctly in `_resolve_conflict_pair` (analyzer.py:474): dependency direction → role ordering → original LLM phase → ticket_id fallback. `test_conflict_ticket_id_fallback_only_when_ties` proves ticket_id is only invoked as last resort.

## Scope compliance

Stays within the plan's declared boundaries: no changes to Dispatcher, `runtime_db.py`, DB schema, or `backlog_batch.py`. `run_global_analysis` signature and `AnalysisOutcome` contract are preserved. Both `_INLINE_PROMPT` and `prompts/global-dependency-analyzer-prompt.md` are updated consistently.

## Observations (non-blocking)

1. **Dead code** in `analyzer.py:554` and `analyzer.py:611`:
   ```python
   original_int_phases = dict(phases)  # snapshot in case we need it later
   ...
   _ = original_int_phases  # Silence unused warning; kept for future debug hooks
   ```
   Speculative "kept for future" state violates the "don't design for hypothetical requirements" principle. Should be removed.

2. **Regex heuristics are broad**: `test` matches inside `attest`/`latest`; `stack` matches "stack trace"; `service` matches inside `microservice`. Only used as tie-break, but could produce surprising role classifications in edge cases. Acceptable given the ladder falls through to other signals.

3. **Observability gap**: coherence `notes` are computed but only returned to `run_global_analysis` where they land in `_coherence_notes` and are dropped. The realistic-backlog test has to re-invoke `_enforce_coherence` directly to inspect resolver steps (test file, lines 646‑651). Not blocking, but the resolver step log line (`analyzer.py:597`) is the primary channel.

## Pre-existing (not related)

`tests/supervisor/test_supervisor.py::test_lifespan_restores_exec_cmd_and_restart_policy` fails on main too — unrelated to T220.

## Verdict

The implementation is coherent with the ticket, faithful to the plan (including the plan-fix on tiebreak ordering), and the invariants that motivated the ticket are enforced deterministically. Dead code and the observability gap are minor and can be addressed later.

IMPLEMENTATION_APPROVED
