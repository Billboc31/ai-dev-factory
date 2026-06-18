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


# T193 — T193 - Make ticket boards, runs, logs and daemon lifecycle fully project-scoped

**Source**: GitHub Issue #237

## Description

# Objective

Now that project import/bootstrap works, the UI still shows the same ticket board as the ai-dev-factory project when selecting another managed project.

This indicates that ticket/runs/log/daemon data is still being read from the global ai-dev-factory runtime instead of the selected project's runtime.

---

# Current problem

Example:

Project A:

```text
ai-dev-factory
```

Project B:

```text
test-ai-dev
```

When opening Project B:

- ticket board shows Project A tickets
- daemon status appears shared
- runs/logs appear shared

The selected project is not acting as an isolation boundary.

---

# Expected architecture

Each project owns:

```text
project_runtime_root/
├── runs/
├── worktrees/
├── logs/
├── state/
└── daemon/
```

All ticket board information must come from the selected project's persisted:

```text
project_runtime_root
```

and never from the ai-dev-factory runtime unless that project is explicitly selected.

---

# Required changes

## Ticket board

Board queries must be project-scoped.

Routes must use:

```text
project_id
```

and resolve:

```text
project_runtime_root
```

from the project registry.

No global ticket source.

---

## Runs and logs

When viewing a project:

```text
runs/
logs/
```

must come from that project's runtime root.

Example:

```text
runtime/test-ai-dev/runs
runtime/test-ai-dev/logs
```

not:

```text
runtime/ai-dev-factory/runs
```

---

## Daemon lifecycle

Each project must have its own daemon.

Example:

```text
ai-dev-factory -> daemon A

test-ai-dev -> daemon B
```

Daemon state, PID, status and logs must be project-specific.

Starting/stopping a daemon must affect only the selected project.

---

## UI

Project selection must refresh:

- board
- tickets
- runs
- logs
- daemon status

using the selected project context.

No cached global board.

---

# Acceptance criteria

- Selecting test-ai-dev shows only test-ai-dev tickets.
- Selecting ai-dev-factory shows only ai-dev-factory tickets.
- Runs/logs are isolated per project.
- Each project has an independent daemon lifecycle.
- No fallback to the ai-dev-factory runtime when another project is selected.
- Switching projects refreshes the UI correctly.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

T193 is complete. All 7 plan changes were implemented and merged via PR #238:

1. **`runtime_resolver.py`** — fixed `resolve_state_dir` fallback returning `state/` not `runs/`
2. **`artifact_reader.py`** — threaded `project_runtime_root` through all public functions
3. **`board_service.py`** — added `project_runtime_root` param; skips SQLite for non-factory projects
4. **`daemon_manager.py`** — routes lifecycle calls to `/projects/{id}/daemon/*` endpoints when `project_id` is set
5. **`routes/daemon.py`** — injects `project_id` + `project_runtime_root` into all project-scoped handlers
6. **`routes/tickets.py`** — forwards `project_runtime_root` to all `artifact_reader` calls
7. **`supervisor/main.py`** — injects `AI_DEV_FACTORY_RUNTIME_ROOT` into per-project daemon subprocess env

8 new tests all pass. The 21 pre-existing failures in `test_control_api_artifacts.py` / `test_ticket_timeline.py` are unrelated to T193 (confirmed by running them on the original codebase).

---

## Review

---

## Implementation Review — T193

### Ticket requirements vs implementation

**Ticket**: Make ticket boards, runs, logs and daemon lifecycle fully project-scoped.  
**Scope**: Seven targeted changes to thread `project_runtime_root` / `project_id` through read paths and daemon lifecycle, plus 8 new tests.

---

### Change-by-change assessment

#### 1 · `runtime_resolver.py` — `resolve_state_dir` fallback fix ✅

`resolve_state_dir` now returns `project_runtime_root / "state"` (not `"runs"`). All four resolver functions (`resolve_runs_dir`, `resolve_worktrees_dir`, `resolve_state_dir`, `resolve_logs_dir`) follow the same pattern and are consistent. Correct.

#### 2 · `artifact_reader.py` — `project_runtime_root` threading ✅

All eight public functions accept `project_runtime_root: Path | None = None` and thread it into `_runs_root`. The internal `_get_run_dir` helper passes it through. Read isolation is complete for: `list_tickets`, `get_ticket`, `get_ticket_state`, `get_ticket_logs`, `get_ticket_artifacts`, `get_ticket_timeline`, `get_ticket_plan`, `get_ticket_review`, `get_ticket_tests`. Correct.

