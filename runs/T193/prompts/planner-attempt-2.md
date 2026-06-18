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

Now I have a complete understanding of the architecture. Let me write the plan.

---

## Objective

Make ticket boards, runs, logs, and daemon lifecycle fully project-scoped by routing all data reads and daemon writes through the selected project's `project_runtime_root` instead of the shared global SQLite database and runtime directory.

## Included

### Root cause (board shows wrong tickets)

`board_service._try_load_runtime_db()` ignores `project_runtime_root` and always calls `mod.get_db_path()`, which returns a single global `{AI_DEV_FACTORY_RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite`. All projects share one DB; `list_ticket_runtime(db_path)` returns every ticket regardless of which project is queried.

**`services/control_api/services/board_service.py`**
- `_try_load_runtime_db(project_root, project_runtime_root=None)`: when `project_runtime_root` is provided, derive DB path as `project_runtime_root / ".runtime/ai-dev-factory.sqlite"`. If that path does not exist, skip SQLite entirely (do not fall back to the global DB). Load the module and return `(mod, per_project_db_path, False)`.
- `get_board(project_root, repo=None, worktrees_dir=None, project_runtime_root=None)`: add `project_runtime_root` parameter; forward it to `_try_load_runtime_db`.

**`services/control_api/routes/daemon.py`**
- `project_daemon_board`: already receives `project_runtime_root` via `Depends(resolve_project_runtime_root)`. Pass it to `board_service.get_board()`.

---

### Daemon writes to per-project database

When a daemon is started for a project, it must inherit `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}` so it writes ticket state, workers, and issue intake to the project's own SQLite DB.

**`services/control_api/services/daemon_manager.py`**
- `start(project_root, exec_cmd, restart_policy, project_runtime_root=None)`: when `project_runtime_root` is provided, override `AI_DEV_FACTORY_RUNTIME_ROOT` in the subprocess env before `Popen`. Also call `runtime_db.init_runtime_db(project_runtime_root / ".runtime/ai-dev-factory.sqlite")` before spawning so the DB directory and tables exist.
- `restart(project_root, exec_cmd, restart_policy, project_runtime_root=None)`: forward `project_runtime_root` to `start()`.

**`services/control_api/routes/daemon.py`**
- `project_daemon_start`: add `project_runtime_root: Path | None = Depends(resolve_project_runtime_root)`; pass it to `daemon_manager.start()`.
- `project_daemon_restart`: same addition, forward to `daemon_manager.restart()`.

---

### Runs and logs isolation

The project-scoped ticket routes already use `resolve_worktrees_dir(project_root, project_runtime_root=project_runtime_root)` for worktree discovery. However, `artifact_reader.list_tickets(project_root, worktrees_dir=wt_dir)` internally calls `resolve_runs_dir(project_root)` without `project_runtime_root`, relying on the env-var formula `{AI_DEV_FACTORY_RUNTIME_ROOT}/{project_id}/runs`.

**`services/control_api/routes/tickets.py`**
- `project_list_tickets`, `project_get_ticket`, `project_get_state`, `project_get_logs`, and all other project-scoped ticket endpoints: compute `runs_dir = resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)` explicitly and pass it to `artifact_reader` so the path is always authoritative rather than derived from the env formula.

Check that `artifact_reader.list_tickets`, `get_ticket`, `get_ticket_state`, `get_ticket_logs` accept an explicit `runs_dir` parameter (or `project_runtime_root`) and use it. Add/update the parameter if absent.

---

### Audit log per-project DB path

`tickets.py` uses `_db_path(request)` → `request.app.state.db_path`, which is a single global path set at startup. Project-scoped audit log writes on actions (approve, retry, etc.) should use the project's own DB.

**`services/control_api/routes/tickets.py`**
- In all project-scoped action endpoints (`project_approve_plan`, `project_retry`, etc.), derive `db_path = project_runtime_root / ".runtime/ai-dev-factory.sqlite"` when `project_runtime_root` is available instead of `_db_path(request)`.
- Keep the fallback to `_db_path(request)` for legacy routes.

---

### Tests

- `services/control_api/tests/` (existing test suite): add or update board tests to assert that `get_board()` called with a `project_runtime_root` pointing to a temporary per-project DB only returns tickets written to that DB, not tickets in a separate global DB.
- Add a test that `daemon_manager.start()` sets the correct `AI_DEV_FACTORY_RUNTIME_ROOT` env var in the spawned process when `project_runtime_root` is given.

---

## Excluded

- **Legacy routes** (`GET /tickets`, `GET /daemon/board` without `/projects/{id}` prefix): not called by the project-scoped UI; do not migrate.
- **Supervisor multi-project support**: the supervisor's `/daemon/start` and `/daemon/status` calls are project-unaware; fixing supervisor routing is a separate ticket.
- **UI changes**: the frontend already calls all project-scoped routes with the correct `projectId`; no frontend edits required.
- **Project selector / routing changes**: UI project switching and re-polling are already correct.
- **`run_daemon.py` and agent runner tools**: they read `AI_DEV_FACTORY_RUNTIME_ROOT` from the environment, which will be correctly set by the daemon start fix above; no changes needed in those files.

---

## Acceptance criteria

- Selecting `test-ai-dev` in the UI returns a board populated only from `{test-ai-dev runtime root}/.runtime/ai-dev-factory.sqlite`; tickets from `ai-dev-factory` are absent.
- Selecting `ai-dev-factory` in the UI returns its own board; tickets from `test-ai-dev` are absent.
- A daemon started for `test-ai-dev` via `POST /projects/test-ai-dev/daemon/start` spawns a process with `AI_DEV_FACTORY_RUNTIME_ROOT` set to the `test-ai-dev` runtime root, confirmed by checking the process env or the banner written to `daemon.log`.
- `GET /projects/test-ai-dev/tickets` lists only tickets whose run directories live under `test-ai-dev`'s `runs/` path.
- `GET /projects/test-ai-dev/tickets/{ticket_id}/logs` returns the log from `{test-ai-dev runtime root}/runs/{ticket_id}/runtime.log`, not from the ai-dev-factory runtime.
- No regression: `GET /projects/ai-dev-factory/daemon/board` continues to work and returns ai-dev-factory tickets.
- All existing control API tests pass.

