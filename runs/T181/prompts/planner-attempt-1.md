## Objective

Transform AI Dev Factory into a multi-project workspace by adding a persistent workspace registry, an existing-project bootstrap flow, per-project isolated runtime directory trees, per-project daemon management in the supervisor, and a project-centric frontend with an import wizard.

## Included

### Backend — workspace registry persistence
- `services/control_api/services/project_registry.py`: add `register(project_id, root)` and `unregister(project_id)` methods that persist to `{RUNTIME_ROOT}/workspace.json`; add `load_from_workspace_file(runtime_root)` classmethod to rehydrate from disk on API startup; keep the existing scan-based `_scan()` fallback when no workspace file exists.

### Backend — project bootstrap service
- `services/control_api/services/project_bootstrap.py` (new): `bootstrap(project_root: Path, project_id: str, runtime_root: Path) -> BootstrapResult` that (1) validates `project_root` is a git repo, (2) creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/`, (3) writes `.ai-dev-factory/project.yml` into the target repo (name, stack, bootstrapped_at) if not already present, (4) registers the project in the workspace registry, (5) returns `BootstrapResult`.

### Backend — stack detector
- `services/control_api/services/stack_detector.py` (new): `detect_stack(project_root: Path) -> str` returning `python | node | go | rust | unknown` based on presence of `pyproject.toml`, `requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`.

### Backend — per-project runtime resolver
- `services/control_api/services/runtime_resolver.py`: add `resolve_project_runtime_root(project_id: str) -> Path | None` returning `{AI_DEV_FACTORY_RUNTIME_ROOT}/projects/{project_id}` when the env var is set; add optional `project_id` parameter to `resolve_runs_dir`, `resolve_logs_dir`, `resolve_state_dir`, `resolve_worktrees_dir` — when both `project_id` and `RUNTIME_ROOT` are provided, return paths nested under `projects/{project_id}/`.

### Backend — API routes
- `services/control_api/routes/projects.py`: add `GET /projects` (list all registered projects with per-project runtime status); add `POST /projects/import` accepting `{ "path": str, "project_id": str | null }` that validates the path, calls `project_bootstrap.bootstrap()`, returns `BootstrapResult`; add `DELETE /projects/{project_id}` that unregisters a project without deleting files.

### Backend — schemas
- `services/control_api/models/schemas.py`: add `ProjectImportRequest(path: str, project_id: str | None)`, `BootstrapResult(project_id: str, project_root: str, runtime_root: str, stack: str, config_path: str, created_dirs: list[str])`; extend `ProjectInfo` with `runtime_root: str | None` and `stack: str | None`.

### Backend — control_api startup
- `services/control_api/main.py` (wherever `ProjectRegistry` is instantiated): on startup prefer `load_from_workspace_file(runtime_root)` if the file exists; fall back to directory scan.

### Supervisor — per-project daemon management
- `services/supervisor/main.py`: add `_per_project_daemon_states: dict[str, DaemonState]` and `_per_project_daemon_procs: dict[str, subprocess.Popen]`; add `_project_daemon_pid_path(project_id)` → `{runtime_root}/projects/{project_id}/runs/daemon.pid`; add `_project_daemon_log_path(project_id)` → `{runtime_root}/projects/{project_id}/logs/daemon.log`; add `_spawn_project_daemon(project_id, project_root, exec_cmd)` (spawns `run_daemon.py` with `cwd=project_root`, `--worktrees-dir` pointing to project-scoped dir); add FastAPI endpoints `POST /projects/{project_id}/daemon/start`, `GET /projects/{project_id}/daemon/status`, `POST /projects/{project_id}/daemon/stop` following the existing analysis/scripts pattern; include per-project daemon PIDs in the `_monitor_daemon` asyncio loop.

### Frontend — projects home
- `apps/dashboard/src/pages/ProjectsPage.jsx` (new): lists all registered projects (name, stack, ticket count, runtime status); includes "Import project" button linking to the import page and a placeholder "Create project" button.

### Frontend — import wizard
- `apps/dashboard/src/pages/ImportProjectPage.jsx` (new): form with `path` (local filesystem path) and optional `project_id`; on submit calls `POST /projects/import`; shows step feedback (validating → bootstrapping → registered); on success navigates to the project's tickets view.

### Frontend — API client
- `apps/dashboard/src/api/projects.js` (new): `listProjects()`, `importProject(path, projectId)`, `deleteProject(projectId)` using the existing axios wrapper pattern from `apps/dashboard/src/api/`.

### Frontend — routing
- `apps/dashboard/src/App.jsx`: add `<Route path="/projects" element={<ProjectsPage />} />` and `<Route path="/import-project" element={<ImportProjectPage />} />`; add "Projects" link to the `Nav` bar.

## Excluded

- Traefik configuration, deploy environments, healthcheck pipelines.
- URL-level project scoping (`/projects/:id/tickets` URL scheme) — existing per-project routing via context/query-param is sufficient for MVP; URL-scheme refactor is a separate concern.
- Per-project daemon auto-start on bootstrap — daemon start remains explicit from the UI.
- SQLite schema partitioning — ticket state remains filesystem-based.
- Worktree collision prevention for shared ticket IDs across projects.
- `create new project` beyond a placeholder button in the UI.
- Migration of the existing single-project runtime layout.

## Acceptance criteria

- `GET /projects` returns all registered projects (at minimum the pre-existing ones discovered on startup).
- `POST /projects/import` with a valid local git repo path creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/`, writes `.ai-dev-factory/project.yml` into the repo, persists the entry to `workspace.json`, and returns `200 BootstrapResult`.
- `POST /projects/import` with a non-git path returns `4xx`; a duplicate `project_id` returns `4xx`.
- After import, `GET /projects` lists the newly added project.
- `POST /projects/{project_id}/daemon/start` on the supervisor spawns a daemon with `cwd` set to the project root and `--worktrees-dir` pointing to `{runtime_root}/projects/{project_id}/worktrees`; the PID file lands at `{runtime_root}/projects/{project_id}/runs/daemon.pid`.
- Two different projects can have active daemons simultaneously with no PID file collision.
- `ProjectsPage` renders in the browser showing registered projects and an "Import project" button.
- `ImportProjectPage` successfully bootstraps a valid local repo and the new project appears in the projects list on completion.
- Existing tests pass without modification.

---

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