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



# T159 — T159 - Harden runtime SQLite architecture and degraded-mode recovery

**Source**: GitHub Issue #166

## Description

# T159 - Harden runtime SQLite architecture and degraded-mode recovery

## Problem

The runtime SQLite database regularly becomes corrupted (`database disk image is malformed`) and currently blocks:

- runtime dashboard visibility
- daemon ticket synchronization
- environment visibility
- runtime observability
- ticket execution flow

The current architecture is too fragile because runtime visibility depends too heavily on a single SQLite file.

---

# Goals

- Make the runtime platform resilient to SQLite corruption
- Ensure the Runtime dashboard remains usable even if SQLite fails
- Move toward a single global runtime database architecture
- Reduce corruption probability significantly
- Improve daemon/runtime recovery behavior

---

# Included

## Global runtime database architecture

Move toward:

```text
~/runtime/ai-dev-factory/.runtime/ai-dev-factory.sqlite
```

Rules:

- single runtime DB per ai-dev-factory instance
- worktrees must NOT create their own runtime DBs
- clone-local runtime DBs should be avoided
- runtime state becomes globally indexed

The runtime DB becomes:

- metadata/index/cache layer
- historical/runtime coordination layer

NOT the sole source of truth.

---

## Filesystem-first runtime architecture

The Runtime dashboard and environment visibility must continue functioning without SQLite.

Filesystem runtime state becomes the primary truth source:

```text
runtime/
  sandboxes/
    <sandbox-id>/
      state.json
      validation.json
      logs/
  proxy/routes/
  worktrees/
```

If SQLite fails:

- Runtime UI still renders environments
- sandboxes still appear
- routes still appear
- validation state still appears
- a degraded-mode warning is shown

---

## SQLite degraded-mode fallback

If SQLite access fails:

- log explicit corruption warning
- rename broken DB automatically
- recreate clean DB if possible
- continue runtime in degraded mode
- avoid daemon crash loops

Example:

```text
runtime DB corrupted -> entering degraded mode
```

---

## SQLite startup integrity checks

At startup:

```sql
PRAGMA integrity_check;
```

If integrity check fails:

- quarantine broken DB
- optionally attempt `.recover`
- recreate empty DB if recovery impossible
- continue degraded runtime mode

---

## SQLite hardening pragmas

