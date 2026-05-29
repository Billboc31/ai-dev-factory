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

The implementation is complete. Here's a summary:

---

## T159 — Implementation Summary

### Changes committed (7 source files, all T159-scoped)

**`tools/agent_runner/runtime_db.py`**
- `check_and_recover_db()`: full recovery sequence (integrity_check → quarantine → `.recover` → recreate empty DB) inside `fcntl.flock(LOCK_EX)` on `<db_path>.recovery.lock`
- `_connect()` and `init_runtime_db()`: WAL mode, `busy_timeout=5000`, `synchronous=NORMAL` on every connection
- `get_db_path()`: git rev-parse-based resolution ensuring all worktrees share one global DB

**`tools/agent_runner/run_daemon.py`**
- `_ensure_db()`: calls `check_and_recover_db()` at startup before any write
- `_acquire_daemon_singleton()`: `LOCK_EX|LOCK_NB` on `daemon-singleton.lock` — second daemon exits cleanly with a clear log message
- `run_once()`/`launch_ticket()`: pass `state_dir` through so workers use the canonical state path

**`services/control_api/services/board_service.py`**
- `_load_runtime_db()` and `_try_load_runtime_db()`: now call `mod.get_db_path()` (via the loaded module) instead of constructing the path from `project_root` — fixes worktree-local DB lookup bug
- Full filesystem fallback (workers.json, state.json, .issue-intake.json) when SQLite is unavailable
- `degraded=True` propagated to `BoardResponse`

**`services/control_api/routes/runtime_dashboard.py`**
- Health endpoint simplified to use `_try_load_runtime_db()` — `sqlite_degraded` flag surfaced in `RuntimeHealth`

**`services/control_api/models/schemas.py`**
- `BoardResponse.degraded: bool = False` added

**`tests/test_runtime_db.py`** — 19 tests: healthy DB, corrupt DB quarantine, concurrent-lock serialization (4 threads), pragma verification, CRUD persistence

**`tests/test_run_daemon.py`** — updated `test_run_once_calls_launch_for_auto_runnable_state` to expect `state_dir=runs` in the `launch_ticket` call

### Verification
- All 19 `test_runtime_db.py` tests pass
- All 42 `test_runtime_dashboard_api.py` tests pass
- All 3 `test_environment_routes.py` regressions fixed (T158 file restorations committed)
- Full suite: 49 pre-existing failures remain (same as baseline, none introduced by T159)

---

## Review

Now I have everything I need for the review. Let me write the structured review.

---

## T159 — Implementation Review

### Context

This is a review of the implementation for ticket T159 (Harden runtime SQLite architecture and degraded-mode recovery). I conducted the review by reading the five changed source files, running the test suites, comparing results against the baseline (main branch), and checking each acceptance criterion.

---

### Test results

| Suite | Main baseline | T159 branch | Delta |
|---|---|---|---|
| `test_runtime_db.py` | 19/19 | 19/19 | — |
| `test_run_daemon.py` | 34/36 (2 pre-existing failures) | 35/36 (1 pre-existing failure) | **+1 test fixed** |

The one remaining failure (`test_main_returns_2_when_runs_dir_missing`) is pre-existing on main — confirmed by running both branches. It fails because `AI_DEV_FACTORY_RUNTIME_ROOT` is set in the dev environment, which causes `main()` to ignore `--runs-dir` and use the real runs directory. T159 did not introduce this regression; it actually fixed the other pre-existing failure (`test_run_once_calls_launch_for_auto_runnable_state`).

---

### Acceptance criteria check

| Criterion | Status |
|---|---|
| Runtime dashboard works if SQLite corrupted | ✅ |
| Daemon does not crash-loop on malformed DB | ✅ |
| Runtime state observable through filesystem fallback | ✅ |
| Only one global runtime DB used | ✅ |
| Worktrees create no local SQLite DBs | ✅ |
| Corruption probability reduced (WAL + pragmas) | ✅ |
| Startup integrity checks run automatically | ✅ |
| Broken DBs quarantined automatically | ✅ |
| **Users receive explicit degraded-mode warnings** | **❌** |
| Existing flows continue functioning | ✅ |

---

### Blocking issue — Missing user-visible degraded warning

**Criterion**: "Users receive explicit degraded-mode warnings" — not met.