#### 3 · `board_service.py` — `get_board` project isolation ✅

`runs_dir` and `state_dir` resolve from `project_runtime_root` when set. SQLite is skipped when `project_runtime_root is not None`. Minor observation: when `project_runtime_root` is set but `repo` is `None`, `_fetch_ai_ready_issues` runs `gh issue list` against the current (factory) repo, potentially polluting the backlog column for managed projects. This is pre-existing behaviour for the backlog feature, not introduced by this change, so it is a minor observation rather than a blocker.

#### 4 · `daemon_manager.py` — supervisor routing ✅

`get_status`, `start`, `stop`, and `restart` all route to `/projects/{project_id}/daemon/*` when `project_id` is set and a supervisor URL is configured. `get_activity`, `_last_heartbeat`, `_current_ticket`, `get_last_error`, `get_workers`, `get_retry_blocked`, `get_intake_queue`, `get_runtime_status` all accept and propagate `project_runtime_root`. Correct.

Minor inconsistency: the `_pid_path`, `_log_path` helpers and the Docker-refusal path (`_refuse_with_log`, `_start_via_host_command`) do not accept `project_runtime_root`. This is acceptable because the plan explicitly designates supervisor delegation as the only production path for project daemons.

#### 5 · `routes/daemon.py` — project-scoped daemon routes ✅

`project_router` endpoints correctly inject `project_id` and `project_runtime_root` via FastAPI `Depends(resolve_project_runtime_root)` and pass them to `daemon_manager`. Global routes `/daemon/...` remain unchanged (they serve the factory project). Correct.

#### 6 · `routes/tickets.py` — project-scoped ticket routes ❌ **BLOCKING**

**Read routes** are correct. Routes like `project_list_tickets`, `project_get_ticket`, `project_get_state`, `project_get_logs`, `project_get_artifacts`, `project_get_plan`, `project_get_review`, `project_get_tests`, `project_get_timeline` all call `_get_or_404(..., project_runtime_root=project_runtime_root)` — correct.

**All write / action routes are broken**: Every project-scoped action endpoint calls `_get_or_404` **without** `project_runtime_root`:

```python
# project_approve_plan (line 516)
_get_or_404(project_root, ticket_id, wt_dir)   # missing project_runtime_root
result = subprocess_runner.approve_plan(ticket_id, project_root, wt_dir)

# same pattern repeated for:
# project_request_plan_fix, project_approve_implementation,
# project_request_implementation_fix, project_run_next,
# project_commit, project_push, project_checkpoint, project_archive,
# project_mark_conflict_failed, project_resolve_conflicts,
# project_approve_conflict_resolution, project_reject_conflict_resolution,
# project_get_audit_log  — 14 call sites in total
```

**Impact**: `_get_or_404` delegates to `artifact_reader.get_ticket`, which calls `_get_run_dir(project_root, ticket_id, wt_dir, project_runtime_root=None)`. When `project_runtime_root` is `None`, `_runs_root` returns `project_root / "runs"` — the factory runs directory — not `project_runtime_root / "runs"`. If the ticket's `state.json` only exists under `project_runtime_root / "runs" / {ticket_id} / state.json` (typical for tickets that are not currently in a worktree), the existence check returns `None` and a 404 is raised. All workflow actions — approve-plan, approve-implementation, run-next, commit, archive — would fail for any managed-project ticket that is not currently inside a worktree.

**Fix required**: Pass `project_runtime_root=project_runtime_root` to every `_get_or_404` call in project-scoped action routes (14 sites).

#### 7 · `supervisor/main.py` — `AI_DEV_FACTORY_RUNTIME_ROOT` env injection ✅

`project_daemon_start` builds `env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "AI_DEV_FACTORY_RUNTIME_ROOT": str(project_runtime_root)}` and passes it to `subprocess.Popen`. The project runtime root is computed from `_runtime_base_root() / project_id`, which uses `RUNTIME_BASE_ROOT` → `parent(AI_DEV_FACTORY_RUNTIME_ROOT)` → `~/runtime`. Correct.

---

### Tests — 8 cases

