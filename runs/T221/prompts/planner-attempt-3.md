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



# T221 — Make GitHub issue intake near real-time and decouple polling from ticket processing

**Source**: GitHub Issue #299

## Description

# Context

For demos, the current GitHub issue intake feels too slow.

At the moment, the daemon effectively intakes about one ticket every 30 seconds. With a backlog of 10 tickets, this can take several minutes before the system even starts showing useful activity.

This hurts the demo experience and makes AI Dev Factory feel less reactive than it should.

# Problem

GitHub polling, issue intake, and ticket pipeline processing are too tightly coupled.

The polling interval should not limit the throughput of ticket intake.

# Goal

Make issue discovery and intake feel near real-time.

When multiple new GitHub issues are created, the daemon should detect and enqueue/intake them quickly, instead of processing one issue per full daemon cycle.

# Desired behavior

```text
GitHub poll runs every X seconds
↓
finds all new eligible issues
↓
intakes all new tickets quickly
↓
Ticket Intelligence workers process them independently
```

For demo mode, creating 10 issues should result in all 10 appearing in AI Dev Factory within a few seconds, not several minutes.

# Proposed changes

## 1. Decouple GitHub polling from ticket processing

Separate these concepts:

```text
GitHub polling interval
Ticket intake throughput
Ticket Intelligence concurrency
Readiness concurrency
Dispatcher execution concurrency
```

The GitHub poller should discover all new eligible issues in one pass.

It should not artificially limit intake to one ticket per daemon cycle unless explicitly configured.

## 2. Intake all discovered issues in a batch

When GitHub polling returns multiple eligible issues:

```text
T001
T002
T003
T004
T005
```

all should be registered/intaken quickly.

The pipeline can then schedule intelligence/readiness independently.

## 3. Add configurable settings

Add runtime settings / env overrides for:

```text
GITHUB_POLL_INTERVAL_SECONDS
MAX_ISSUES_INTAKED_PER_POLL
MAX_PARALLEL_TICKET_INTELLIGENCE
MAX_PARALLEL_READINESS
```

Suggested demo-friendly defaults:

```text
GITHUB_POLL_INTERVAL_SECONDS = 5
MAX_ISSUES_INTAKED_PER_POLL = 50
MAX_PARALLEL_TICKET_INTELLIGENCE = 4
MAX_PARALLEL_READINESS = 4
```

Production defaults may remain more conservative if needed.

## 4. Keep execution concurrency separate

This ticket should not make the daemon launch more coding workers than configured.

Intake and intelligence can be fast/parallel, but actual ticket execution remains controlled by Dispatcher/daemon worker limits.

# Acceptance criteria

- GitHub polling can discover and intake multiple issues in a single poll cycle.
- Intake no longer processes only one issue per daemon cycle unless explicitly configured.
- Poll interval is configurable independently from pipeline execution.
- Ticket Intelligence concurrency is configurable independently from GitHub polling.
- Readiness concurrency is configurable independently from GitHub polling.
- Creating 10 eligible issues results in all 10 being registered/intaken within one or two poll cycles.
- Existing daemon execution concurrency limits remain unchanged.
- Logs clearly show how many issues were discovered and intaken per poll.
- Tests cover multiple issues discovered in one poll and verify all are queued/intaken without waiting for 30-second sequential cycles.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T221/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