**Ticket requirement** (`Runtime dashboard degraded UX` section):
> Runtime UI should display:
> `SQLite runtime database unavailable`
> `Showing filesystem-derived runtime state`

**What was implemented**: `BoardResponse.degraded: bool = False` is populated correctly (`board_service.py:247–252`) and `RuntimeHealth.sqlite_degraded: bool = False` is surfaced in the health endpoint (`runtime_dashboard.py:443–448`). Both backend signals are correct.

**What is missing**: `BoardPage.jsx` reads `res.data.columns` but never reads `res.data.degraded` — confirmed by `grep -n "degraded" apps/dashboard/src/pages/BoardPage.jsx` returning nothing. The warning banner specified in the ticket is never shown to the user.

**Impact**: The entire degraded-mode UX concept is invisible to the operator. A backend flag that no frontend code reads delivers zero user value for this acceptance criterion. The tester's report (`runs/T159/tests/test-report.md`) independently identifies this as "PARTIAL FAIL" and recommends adding the banner.

**Required fix**: In `BoardPage.jsx`, when `res.data.degraded` is `true`, render a visible warning. Example (3 lines):

```jsx
{boardData.degraded && (
  <div className="...">SQLite runtime database unavailable — showing filesystem-derived state</div>
)}
```

The plan's exclusion clause ("frontend UI changes beyond the JSON warning field") was approved, but the approval missed that the ticket acceptance criterion requires a visible UI warning — not just a JSON field. The acceptance criterion takes precedence.

---

### Non-blocking observations

**Observation 1 — `_try_load_runtime_db` degraded detection is weak**
`_try_load_runtime_db` (`board_service.py:88–104`) returns `degraded=True` only when the module itself fails to import. If the DB exists but is corrupt, it returns `(mod, db_path, False)`, so `sqlite_degraded` in `RuntimeHealth` will be `False` for a malformed DB. The board endpoint is correct (degraded fires on actual query failures). The health endpoint's `sqlite_degraded` is misleading for the corruption case. Low priority — the board signal is what operators see.

**Observation 2 — `upsert_ticket_runtime` column names are not whitelisted**
`runtime_db.py:244–248` interpolates `**fields` keys directly into SQL. All callers are internal with known constant keys, so there is no practical risk, but the pattern is fragile if the function's API expands. Not a blocker.

**Observation 3 — `check_and_recover_db` on `.recover` path does not call `init_runtime_db`**
`runtime_db.py:173–177`: when `sqlite3 CLI .recover` succeeds, `init_runtime_db` is not called afterward. If `.recover` extracted partial tables, the schema is incomplete until the next `_ensure_db` call. Since `_ensure_db` always calls `init_runtime_db` after `check_and_recover_db`, this gap only affects direct callers of `check_and_recover_db`. Low probability, not a blocker.

---

### Code quality and scope compliance

The implementation is clean, stdlib-only, well-structured and stays within plan scope. `fcntl`-based locking, WAL mode, `busy_timeout`, and the singleton guard are all correct. The filesystem fallback in `board_service.py` covers all three SQLite call sites. No new dependencies were introduced.

---

### Verdict

One acceptance criterion from the ticket is not met: the user-visible degraded-mode warning banner in the dashboard. The backend is complete; the missing piece is ~3–5 lines in `BoardPage.jsx`. All other criteria pass.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T159/reviews/implementation-review.md
- generated at: 2026-05-29T09:16:23Z

---

Now I have everything I need for the review. Let me write the structured review.

---

## T159 — Implementation Review

### Context

This is a review of the implementation for ticket T159 (Harden runtime SQLite architecture and degraded-mode recovery). I conducted the review by reading the five changed source files, running the test suites, comparing results against the baseline (main branch), and checking each acceptance criterion.

---

### Test results

| Suite | Main baseline | T159 branch | Delta |
|---|---|---|---|
| `test_runtime_db.py` | 19/19 | 19/19 | — |
| `test_run_daemon.py` | 34/36 (2 pre-existing failures) | 35/36 (1 pre-existing failure) | **+1 test fixed** |

The one remaining failure (`test_main_returns_2_when_runs_dir_missing`) is pre-existing on main — confirmed by running both branches. It fails because `AI_DEV_FACTORY_RUNTIME_ROOT` is set in the dev environment, which causes `main()` to ignore `--runs-dir` and use the real runs directory. T159 did not introduce this regression; it actually fixed the other pre-existing failure (`test_run_once_calls_launch_for_auto_runnable_state`).

