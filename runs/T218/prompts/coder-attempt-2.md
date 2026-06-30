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

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

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

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


# T218 — Add batch-based backlog ingestion and dependency analysis pipeline before Dispatcher execution

**Source**: GitHub Issue #292

## Description

# Context

The current workflow continuously polls GitHub issues and immediately runs Ticket Intelligence and Readiness.

This works for isolated tickets but is not ideal for Dispatcher-driven execution because dependencies between newly created tickets may not yet be known.

We want to introduce a batch-oriented backlog ingestion workflow.

# Goal

Create batches of newly discovered tickets.

Tickets in a batch should first receive individual Ticket Intelligence analysis.

Once the backlog has been stable for a configurable amount of time, a global dependency analysis should run on the entire batch.

Only after dependency analysis is complete should Readiness and Dispatcher scheduling occur.

# Proposed workflow

```text
Poll GitHub every X seconds
↓
New ticket discovered
↓
Run Ticket Intelligence only
↓
Store ticket in current collecting batch
↓
No new tickets received for Y minutes
↓
Freeze batch
↓
Run Global Dependency Analysis on the whole batch
↓
Update dependencies on tickets
↓
Run Readiness for all tickets in the batch
↓
Dispatcher computes queue
↓
Daemon executes tickets
```

# Global Dependency Analysis responsibilities

The Global Dependency Analysis agent is responsible for building and maintaining a dependency graph for the entire batch.

The agent must analyze all tickets in the batch together and:

- detect implicit dependencies between tickets
- detect foundation/bootstrap tickets
- detect architectural prerequisites
- detect implementation ordering constraints
- detect tickets that can safely run in parallel
- detect conflicting tickets touching the same scope
- propose or update ticket dependencies

Examples:

```text
T001 - Define architecture
T010 - Bootstrap project

→ T010 depends on T001

T011 - Backend foundation
T012 - Frontend foundation

→ T011 depends on T010
→ T012 depends on T010

T015 - Task CRUD API
T016 - Frontend task client

→ T016 depends on T015
```

The analyzer should classify relationships:

```text
HARD_DEPENDENCY
SOFT_DEPENDENCY
FOUNDATION_DEPENDENCY
PARALLEL_COMPATIBLE
CONFLICTING_SCOPE
```

Outputs produced by the analyzer:

- depends_on[]
- blocks[]
- parallel_group
- conflicting_tickets[]
- execution_phase

The analyzer must also produce a global dependency graph.

Example:

```text
T001
└── T010
    ├── T011
    └── T012
         └── T016
```

The analyzer never directly decides execution order.

```text
Dependency Analyzer
→ builds and updates the graph

Dispatcher
→ computes scheduling and execution order
```

# Additional rule

While a batch is actively being executed by the Dispatcher:

```text
new incoming tickets
→ intelligence only
→ placed into next batch
→ no dependency analysis yet
```

This prevents changing the dependency graph while execution is in progress.

# New concepts

Introduce backlog batches with statuses such as:

```text
collecting
frozen
dependency_analysis_running
readiness_running
dispatching
completed
```

# Configuration

Add configurable settings:

```text
github_poll_interval_seconds
batch_idle_timeout_minutes
max_batch_size
allow_parallel_batches
```

# Acceptance criteria

- New tickets are grouped into batches.
- Ticket Intelligence still runs continuously for newly discovered tickets.
- Global Dependency Analysis only runs once a batch becomes idle.
- Dependencies discovered by the analysis are persisted back onto tickets.
- Readiness starts only after dependency analysis completes.
- Dispatcher only schedules tickets from a finalized batch.
- Tickets arriving while a batch is executing are queued for the next batch.
- Batch lifecycle and status are visible in logs.
- Existing non-dispatcher workflows remain supported.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

## Summary

T218 is implemented end-to-end, with all targeted tests green. Changes already committed to the branch by the daemon's auto-checkpoint as `2a7d88db`.

### What was built