Plan written to `runs/T221/plan.md` with the four mandatory headings (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`). It targets the two `break` statements in `poll_github_issues` (run_daemon.py:1432 & 1501), wires `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` into the sleep, registers three new settings (`MAX_ISSUES_INTAKED_PER_POLL`, `MAX_PARALLEL_TICKET_INTELLIGENCE`, `MAX_PARALLEL_READINESS`), parallelises `poll_ticket_pipeline` via two bounded thread pools, and leaves `MAX_WORKERS` / execution scheduling untouched.

---

## Review

# Plan review — concurrency guards for near real-time intake

The T221 plan is directionally correct.

It targets the right bottleneck:

```text
GitHub polling / intake should not be limited to one ticket per daemon cycle.
```

It also correctly keeps execution scheduling separate from intake throughput:

```text
fast intake + parallel intelligence/readiness
!= more coding workers
```

However, the plan should explicitly cover concurrency safety before implementation.

## Concern

Parallelizing Ticket Intelligence and Readiness introduces a common race condition:

```text
worker A sees ticket T001 eligible
worker B sees ticket T001 eligible
both workers start processing T001
```

The plan currently mentions bounded thread pools, but it does not explicitly require atomic claim transitions.

## Required additions

The plan should add explicit concurrency guards:

```text
- atomic claim transitions before worker execution
- no duplicate Intelligence processing for the same ticket
- no duplicate Readiness processing for the same ticket
- tests with many tickets discovered at once
- logs showing discovered / intaken / skipped counts per poll
```

## Expected behavior

For each pipeline stage:

```text
eligible ticket
↓
atomic claim
↓
worker runs stage
```

Example:

```text
NEW / INTELLIGENCE_PENDING
→ INTELLIGENCE_RUNNING
```

must happen atomically before the worker starts.

If another worker tries to claim the same ticket, it should get zero rows updated / no-op and skip it.

## Review verdict

PLAN_FIX_REQUIRED until atomic claim semantics and concurrency tests are explicitly added to the plan.

---

## Instructions de fix

# Plan fix — add atomic claim guards and concurrency tests

Update `runs/T221/plan.md` before implementation.

The plan already targets the right performance issue, but it must explicitly define how parallel processing stays safe.

## Required change 1 — atomic claim transitions

Before a worker starts Ticket Intelligence or Readiness, it must atomically claim the ticket.

The claim operation must be conditional on the current stage/status.

Example shape:

```sql
UPDATE ticket_pipeline
SET intelligence_status = 'running', intelligence_started_at = CURRENT_TIMESTAMP
WHERE ticket_id = ?
  AND intelligence_status IN ('pending', 'retry_pending')
```

The worker may proceed only if exactly one row was updated.

If zero rows are updated, another worker already claimed the ticket and this worker must skip.

Equivalent logic using existing runtime DB helpers is fine, but the semantics must be atomic.

## Required change 2 — no duplicate processing

The implementation must guarantee:

```text
- one Intelligence run per ticket at a time
- one Readiness run per ticket at a time
- no double intake for the same GitHub issue
- idempotent handling if GitHub returns the same issue across multiple polls
```

Use existing uniqueness constraints where possible.

If uniqueness is missing, add guarded checks or a small helper that safely records intake once.

## Required change 3 — bounded parallelism

The new settings should bound concurrency:

```text
MAX_PARALLEL_TICKET_INTELLIGENCE
MAX_PARALLEL_READINESS
```

The implementation must never start more active workers than configured.

If a configured value is invalid or <= 0, fall back to a safe default such as 1.

## Required change 4 — intake batch logs

Each GitHub poll should log a compact summary:

```text
github poll: discovered=20 intaked=20 skipped_existing=0 skipped_limit=0
```

When `MAX_ISSUES_INTAKED_PER_POLL` is reached, logs should make that obvious:

```text
github poll: discovered=80 intaked=50 skipped_limit=30
```

## Required tests

Add tests for:

```text
1. Multiple issues discovered in one poll
   - GitHub poll returns 20 eligible issues
   - all are intaken within the same poll up to MAX_ISSUES_INTAKED_PER_POLL

2. Existing issue returned again
   - same GitHub issue appears in a later poll
   - it is skipped/idempotent and not intaken twice

3. Intelligence parallel claim safety
   - two workers try to process the same ticket
   - only one claim succeeds

4. Readiness parallel claim safety
   - two workers try to process the same ticket
   - only one claim succeeds

5. Concurrency bound
   - MAX_PARALLEL_TICKET_INTELLIGENCE=4
   - more than 4 eligible tickets exist
   - no more than 4 intelligence workers run at the same time

6. Execution worker limit unchanged
   - MAX_WORKERS / Dispatcher execution scheduling is unaffected
```

## Acceptance criteria update

Add:

```text
- Stage workers claim tickets atomically before processing.
- Parallel Intelligence cannot process the same ticket twice.
- Parallel Readiness cannot process the same ticket twice.
- GitHub issue intake is idempotent across repeated polls.
- Poll logs include discovered/intaked/skipped counts.
- Tests cover 20 issues discovered in one poll and concurrent claims for the same ticket.
```

## Non-goal reminder

Do not change coding execution concurrency in this ticket.

This ticket improves:

```text
GitHub discovery
intake throughput
intelligence/readiness throughput
```

It must not increase:

```text
number of coding workers launched by Dispatcher/daemon
```