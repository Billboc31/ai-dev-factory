# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Planner

## Mission

Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.

## Tu dois

- comprendre le ticket
- proposer les étapes minimales
- lister les fichiers à créer ou modifier
- identifier les risques
- expliciter le hors scope
- produire un plan Markdown versionnable
- signaler les hypothèses nécessaires

## Tu ne dois pas

- coder
- réécrire le ticket
- anticiper les tickets suivants
- élargir le scope
- masquer les incertitudes

## Sortie attendue

Un fichier de plan conforme à `ai/templates/plan-template.md`.

## Règles

- le plan doit rester court
- le plan doit être exécutable par un Coder sans ambiguïté
- toute hypothèse doit être explicite
- toute dérive de scope doit être refusée

## Structure obligatoire

Tout plan doit contenir au minimum **les sections suivantes** (titres
Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :

| Français (recommandé)         | English equivalent       |
|-------------------------------|--------------------------|
| `## Contexte`                 | `## Context`             |
| `## Objectif`                 | `## Objective`           |
| `## Inclus`                   | `## Included`            |
| `## Hors scope`               | `## Excluded`            |
| `## Critères d'acceptation`   | `## Acceptance criteria` |

Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.

Ces titres sont obligatoires même si une section est courte : un ticket
trivial peut produire un plan court, mais la structure doit rester stable.

Ne jamais produire uniquement un résumé.
Ne jamais produire un compte rendu d’implémentation.

## Interdictions absolues

Tu ne dois jamais écrire :
- "implémentation terminée"
- "syntaxe valide"
- "changements appliqués"
- "voici ce qui a été fait"

Tu dois produire uniquement un plan futur, pas un compte rendu passé.

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: architecture-discipline

# Skill — Architecture Discipline

## Objectif

Préserver la cohérence architecture du projet dans le temps.

## Règles

- respecter les invariants documentés
- éviter les couplages implicites
- éviter les dépendances inutiles
- éviter les refactors transversaux non demandés
- documenter toute nouvelle règle structurante
- privilégier les changements locaux et bornés

## Refuser si

- le scope dérive
- plusieurs couches sont modifiées sans justification
- des conventions existantes sont cassées
- la mémoire projet devient incohérente

---

# SKILL: documentation

# Skill — Documentation

## Objectif

Maintenir une documentation utile, concise et alignée avec le code réel.

## Règles

- documenter les décisions importantes
- éviter les documentations vagues
- garder la mémoire projet cohérente
- expliciter les invariants architecture
- préférer Markdown simple et versionnable

## Refuser si

- la documentation diverge du comportement réel
- la mémoire contient des suppositions non validées
- des décisions importantes ne sont pas tracées

---

# TASK

The ticket follows.
# Generic Planner Task Read the ticket below and produce a detailed implementation plan.

## Artifact-only output (strict)

Your response will be written verbatim to `runs/<ticket>/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.

This rule applies to both initial plans and rewrites after a review.
Examples of forbidden openings: "The plan has been rewritten…",
"This plan now covers…", "Plan rewritten as a real implementation
document…", "Key points covered…", "The document now contains…".

## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
## Objective
## Included
## Excluded
## Acceptance criteria
These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
markdown
## Objective
Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
naming convention. Behaviour is preserved.

## Included
- `utils.py`: rename `foo` → `bar`, update the docstring.
- `tests/test_utils.py`: update the single import and assertion.

## Excluded
- Renaming callers in other modules (tracked in a follow-up ticket).
- Any logic change inside `foo` / `bar`.

## Acceptance criteria
- `utils.py` no longer defines `foo`.
- `pytest tests/test_utils.py` passes.
- No other file references the old name.

The ticket follows.



# T220 — Improve Global Dependency Analyzer to produce coherent execution phases and foundation ordering

**Source**: GitHub Issue #297

## Description

# Context

The Global Dependency Analyzer is now responsible for building a dependency graph for a backlog batch.

During testing on the `test-ai-dev` repository, the analyzer produced an inconsistent graph:

- T001 (project vision / architecture) was placed in the same execution phase as T010.
- At the same time, the analyzer reported `T001 conflicts with T010`.

Those two statements cannot both be true.

The analyzer must produce a coherent dependency graph that can be consumed safely by the Dispatcher.

# Goal

Improve the Global Dependency Analyzer prompt, reasoning process, and output consistency.

The objective is to generate a dependency graph that reflects how an experienced software architect would plan implementation work.

# Improvements

## 1. Detect foundation tickets

Detect tickets whose purpose is to:

- define product vision
- define architecture
- define technical stack
- define conventions
- bootstrap the project

Classify them as foundation/bootstrap tickets.

These tickets should naturally appear before implementation tickets.

## 2. Improve dependency inference

Infer implicit dependencies such as:

- architecture → bootstrap
- bootstrap → backend/frontend foundations
- backend API → frontend consuming the API
- infrastructure → features
- features → integration
- implementation → testing

The analyzer should propose dependencies even when they are not explicitly written in GitHub.

## 3. Produce coherent execution phases

Execution phases represent tickets that may safely execute in parallel.

Rules:

- if A depends on B then phase(A) > phase(B)
- tickets in the same phase must be parallel compatible
- foundation tickets should normally occupy the earliest phases

## 4. Resolve conflicts consistently

If two tickets are marked as conflicting:

- they must not be placed in the same execution phase
- or the analyzer must remove the conflict if they are actually parallel compatible

The output must never simultaneously state:

- same execution phase
- conflicting tickets

for the same ticket pair.

## 5. Strengthen prompting

Update the analyzer prompt to reason globally over the entire backlog before assigning:

- dependencies
- conflicts
- execution phases
- parallel groups

The model should first build a conceptual implementation plan, then derive the graph.

# Acceptance criteria

- Foundation tickets are detected reliably.
- Execution phases respect dependency ordering.
- No conflicting tickets appear in the same parallel phase.
- Implicit architectural dependencies are inferred when appropriate.
- The dependency graph is internally consistent and suitable for Dispatcher scheduling.
- Existing dependency analysis tests are updated and extended with realistic project scenarios (including the `test-ai-dev` backlog).

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T220/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

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

---

## Review

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

---

## Instructions de fix

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