**Schema (`tools/agent_runner/runtime_db.py`)**
- New tables: `backlog_batches`, `backlog_batch_tickets` (with `UNIQUE(ticket_id)`), `ticket_dependency_analysis` (PK `(ticket_id, batch_id)`, UPSERT-safe).
- Additive `ALTER TABLE` migration for `backlog_batches` columns guarded by `PRAGMA table_info`.
- Helpers: `insert/get/list_backlog_batches`, `update_backlog_batch`, `insert_backlog_batch_ticket`, `list_backlog_batch_ticket_ids`, `get_batch_for_ticket`, `upsert_dependency_analysis`, `get_dependency_analysis`.

**Lifecycle (`tools/agent_runner/backlog_batch.py`)**
- `BatchStatus` enum with exactly the 7 plan-mandated values; explicit test that `pending_collecting` is not present.
- `get_or_create_collecting_batch`, `add_ticket_to_batch`, `try_freeze_idle_batches`, `unblock_freezing_for_pending_collecting_batches`, `transition_batch` (guarded), `mark_dependency_analysis_attempt_started/succeeded/failed`, `pick_batches_ready_for_dependency_analysis`, `get_batch_status`, `get_ticket_batch_status`.
- Emits all required runtime events (`batch.created`, `batch.frozen`, `batch.freeze_blocked`, `batch.freeze_unblocked`, `batch.dependency_analysis_started/completed/failed/exhausted`, `batch.readiness_started`, status_changed, etc.). `exhausted` emitted exactly once.

**Analyzer (`tools/agent_runner/global_dependency_analyzer.py` + `prompts/global-dependency-analyzer-prompt.md`)**
- `AnalysisOutcome` dataclass; `run_global_analysis(db_path, runs_dir, batch_id, exec_cmd, …)` never raises.
- Builds the prompt from the batch ticket markdown + persisted intelligence summary/hints, runs `exec_cmd` with timeout, parses strict JSON, validates relationship types, persists per-ticket rows via UPSERT.

**Dependency union**
- `ticket_readiness_evaluator.collect_dependency_ticket_ids` now also unions `ticket_dependency_analysis.depends_on`.
- `ticket_execution_eligibility.evaluate_eligibility` reads + passes the analyzer row to `_eval_dependencies`.

**Daemon integration (`run_daemon.py`)**
- After successful issue intake, the new ticket is attached to the current collecting batch via `_attach_ticket_to_collecting_batch`.
- New `process_backlog_batches(db, runs_dir, exec_cmd)` runs once per cycle (`--once` and the main loop), driving: freeze → analyze → readiness_running → dispatching → completed, with retry/cooldown/exhaustion as per plan.
- Readiness pipeline (`ticket_pipeline.find_next_ticket`, `process_ticket`, `maybe_run_readiness_after_intelligence`) now gates on batch status — tickets without a batch keep legacy behaviour.
- Dispatcher (`ticket_dispatcher.get_recommended_tickets`) filters out tickets whose batch is not `dispatching`.

**Settings (`runtime_settings.py`)**
- `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS`, `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES`, `BACKLOG_MAX_BATCH_SIZE`, `BACKLOG_ALLOW_PARALLEL_BATCHES`, `BACKLOG_DEPENDENCY_ANALYSIS_MAX_ATTEMPTS`, `BACKLOG_DEPENDENCY_ANALYSIS_RETRY_COOLDOWN_MINUTES`.

### Tests (43 new tests, all green under `RUNTIME_DB_BACKEND=sqlite`)
- `tests/test_backlog_batch.py` — enum closedness, creation, idempotent membership, idle/size freeze, `allow_parallel_batches=False` lifecycle, retry scheduling, exhaustion terminal, transition guard.
- `tests/test_global_dependency_analyzer.py` — well-formed → persisted, malformed → failure (no raise), non-zero rc → failure, UPSERT no duplicates, invalid relationship type dropped.
- `tests/test_daemon_batch_lifecycle.py` — pipeline gated on batch, dispatcher gated on batch, ticket arriving during dispatch lands in blocked batch, retry success path, exhaustion event emitted once.
- `tests/test_ticket_readiness_evaluator.py` — new test: analyzer-only dep is included in union and blocks.
- `tests/test_run_daemon.py` — new test: `main --once` calls `process_backlog_batches` exactly once.