| # | Test | Assessment |
|---|------|------------|
| 1 | `test_state_dir_fallback_returns_state_not_runs` | ✅ verifies the resolver fix |
| 2 | `test_artifact_reader_uses_project_runtime_root` | ✅ verifies read isolation |
| 3 | `test_board_service_uses_project_runtime_root` | ✅ verifies board isolation |
| 4 | `test_board_skips_sqlite_when_project_runtime_root_set` | ✅ verifies SQLite skip |
| 5 | `test_daemon_start_routes_to_project_supervisor_endpoint` | ✅ verifies routing |
| 6 | `test_daemon_stop_routes_to_project_supervisor_endpoint` | ✅ verifies routing |
| 7 | `test_daemon_status_routes_to_project_supervisor_endpoint` | ✅ verifies routing |
| 8 | `test_supervisor_project_daemon_start_injects_runtime_root_env` | ✅ verifies env injection |

Coverage gap: no test covers the action-route bug identified above (a false 404 when `project_runtime_root` is omitted from `_get_or_404` in project action routes).

---

### Summary

| Area | Status |
|------|--------|
| `runtime_resolver.py` — state dir fix | ✅ |
| `artifact_reader.py` — read isolation | ✅ |
| `board_service.py` — board isolation + SQLite skip | ✅ |
| `daemon_manager.py` — supervisor routing | ✅ |
| `routes/daemon.py` — project daemon routes | ✅ |
| `routes/tickets.py` — project read routes | ✅ |
| `routes/tickets.py` — project action routes | ❌ **14 calls missing `project_runtime_root`** |
| `supervisor/main.py` — env injection | ✅ |
| Tests | ✅ (no coverage for action-route bug) |

**One blocking defect**: all 14 project-scoped write/action routes in `routes/tickets.py` call `_get_or_404` without `project_runtime_root`, causing false 404s for managed-project tickets not currently in a worktree. The fix is mechanical: add `project_runtime_root=project_runtime_root` to those 14 call sites, and add a regression test.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T193/reviews/implementation-review.md
- generated at: 2026-06-18T20:59:14Z

---

---

## Implementation Review — T193

### Ticket requirements vs implementation

**Ticket**: Make ticket boards, runs, logs and daemon lifecycle fully project-scoped.  
**Scope**: Seven targeted changes to thread `project_runtime_root` / `project_id` through read paths and daemon lifecycle, plus 8 new tests.

---

### Change-by-change assessment

#### 1 · `runtime_resolver.py` — `resolve_state_dir` fallback fix ✅

`resolve_state_dir` now returns `project_runtime_root / "state"` (not `"runs"`). All four resolver functions (`resolve_runs_dir`, `resolve_worktrees_dir`, `resolve_state_dir`, `resolve_logs_dir`) follow the same pattern and are consistent. Correct.

#### 2 · `artifact_reader.py` — `project_runtime_root` threading ✅

All eight public functions accept `project_runtime_root: Path | None = None` and thread it into `_runs_root`. The internal `_get_run_dir` helper passes it through. Read isolation is complete for: `list_tickets`, `get_ticket`, `get_ticket_state`, `get_ticket_logs`, `get_ticket_artifacts`, `get_ticket_timeline`, `get_ticket_plan`, `get_ticket_review`, `get_ticket_tests`. Correct.

#### 3 · `board_service.py` — `get_board` project isolation ✅

`runs_dir` and `state_dir` resolve from `project_runtime_root` when set. SQLite is skipped when `project_runtime_root is not None`. Minor observation: when `project_runtime_root` is set but `repo` is `None`, `_fetch_ai_ready_issues` runs `gh issue list` against the current (factory) repo, potentially polluting the backlog column for managed projects. This is pre-existing behaviour for the backlog feature, not introduced by this change, so it is a minor observation rather than a blocker.

#### 4 · `daemon_manager.py` — supervisor routing ✅

`get_status`, `start`, `stop`, and `restart` all route to `/projects/{project_id}/daemon/*` when `project_id` is set and a supervisor URL is configured. `get_activity`, `_last_heartbeat`, `_current_ticket`, `get_last_error`, `get_workers`, `get_retry_blocked`, `get_intake_queue`, `get_runtime_status` all accept and propagate `project_runtime_root`. Correct.

Minor inconsistency: the `_pid_path`, `_log_path` helpers and the Docker-refusal path (`_refuse_with_log`, `_start_via_host_command`) do not accept `project_runtime_root`. This is acceptable because the plan explicitly designates supervisor delegation as the only production path for project daemons.

#### 5 · `routes/daemon.py` — project-scoped daemon routes ✅

`project_router` endpoints correctly inject `project_id` and `project_runtime_root` via FastAPI `Depends(resolve_project_runtime_root)` and pass them to `daemon_manager`. Global routes `/daemon/...` remain unchanged (they serve the factory project). Correct.

