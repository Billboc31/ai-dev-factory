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



# T181 — T181 - Add existing project bootstrap and per-project agent runtime management

**Source**: GitHub Issue #215

## Description

# Objective

Transform AI Dev Factory from an environment-centric tool into a multi-project workspace capable of bootstrapping existing projects and managing isolated per-project agent runtimes.

The immediate focus is NOT deployment.

The focus is:
- project bootstrap
- project management UI
- ticket/dev workflow
- per-project supervisor/daemon isolation

Deployment/runtime sandbox orchestration can come later.

---

# MVP Scope

## 1. Multi-project workspace UI

Add a true project-centric UI.

Required:

- Projects home/dashboard
- Sidebar project navigation
- Open existing project
- Import existing project
- Create new project (placeholder flow acceptable initially)
- Per-project dashboard

Each project should expose:

- tickets/issues
- branches/worktrees
- agents
- logs
- runtime state
- settings

---

# 2. Existing project bootstrap

Add a bootstrap flow for existing repositories/projects.

Flow:

```text
Import existing project
→ choose local repo/folder
→ detect stack
→ generate ai-dev-factory metadata/config
→ initialize project runtime structure
→ enable ticket/agent workflow
```

Required bootstrap outputs:

- project config
- runtime directory structure
- worktrees directory
- logs/state directories
- minimal supervisor metadata
- project registration in workspace

Out of scope initially:

- Traefik
- deploy environments
- healthchecks
- production runtime deployment

---

# 3. Per-project agent runtime isolation

Each project must have isolated:

- supervisor
- daemon
- worktrees
- logs
- state
- PID files
- locks

No project may reuse another project's runtime directories.

Required:

```text
1 supervisor per project
1 daemon per project
```

with runtime roots derived from the project.

Example:

```text
projects/
  personal-rag/
    runtime/
      logs/
      state/
      worktrees/
```

---

# 4. Ticket/dev workflow

The imported project must immediately support:

- issue creation
- branch creation
- ticket/TXXX-* naming
- worktree creation
- Claude/Coder execution
- commit/push/PR workflow

without requiring deployment support.

---

# Important architecture goal

Move from:

```text
Environment-centric architecture
```

to:

```text
Project-centric architecture
```

Environments should eventually become derived runtime instances of a project, not the primary top-level entity.

---

# Acceptance criteria

- Workspace supports multiple projects
- Existing local projects can be imported
- Imported projects appear in the UI
- Imported projects get isolated runtime directories
- Each project can run its own supervisor and daemon
- Ticket/dev workflow works for imported projects
- Worktrees/logs/state are isolated per project
- No deployment/Traefik dependency is required for the MVP

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Here is the implementation plan:

---

## Objective

Transform AI Dev Factory into a multi-project workspace by adding a persistent workspace registry, an existing-project bootstrap flow, per-project isolated runtime directory trees, per-project daemon management in the supervisor, and a project-centric frontend with an import wizard.

## Included

### Backend — workspace registry persistence
- `services/control_api/services/project_registry.py`: add `register(project_id, root)` and `unregister(project_id)` methods that persist to `{RUNTIME_ROOT}/workspace.json`; add `load_from_workspace_file(runtime_root)` classmethod to rehydrate from disk on API startup; keep the existing scan-based `_scan()` fallback when no workspace file exists.