### Limits known
- The 4 remaining pre-existing failures (`test_main_once_returns_zero`, `test_main_returns_2_when_runs_dir_missing`, `test_main_calls_poll_ticket_pipeline_each_cycle`, `test_run_once_calls_launch_for_auto_runnable_state`) are not caused by this change — they fail on the unmodified branch because a real daemon process is already holding the singleton lock locally (and, when not, because the host DB has `DISPATCHER_ENABLED=advisory`).
- Only one batch is freeze-blocked at a time via the `prior_batch_dispatching` flag; the plan explicitly leaves cross-batch dependency analysis, batch UI/CLI, and operator-driven retry reset out of scope.

---

## Review

Now I have enough to write the review. Let me compose it.

# Review — T218

## Summary

The implementation is correct on the **SQLite backend** and faithfully follows the plan: closed `BatchStatus` enum (no `pending_collecting`), guarded transitions, `freeze_blocked` flag instead of a new status, retry/cooldown/exhaustion with the `batch.dependency_analysis_exhausted` event emitted exactly once, idempotent membership and analysis UPSERTs, dispatcher/readiness gating, dependency-union extension, and per-cycle integration in `run_daemon.py`. All 26 new tests in `tests/test_backlog_batch.py`, `tests/test_global_dependency_analyzer.py`, `tests/test_daemon_batch_lifecycle.py`, plus the new union case in `tests/test_ticket_readiness_evaluator.py::test_dependency_analysis_dep_included_in_union`, pass. The full repo suite was compared against `main`: no new failures were introduced (T218 has 113 failed / main has 112 failed, all attributable to pre-existing environmental issues; an external daemon holds the local singleton lock).

## Blocking issues

### B1. Postgres backend support missing — silent split-brain risk

The repository declares Postgres as a first-class backend, selected by `RUNTIME_DB_BACKEND=postgres`, with rebinding at `tools/agent_runner/runtime_db.py:1427-1482` that swaps the SQLite helpers for their `runtime_db_pg.py` counterparts. The module's own contract (`runtime_db.py:1378-1392`) reads:

> "Postgres mode NEVER falls back to SQLite. A backend mismatch between the API, the supervisor and the daemon is a configuration error: a silent downgrade would create an invisible split-brain..."

T218 adds three new tables (`backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis`) and nine new helpers (`insert_backlog_batch`, `get_backlog_batch`, `list_backlog_batches`, `update_backlog_batch`, `insert_backlog_batch_ticket`, `list_backlog_batch_ticket_ids`, `get_batch_for_ticket`, `upsert_dependency_analysis`, `get_dependency_analysis`) — exclusively on the SQLite side:

- `runtime_db_pg.py:_DDL` (lines 43-245) does not create the new tables, and `init_runtime_db(handle)` therefore won't create them in Postgres.
- None of the nine helpers are implemented in `runtime_db_pg.py` (verified: `grep "backlog\|dependency_analysis"` returns zero matches).
- The PG rebind block at `runtime_db.py:1427-1482` does not include any of the new helpers.

Consequence in PG mode: `backlog_batch.py` and `global_dependency_analyzer.py` call `runtime_db.list_backlog_batches(db_path, ...)`, which remains bound to the SQLite implementation. The SQLite helper executes `sqlite3.connect(str(db_path))` with `db_path` being a `PgHandle` object — `str(PgHandle)` returns `"backend=postgres project_id=... db=... host=..."` (see `runtime_db_pg.py:299`), so SQLite happily creates a new file at that literal path. Result: a silent SQLite split-brain exactly as the architecture comment warns. The plan's first acceptance criterion — *"Running the daemon on a fresh runtime DB creates the new tables ... and applies the additive ALTER TABLE migrations on existing DBs without errors"* — is not met in PG mode.

The `implementation-output.md` confirms tests were only run under `RUNTIME_DB_BACKEND=sqlite`; the new tests load `runtime_db.py` with `RUNTIME_DB_BACKEND=sqlite` forced via env override and then rebind `mod.runtime_db = _db`, so they cannot detect the PG gap.