Enable safer defaults:

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA synchronous=NORMAL;
```

Evaluate additional pragmas if needed.

---

## Single-writer protections

Add protections against multiple daemon writers:

- startup lock file
- daemon singleton guard
- clearer logs when another daemon already exists
- prevent concurrent SQLite writers when possible

---

## Runtime dashboard degraded UX

Runtime UI should display:

```text
SQLite runtime database unavailable
Showing filesystem-derived runtime state
```

The platform should remain observable.

---

## Cleanup of legacy runtime DB locations

Audit and remove accidental DB creation in:

```text
worktrees/*/.runtime/
clones/*/.runtime/
```

Ensure runtime DB path resolution is deterministic and centralized.

---

# Excluded

- No PostgreSQL migration
- No distributed runtime coordination
- No multi-user runtime synchronization
- No HA/replication architecture
- No cloud database support
- No Kubernetes persistence layer

---

# Acceptance criteria

- Runtime dashboard still works if SQLite becomes corrupted
- Daemon does not enter infinite crash/retry loops on malformed DB
- Runtime state remains observable through filesystem fallback
- Only one global runtime DB is used
- Worktrees no longer create runtime SQLite DBs
- SQLite corruption probability is significantly reduced
- Startup integrity checks run automatically
- Broken DBs are quarantined automatically
- Users receive explicit degraded-mode warnings
- Existing deploy/sandbox/runtime flows continue functioning

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Plan saved to `runs/T159/plan.md`. Here is the output:

---

## Objective

Harden the runtime SQLite layer so corruption never blocks dashboard visibility or daemon operation: add startup integrity checks with automatic quarantine, add missing hardening pragmas, expose a degraded-mode flag to the board UI, and confirm the single-global-DB invariant is already enforced.

## Included

### 1. `tools/agent_runner/runtime_db.py` — hardening pragmas
- Add `PRAGMA busy_timeout=5000` and `PRAGMA synchronous=NORMAL` to both `init_runtime_db()` and `_connect()` (WAL mode is already set; these two are missing).

### 2. `tools/agent_runner/runtime_db.py` — startup integrity check + quarantine
- Add `check_and_recover_db(db_path: Path) -> bool`:
  - Open connection, run `PRAGMA integrity_check`.
  - If result is not `[('ok',)]`: rename to `<stem>.corrupted-<YYYYMMDDTHHmmss>.sqlite`; log `"runtime DB corrupted -> entering degraded mode"`.
  - Attempt recovery via iterdump into a new DB; if impossible, recreate empty DB from schema.
  - Return `True` if healthy or recovered, `False` if degraded.
- File rename is atomic on POSIX; function is safe for concurrent callers.

### 3. `tools/agent_runner/run_daemon.py` — use integrity check at startup
- In `_ensure_db()`: call `check_and_recover_db(db_path)` before `_rdb_init()`.
- Add module-level `_DB_DEGRADED: bool = False`; set to `True` on corruption.
- Improve singleton log: emit `"daemon already running (pid=<N>) — exiting to avoid concurrent SQLite writers"` when live PID detected.

### 4. `services/control_api/models/schemas.py` — extend `BoardResponse`
- Add `sqlite_degraded: bool = False` field.

### 5. `services/control_api/services/board_service.py` — surface degraded state
- Catch `sqlite3.DatabaseError` explicitly and log at `WARNING` level (not silent `pass`).
- Set `sqlite_degraded = True` when SQLite is unavailable or throws; include in `BoardResponse`.

### 6. `apps/dashboard/src/pages/BoardPage.jsx` — degraded-mode banner
- When `sqlite_degraded` is `true`, render a visible warning banner: _"SQLite runtime database unavailable — showing filesystem-derived state."_

### 7. Worktree/clone DB audit (read-only)
- Grep for secondary `sqlite3.connect` / `init_runtime_db` calls that could create a DB under `worktrees/` or `clones/`; fix any found, or add a comment in `get_db_path()` confirming the invariant holds.

## Excluded

- PostgreSQL or any other non-SQLite backend.
- Distributed or multi-user runtime coordination.
- WAL checkpoint tuning, page-size tuning, or vacuum scheduling.
- Any change to sandbox runtime roots (`sandboxes/<id>/runtime/`).
- Shell `.recover` integration if stdlib-only approach succeeds.
- `runtime_dashboard.py` routes — already filesystem-first.
- Daemon tick loop, retry policies, or ticket execution flow.

## Acceptance criteria

- `PRAGMA busy_timeout=5000` and `PRAGMA synchronous=NORMAL` present in `_connect()` and `init_runtime_db()`.
- `PRAGMA integrity_check` runs at daemon startup; corrupt DB is quarantined and a fresh DB is created automatically.
- Daemon log contains `"runtime DB corrupted -> entering degraded mode"` on integrity failure.
- `BoardResponse.sqlite_degraded` is `true` when SQLite is unavailable or corrupt.
- Board API returns HTTP 200 with filesystem-derived tickets when SQLite is absent or corrupt.
- Dashboard renders degraded-mode banner when `sqlite_degraded` is `true`.
- Grep confirms no secondary `ai-dev-factory.sqlite` can be created under worktrees or clones.
- Existing daemon, board, and sandbox test suites pass without regressions.

---

## Review

T159 review:

The plan is good overall.

Main required correction:
SQLite recovery/quarantine must be protected by a file lock.

Atomic rename alone is not enough because the full sequence is:
- integrity_check
- corruption decision
- DB quarantine
- recovery/recreate
- schema initialization

That whole flow is a critical section.

Recommendation:
Add a recovery lock file such as:
<db_path>.recovery.lock

Acceptance criteria to add:
- concurrent recovery attempts cannot recreate/quarantine simultaneously
- recovery is protected by a file lock
- race conditions are tested

---

## Instructions de fix

T159 plan fix v1:

Required correction:
Protect SQLite recovery/quarantine with a file lock.

The current plan should not imply that atomic rename alone makes concurrent recovery safe.

Required updates to runs/T159/plan.md:

1. Replace the concurrent safety statement with:

File rename is atomic on POSIX, but recovery/quarantine must still be protected by a file lock.

2. Add:

- Add a file-lock guard around check_and_recover_db(db_path)
- lock path: <db_path>.recovery.lock
- acquire before integrity_check/quarantine/recreate
- release after recovery or empty DB initialization

3. Add acceptance criteria:

- concurrent recovery attempts cannot recreate/quarantine simultaneously
- recovery/quarantine is protected by a file lock
- recovery race conditions are tested