### Backend — project bootstrap service
- `services/control_api/services/project_bootstrap.py` (new): `bootstrap(project_root, project_id, runtime_root) -> BootstrapResult` that (1) validates the path is a git repo, (2) creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/`, (3) writes `.ai-dev-factory/project.yml` into the target repo (name, stack, bootstrapped_at) if absent, (4) registers the project, (5) returns `BootstrapResult`.

### Backend — stack detector
- `services/control_api/services/stack_detector.py` (new): `detect_stack(project_root) -> str` returning `python | node | go | rust | unknown` from file presence heuristics.

### Backend — per-project runtime resolver
- `services/control_api/services/runtime_resolver.py`: add `resolve_project_runtime_root(project_id)` → `{RUNTIME_ROOT}/projects/{project_id}`; add optional `project_id` to `resolve_runs_dir / resolve_logs_dir / resolve_state_dir / resolve_worktrees_dir` so they return project-nested paths when both args are provided.

### Backend — API routes
- `services/control_api/routes/projects.py`: add `GET /projects`, `POST /projects/import`, `DELETE /projects/{project_id}`.

### Backend — schemas
- `services/control_api/models/schemas.py`: add `ProjectImportRequest`, `BootstrapResult`; extend `ProjectInfo` with `runtime_root` and `stack`.

### Backend — control_api startup
- `services/control_api/main.py`: prefer `load_from_workspace_file()` on startup; fall back to directory scan.

### Supervisor — per-project daemon management
- `services/supervisor/main.py`: add `_per_project_daemon_states` and `_per_project_daemon_procs` dicts; add per-project PID/log path helpers; add `_spawn_project_daemon(project_id, project_root, exec_cmd)`; add `POST /projects/{id}/daemon/start`, `GET /projects/{id}/daemon/status`, `POST /projects/{id}/daemon/stop` following the existing analysis/scripts endpoint pattern; include per-project PIDs in the monitor loop.

### Frontend
- `apps/dashboard/src/pages/ProjectsPage.jsx` (new): projects home with import button.
- `apps/dashboard/src/pages/ImportProjectPage.jsx` (new): import wizard (path → validate → bootstrap → navigate).
- `apps/dashboard/src/api/projects.js` (new): `listProjects()`, `importProject()`, `deleteProject()`.
- `apps/dashboard/src/App.jsx`: add `/projects` and `/import-project` routes; add "Projects" nav link.

## Excluded

- Traefik, deploy environments, healthcheck pipelines.
- URL-scheme refactor to `/projects/:id/*` — context/query-param routing is sufficient for the MVP.
- Per-project daemon auto-start on bootstrap — start remains explicit.
- SQLite schema partitioning.
- Worktree collision prevention for duplicate ticket IDs across projects.
- "Create new project" beyond a placeholder button.
- Migration of the existing single-project runtime layout.

## Acceptance criteria

- `GET /projects` returns all registered projects.
- `POST /projects/import` with a valid git repo creates the full runtime directory tree, writes `.ai-dev-factory/project.yml`, persists to `workspace.json`, returns `200 BootstrapResult`.
- `POST /projects/import` with a non-git path or duplicate `project_id` returns `4xx`.
- `GET /projects` includes the newly imported project after a successful import.
- `POST /projects/{id}/daemon/start` on the supervisor spawns a daemon with `cwd` set to the project root; the PID file lands at `{runtime_root}/projects/{id}/runs/daemon.pid`.
- Two projects can have simultaneous active daemons without PID file collision.
- `ProjectsPage` renders with the project list and an "Import project" button.
- `ImportProjectPage` completes a bootstrap and the project appears in the list on success.
- Existing tests pass without modification.

---

## Review

# T181 — Plan Review

## Verdict

The plan is good and aligned with the intended pivot: move AI Dev Factory from an environment-centric/deployer-centric tool toward a project-centric multi-project workspace.

The scope is correctly focused on:

- importing existing projects;
- registering projects in a workspace;
- creating isolated per-project runtime directories;
- starting/stopping one supervisor/daemon runtime per project;
- enabling the ticket/dev loop without requiring deployment.

This is the right foundation for bootstrapping an existing project such as the personal RAG project and using AI Dev Factory to work on it.

## Strong points

- Deployment, Traefik and healthchecks are explicitly out of scope.
- The plan introduces a persistent workspace registry instead of relying only on directory scanning.
- Imported projects get their own runtime tree.
- Per-project daemon isolation is addressed at the supervisor level.
- The UI starts with a simple Projects page and Import wizard, which is the right MVP.
- The ticket/dev workflow remains part of the acceptance criteria.

## Main risks

### Project ID safety

`project_id` must be strictly normalized and validated before it is used in filesystem paths.

Without strict validation, runtime paths can become unsafe or inconsistent.

### Runtime ownership

The implementation must avoid silently reusing the global AI Dev Factory runtime directories.

Every imported project must resolve to its own runtime root.

### Daemon lifecycle complexity

Per-project daemon state must not reuse the existing single-daemon globals accidentally. The implementation should make it obvious whether a daemon belongs to the global/dev runtime or to a specific project.

### Ticket collisions

The plan excludes duplicate ticket collision prevention across projects. That is acceptable for the MVP, but it should be tracked as a follow-up because ticket IDs such as `T181` may exist in several projects.

## Recommendation

Proceed with the plan, but add a small required fix before implementation: strict `project_id` normalization/validation and explicit runtime-root logging for every per-project daemon operation.

---

## Instructions de fix

# Required Plan Fix — Project ID Safety and Runtime Isolation

## Problem

The current T181 plan is globally correct, but it needs two mandatory safeguards before implementation:

1. strict `project_id` normalization/validation;
2. explicit per-project runtime isolation diagnostics.

Because `project_id` is used to derive filesystem paths, it must never accept arbitrary user input.

## Required additions to the plan

### 1. Project ID normalization

Add a helper such as:

```text
normalize_project_id(name_or_path) -> project_id
```

Rules:

- lowercase only;
- allowed characters: `a-z`, `0-9`, `-`, `_`;
- reject `/`, `\\`, `.`, `..`, whitespace-only values, empty values;
- collapse unsupported characters to `-` only when auto-generating from a project name;
- for explicit user-provided `project_id`, reject invalid input instead of silently rewriting it;
- enforce a reasonable max length.

### 2. Path containment validation

Before creating runtime directories, validate:

```text
project_runtime_root = {RUNTIME_ROOT}/projects/{project_id}
```

and ensure:

- it is absolute;
- it remains inside `{RUNTIME_ROOT}/projects`;
- it does not escape via symlinks or `..`;
- duplicate project IDs are rejected.

### 3. Runtime isolation logging

Every per-project daemon operation must log:

```text
project_id=<id>
project_root=<repo path>
project_runtime_root=<runtime path>
runs_dir=<...>
logs_dir=<...>
state_dir=<...>
worktrees_dir=<...>
daemon_pid_path=<...>
```

This is required to avoid repeating the previous confusion between global runtime, environment runtime and project runtime.

### 4. Supervisor endpoint validation

The supervisor endpoints:

```text
POST /projects/{id}/daemon/start
GET /projects/{id}/daemon/status
POST /projects/{id}/daemon/stop
```

must validate that the project exists in the workspace registry before starting or stopping any daemon.

They must not accept arbitrary paths from the request body without registry validation.

### 5. Follow-up ticket

Create or mention a follow-up for ticket/worktree collision prevention across projects.

This can stay out of T181 implementation, but the limitation must be documented clearly.

## Acceptance criteria additions

- invalid project IDs are rejected with 4xx;
- project runtime root cannot escape the workspace runtime root;
- importing the same project ID twice returns 4xx;
- per-project daemon logs show all resolved runtime paths;
- supervisor daemon endpoints require a registered project;
- no per-project daemon operation uses the global runtime directories accidentally.