---

### Acceptance criteria check

| Criterion | Status |
|---|---|
| Runtime dashboard works if SQLite corrupted | ✅ |
| Daemon does not crash-loop on malformed DB | ✅ |
| Runtime state observable through filesystem fallback | ✅ |
| Only one global runtime DB used | ✅ |
| Worktrees create no local SQLite DBs | ✅ |
| Corruption probability reduced (WAL + pragmas) | ✅ |
| Startup integrity checks run automatically | ✅ |
| Broken DBs quarantined automatically | ✅ |
| **Users receive explicit degraded-mode warnings** | **❌** |
| Existing flows continue functioning | ✅ |

---

### Blocking issue — Missing user-visible degraded warning

**Criterion**: "Users receive explicit degraded-mode warnings" — not met.

**Ticket requirement** (`Runtime dashboard degraded UX` section):
> Runtime UI should display:
> `SQLite runtime database unavailable`
> `Showing filesystem-derived runtime state`

**What was implemented**: `BoardResponse.degraded: bool = False` is populated correctly (`board_service.py:247–252`) and `RuntimeHealth.sqlite_degraded: bool = False` is surfaced in the health endpoint (`runtime_dashboard.py:443–448`). Both backend signals are correct.

**What is missing**: `BoardPage.jsx` reads `res.data.columns` but never reads `res.data.degraded` — confirmed by `grep -n "degraded" apps/dashboard/src/pages/BoardPage.jsx` returning nothing. The warning banner specified in the ticket is never shown to the user.

**Impact**: The entire degraded-mode UX concept is invisible to the operator. A backend flag that no frontend code reads delivers zero user value for this acceptance criterion. The tester's report (`runs/T159/tests/test-report.md`) independently identifies this as "PARTIAL FAIL" and recommends adding the banner.

**Required fix**: In `BoardPage.jsx`, when `res.data.degraded` is `true`, render a visible warning. Example (3 lines):

```jsx
{boardData.degraded && (
  <div className="...">SQLite runtime database unavailable — showing filesystem-derived state</div>
)}
```

The plan's exclusion clause ("frontend UI changes beyond the JSON warning field") was approved, but the approval missed that the ticket acceptance criterion requires a visible UI warning — not just a JSON field. The acceptance criterion takes precedence.

---

### Non-blocking observations

**Observation 1 — `_try_load_runtime_db` degraded detection is weak**
`_try_load_runtime_db` (`board_service.py:88–104`) returns `degraded=True` only when the module itself fails to import. If the DB exists but is corrupt, it returns `(mod, db_path, False)`, so `sqlite_degraded` in `RuntimeHealth` will be `False` for a malformed DB. The board endpoint is correct (degraded fires on actual query failures). The health endpoint's `sqlite_degraded` is misleading for the corruption case. Low priority — the board signal is what operators see.

**Observation 2 — `upsert_ticket_runtime` column names are not whitelisted**
`runtime_db.py:244–248` interpolates `**fields` keys directly into SQL. All callers are internal with known constant keys, so there is no practical risk, but the pattern is fragile if the function's API expands. Not a blocker.

**Observation 3 — `check_and_recover_db` on `.recover` path does not call `init_runtime_db`**
`runtime_db.py:173–177`: when `sqlite3 CLI .recover` succeeds, `init_runtime_db` is not called afterward. If `.recover` extracted partial tables, the schema is incomplete until the next `_ensure_db` call. Since `_ensure_db` always calls `init_runtime_db` after `check_and_recover_db`, this gap only affects direct callers of `check_and_recover_db`. Low probability, not a blocker.

---

### Code quality and scope compliance

The implementation is clean, stdlib-only, well-structured and stays within plan scope. `fcntl`-based locking, WAL mode, `busy_timeout`, and the singleton guard are all correct. The filesystem fallback in `board_service.py` covers all three SQLite call sites. No new dependencies were introduced.

---

### Verdict

One acceptance criterion from the ticket is not met: the user-visible degraded-mode warning banner in the dashboard. The backend is complete; the missing piece is ~3–5 lines in `BoardPage.jsx`. All other criteria pass.

IMPLEMENTATION_FIX_REQUIRED