Required fix:
- Add the three new tables (with PG-appropriate types/keys) to `runtime_db_pg.py:_DDL`.
- Implement the nine helpers in `runtime_db_pg.py` (mirroring the SQLite signatures; `insert_backlog_batch_ticket` must return `False` on unique-violation conflict, matching the SQLite contract).
- Rebind all nine helpers in the `if _RUNTIME_DB_BACKEND == "postgres":` block at `runtime_db.py:1427-1482`.
- Add at minimum a smoke test (mirroring `tests/test_runtime_db_pg.py` patterns) covering insert/list/upsert/UNIQUE for the new tables.

## Non-blocking observations

- **O1.** `tools/agent_runner/run_daemon.py:1834-1862` calls `_resolve_backlog_setting` 4× per cycle and `_attach_ticket_to_collecting_batch` calls it 2× per intaken ticket. Each call hits the `runtime_settings` registry, which re-queries the DB per call by design ("Tight inner loops are not in scope for V1" — `runtime_settings.py:12-16`). Acceptable for V1; consider caching when the cycle frequency increases.
- **O2.** `_advance_dispatching_batches` (`run_daemon.py:1923-1968`) uses `_TERMINAL_TICKET_STATES = {"TEST_COMPLETE", "CANCELLED"}` OR `daemon_archived` to mark a ticket terminal. The plan says *"every member has reached a terminal runtime state (merged, cancelled, or failed-final)"*. There is no explicit `FAILED_FINAL` ticket state in the codebase, and a permanently-failed ticket without `daemon_archived=1` would keep its batch stuck in `dispatching` forever and prevent `freeze_unblock`. Not blocking — current ticket-failure path archives via `daemon_archived` — but worth a follow-up to confirm there is no orphan-state risk.
- **O3.** The fix-context artifact `runs/T218/fixes/context-20260630T142858Z.md` (428 lines) is left in the worktree untracked. Workflow noise rather than a code issue, but worth cleaning up before merge.

## Verdict

The plan-defined behaviour is implemented correctly on SQLite and covered by passing, well-targeted tests; no regressions to the rest of the suite. The Postgres-backend gap (B1) is a hard architectural invariant violation that the repo explicitly warns against, and it must be closed before merge.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T218/reviews/implementation-review.md
- generated at: 2026-06-30T15:11:57Z

---

Now I have enough to write the review. Let me compose it.

# Review — T218

## Summary

The implementation is correct on the **SQLite backend** and faithfully follows the plan: closed `BatchStatus` enum (no `pending_collecting`), guarded transitions, `freeze_blocked` flag instead of a new status, retry/cooldown/exhaustion with the `batch.dependency_analysis_exhausted` event emitted exactly once, idempotent membership and analysis UPSERTs, dispatcher/readiness gating, dependency-union extension, and per-cycle integration in `run_daemon.py`. All 26 new tests in `tests/test_backlog_batch.py`, `tests/test_global_dependency_analyzer.py`, `tests/test_daemon_batch_lifecycle.py`, plus the new union case in `tests/test_ticket_readiness_evaluator.py::test_dependency_analysis_dep_included_in_union`, pass. The full repo suite was compared against `main`: no new failures were introduced (T218 has 113 failed / main has 112 failed, all attributable to pre-existing environmental issues; an external daemon holds the local singleton lock).

## Blocking issues

### B1. Postgres backend support missing — silent split-brain risk

The repository declares Postgres as a first-class backend, selected by `RUNTIME_DB_BACKEND=postgres`, with rebinding at `tools/agent_runner/runtime_db.py:1427-1482` that swaps the SQLite helpers for their `runtime_db_pg.py` counterparts. The module's own contract (`runtime_db.py:1378-1392`) reads:

> "Postgres mode NEVER falls back to SQLite. A backend mismatch between the API, the supervisor and the daemon is a configuration error: a silent downgrade would create an invisible split-brain..."