---

## Review

# Plan review — daemon lifecycle fix required

The current T193 plan correctly identifies the board/data isolation problem: project boards must read from the selected project's persisted `project_runtime_root`, not from the global ai-dev-factory runtime database.

However, the plan is incomplete for daemon lifecycle.

## Blocking concern

The plan proposes changing `services/control_api/services/daemon_manager.py` so the Control API starts project daemons locally with `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}`.

This is risky and likely wrong when the Control API runs in Docker:

- Control API container paths are not host paths.
- Project roots and runtime roots may require host filesystem access.
- Previous import/bootstrap fixes established that host filesystem operations must go through the supervisor.
- Starting a daemon is a host process lifecycle operation and should not silently happen inside the API container unless that is explicitly intended and tested.

## Required clarification

The plan must explicitly define one of these architectures:

### Option A — Supervisor-backed project daemons preferred

Project daemon start/stop/restart/status/logs go through the supervisor.

Control API responsibilities:

- resolve selected project via registry
- resolve persisted `project_runtime_root`
- call supervisor project-daemon endpoint with `project_id`, `project_root`, `project_runtime_root`, `exec_cmd`, and `restart_policy`
- expose the supervisor response to the UI

Supervisor responsibilities:

- start one daemon per project
- set `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}` for the daemon process
- use `cwd={project_root}` or the correct project clone/worktree path
- write PID/status/logs under that project's runtime root
- never share daemon state between projects

### Option B — Container-local project daemons

If the intended design is to run project daemons inside the Control API container, the plan must justify it and prove all required paths are mounted and mapped correctly.

It must include tests proving that a project daemon for an imported host project can read/write the selected project runtime without leaking to ai-dev-factory.

## Required plan changes

- Do not leave project daemon lifecycle half-scoped.
- Board/runs/logs isolation and daemon process isolation must use the same `project_runtime_root` source of truth.
- The plan must state whether `project_daemon_start`, `project_daemon_stop`, `project_daemon_restart`, `project_daemon_status`, and project daemon logs are supervisor-backed or container-local.
- If supervisor-backed, include supervisor endpoint changes in scope.
- If container-local, include explicit Docker path/mount validation and tests.

## Acceptance additions

- Starting a daemon for `test-ai-dev` does not start or mutate the ai-dev-factory daemon.
- Stopping a daemon for `test-ai-dev` does not stop the ai-dev-factory daemon.
- Daemon PID/status/log path is under `test-ai-dev`'s persisted runtime root.
- The daemon process environment contains `AI_DEV_FACTORY_RUNTIME_ROOT={test-ai-dev project_runtime_root}`.
- The implementation has a test for the selected daemon architecture.

## Review verdict

PLAN_FIX_REQUIRED until daemon lifecycle architecture is clarified and included.

---

## Instructions de fix

# Plan fix — clarify and include project daemon architecture

The current T193 plan correctly scopes board/runs/log reads to the selected project's `project_runtime_root`, but the daemon lifecycle part is not safe enough.

## Required fix

The plan must explicitly choose and implement a project daemon architecture.

Preferred architecture: supervisor-backed project daemons.

Control API should not silently spawn project daemons locally from inside the API container unless that is explicitly intended and proven safe. Starting/stopping daemon processes is a host process lifecycle operation and previous project import/bootstrap work established that host filesystem operations must go through the supervisor.

## Required changes to the plan

### Control API responsibilities

For project daemon start/stop/restart/status/logs, Control API must:

1. Resolve selected `project_id` from the route.
2. Resolve `project_root` from the registry.
3. Resolve persisted `project_runtime_root` from the registry.
4. Call the supervisor project-daemon endpoint with:

```json
{
  "project_id": "<project_id>",
  "project_root": "<project_root>",
  "project_runtime_root": "<project_runtime_root>",
  "exec_cmd": "<exec_cmd>",
  "restart_policy": "<restart_policy>"
}
```

5. Return the supervisor response to the UI.

### Supervisor responsibilities

Supervisor must:

1. Keep one daemon state/process per project.
2. Start daemon with:

```text
AI_DEV_FACTORY_RUNTIME_ROOT=<project_runtime_root>
```

3. Use the correct project cwd, usually `project_root` or the managed clone path if the project has been cloned into its runtime.
4. Write PID/status/log files under the selected project's runtime root.
5. Never mutate the ai-dev-factory daemon when a different project daemon is started/stopped.

### Board/runs/logs responsibilities

Board, run, ticket and log reads must continue to use the persisted `project_runtime_root` and must not fall back to the global ai-dev-factory runtime when a project is selected.

## Acceptance additions

- Starting daemon for `test-ai-dev` creates/updates only `test-ai-dev` daemon state.
- Stopping daemon for `test-ai-dev` does not stop `ai-dev-factory` daemon.
- Project daemon logs/PID/status live under `test-ai-dev`'s persisted runtime root.
- The daemon process env includes `AI_DEV_FACTORY_RUNTIME_ROOT=<test-ai-dev project_runtime_root>`.
- The implementation includes tests for the chosen daemon architecture.
- No implementation path starts project daemons from Control API inside Docker unless a test proves the path/mount model is valid.

## Review verdict

PLAN_FIX_REQUIRED until this architecture is included in `runs/T193/plan.md`.