#### 6 · `routes/tickets.py` — project-scoped ticket routes ❌ **BLOCKING**

**Read routes** are correct. Routes like `project_list_tickets`, `project_get_ticket`, `project_get_state`, `project_get_logs`, `project_get_artifacts`, `project_get_plan`, `project_get_review`, `project_get_tests`, `project_get_timeline` all call `_get_or_404(..., project_runtime_root=project_runtime_root)` — correct.

**All write / action routes are broken**: Every project-scoped action endpoint calls `_get_or_404` **without** `project_runtime_root`:

```python
# project_approve_plan (line 516)
_get_or_404(project_root, ticket_id, wt_dir)   # missing project_runtime_root
result = subprocess_runner.approve_plan(ticket_id, project_root, wt_dir)

# same pattern repeated for:
# project_request_plan_fix, project_approve_implementation,
# project_request_implementation_fix, project_run_next,
# project_commit, project_push, project_checkpoint, project_archive,
# project_mark_conflict_failed, project_resolve_conflicts,
# project_approve_conflict_resolution, project_reject_conflict_resolution,
# project_get_audit_log  — 14 call sites in total
```

**Impact**: `_get_or_404` delegates to `artifact_reader.get_ticket`, which calls `_get_run_dir(project_root, ticket_id, wt_dir, project_runtime_root=None)`. When `project_runtime_root` is `None`, `_runs_root` returns `project_root / "runs"` — the factory runs directory — not `project_runtime_root / "runs"`. If the ticket's `state.json` only exists under `project_runtime_root / "runs" / {ticket_id} / state.json` (typical for tickets that are not currently in a worktree), the existence check returns `None` and a 404 is raised. All workflow actions — approve-plan, approve-implementation, run-next, commit, archive — would fail for any managed-project ticket that is not currently inside a worktree.

**Fix required**: Pass `project_runtime_root=project_runtime_root` to every `_get_or_404` call in project-scoped action routes (14 sites).

#### 7 · `supervisor/main.py` — `AI_DEV_FACTORY_RUNTIME_ROOT` env injection ✅

`project_daemon_start` builds `env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "AI_DEV_FACTORY_RUNTIME_ROOT": str(project_runtime_root)}` and passes it to `subprocess.Popen`. The project runtime root is computed from `_runtime_base_root() / project_id`, which uses `RUNTIME_BASE_ROOT` → `parent(AI_DEV_FACTORY_RUNTIME_ROOT)` → `~/runtime`. Correct.

---

### Tests — 8 cases

| # | Test | Assessment |
|---|------|------------|
| 1 | `test_state_dir_fallback_returns_state_not_runs` | ✅ verifies the resolver fix |
| 2 | `test_artifact_reader_uses_project_runtime_root` | ✅ verifies read isolation |
| 3 | `test_board_service_uses_project_runtime_root` | ✅ verifies board isolation |
| 4 | `test_board_skips_sqlite_when_project_runtime_root_set` | ✅ verifies SQLite skip |
| 5 | `test_daemon_start_routes_to_project_supervisor_endpoint` | ✅ verifies routing |
| 6 | `test_daemon_stop_routes_to_project_supervisor_endpoint` | ✅ verifies routing |
| 7 | `test_daemon_status_routes_to_project_supervisor_endpoint` | ✅ verifies routing |
| 8 | `test_supervisor_project_daemon_start_injects_runtime_root_env` | ✅ verifies env injection |

Coverage gap: no test covers the action-route bug identified above (a false 404 when `project_runtime_root` is omitted from `_get_or_404` in project action routes).

---

### Summary

| Area | Status |
|------|--------|
| `runtime_resolver.py` — state dir fix | ✅ |
| `artifact_reader.py` — read isolation | ✅ |
| `board_service.py` — board isolation + SQLite skip | ✅ |
| `daemon_manager.py` — supervisor routing | ✅ |
| `routes/daemon.py` — project daemon routes | ✅ |
| `routes/tickets.py` — project read routes | ✅ |
| `routes/tickets.py` — project action routes | ❌ **14 calls missing `project_runtime_root`** |
| `supervisor/main.py` — env injection | ✅ |
| Tests | ✅ (no coverage for action-route bug) |

**One blocking defect**: all 14 project-scoped write/action routes in `routes/tickets.py` call `_get_or_404` without `project_runtime_root`, causing false 404s for managed-project tickets not currently in a worktree. The fix is mechanical: add `project_runtime_root=project_runtime_root` to those 14 call sites, and add a regression test.

IMPLEMENTATION_FIX_REQUIRED