T218 adds three new tables (`backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis`) and nine new helpers (`insert_backlog_batch`, `get_backlog_batch`, `list_backlog_batches`, `update_backlog_batch`, `insert_backlog_batch_ticket`, `list_backlog_batch_ticket_ids`, `get_batch_for_ticket`, `upsert_dependency_analysis`, `get_dependency_analysis`) — exclusively on the SQLite side:

- `runtime_db_pg.py:_DDL` (lines 43-245) does not create the new tables, and `init_runtime_db(handle)` therefore won't create them in Postgres.
- None of the nine helpers are implemented in `runtime_db_pg.py` (verified: `grep "backlog\|dependency_analysis"` returns zero matches).
- The PG rebind block at `runtime_db.py:1427-1482` does not include any of the new helpers.

Consequence in PG mode: `backlog_batch.py` and `global_dependency_analyzer.py` call `runtime_db.list_backlog_batches(db_path, ...)`, which remains bound to the SQLite implementation. The SQLite helper executes `sqlite3.connect(str(db_path))` with `db_path` being a `PgHandle` object — `str(PgHandle)` returns `"backend=postgres project_id=... db=... host=..."` (see `runtime_db_pg.py:299`), so SQLite happily creates a new file at that literal path. Result: a silent SQLite split-brain exactly as the architecture comment warns. The plan's first acceptance criterion — *"Running the daemon on a fresh runtime DB creates the new tables ... and applies the additive ALTER TABLE migrations on existing DBs without errors"* — is not met in PG mode.

The `implementation-output.md` confirms tests were only run under `RUNTIME_DB_BACKEND=sqlite`; the new tests load `runtime_db.py` with `RUNTIME_DB_BACKEND=sqlite` forced via env override and then rebind `mod.runtime_db = _db`, so they cannot detect the PG gap.

Required fix:
- Add the three new tables (with PG-appropriate types/keys) to `runtime_db_pg.py:_DDL`.
- Implement the nine helpers in `runtime_db_pg.py` (mirroring the SQLite signatures; `insert_backlog_batch_ticket` must return `False` on unique-violation conflict, matching the SQLite contract).
- Rebind all nine helpers in the `if _RUNTIME_DB_BACKEND == "postgres":` block at `runtime_db.py:1427-1482`.
- Add at minimum a smoke test (mirroring `tests/test_runtime_db_pg.py` patterns) covering insert/list/upsert/UNIQUE for the new tables.

## Non-blocking observations

- **O1.** `tools/agent_runner/run_daemon.py:1834-1862` calls `_resolve_backlog_setting` 4× per cycle and `_attach_ticket_to_collecting_batch` calls it 2× per intaken ticket. Each call hits the `runtime_settings` registry, which re-queries the DB per call by design ("Tight inner loops are not in scope for V1" — `runtime_settings.py:12-16`). Acceptable for V1; consider caching when the cycle frequency increases.
- **O2.** `_advance_dispatching_batches` (`run_daemon.py:1923-1968`) uses `_TERMINAL_TICKET_STATES = {"TEST_COMPLETE", "CANCELLED"}` OR `daemon_archived` to mark a ticket terminal. The plan says *"every member has reached a terminal runtime state (merged, cancelled, or failed-final)"*. There is no explicit `FAILED_FINAL` ticket state in the codebase, and a permanently-failed ticket without `daemon_archived=1` would keep its batch stuck in `dispatching` forever and prevent `freeze_unblock`. Not blocking — current ticket-failure path archives via `daemon_archived` — but worth a follow-up to confirm there is no orphan-state risk.
- **O3.** The fix-context artifact `runs/T218/fixes/context-20260630T142858Z.md` (428 lines) is left in the worktree untracked. Workflow noise rather than a code issue, but worth cleaning up before merge.

## Verdict

The plan-defined behaviour is implemented correctly on SQLite and covered by passing, well-targeted tests; no regressions to the rest of the suite. The Postgres-backend gap (B1) is a hard architectural invariant violation that the repo explicitly warns against, and it must be closed before merge.

IMPLEMENTATION_FIX_REQUIRED