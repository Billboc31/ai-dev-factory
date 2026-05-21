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



# T124 — T124 — Multi-project runtime boards and project isolation

**Source**: GitHub Issue #87

## Description

# Objective

Introduce first-class multi-project support in the dashboard and runtime architecture so multiple independent AI-managed projects can be orchestrated from a single control surface.

## Included

- Add a project abstraction to the runtime model.
- Introduce project-aware runtime roots and worktree isolation.
- Add a project selector/sidebar in the dashboard.
- Display separate boards per project.
- Separate:
  - tickets
  - runtime state
  - daemon status
  - workers
  - logs
  - queue/intake
  - runtime artifacts
- Add backend APIs/services for project discovery and project-scoped runtime operations.
- Add frontend routing/state for project-aware navigation.
- Support the existing `ai-dev-factory` project as the initial/default project.
- Add tests for project isolation and project-scoped runtime queries.

## Excluded

- Multi-user authentication.
- Cross-project orchestration.
- Distributed remote runtimes.
- Kubernetes/container orchestration.
- SaaS billing/account management.
- Full plugin architecture.

## Acceptance criteria

- Dashboard can display multiple independent projects.
- Each project has isolated runtime state and worktrees.
- Switching project updates the visible board/runtime context.
- Runtime actions only affect the selected project.
- Existing `ai-dev-factory` workflows continue to function.
- Project-scoped runtime APIs are covered by tests.
- Runtime garbage files are not shared across project runtimes.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have a complete picture of the codebase. Let me write the plan.

## Objective

Introduce project-scoped backend APIs and a project-aware dashboard so multiple independent `ai-dev-factory` projects can be orchestrated from a single control surface, with each project's runtime state, daemon, workers, tickets, and board fully isolated.

## Included

**Backend — project registry service**

- `services/control_api/services/project_registry.py` (new): discovers projects by scanning `AI_DEV_FACTORY_PROJECTS_ROOT` for subdirectories that are git repositories containing an `ai/` directory; maps `project_id` (dirname) → absolute `project_root`; exposes `list_projects()` and `resolve(project_id) → Path | None`.
- `services/control_api/main.py`: accept `--projects-root` CLI flag and `AI_DEV_FACTORY_PROJECTS_ROOT` env var; store `ProjectRegistry` instance in `app.state.registry`; fall back to existing single-project mode (`app.state.project_root`) when the env var is absent, preserving backward compatibility.

**Backend — project-scoped routing**

- `services/control_api/routes/projects.py` (new): `GET /projects` (list all discovered projects with `name`, `root`, `tickets_count`); all existing `daemon`, `tickets`, and `project_map` routers re-mounted under `/projects/{project_id}/` using a FastAPI `APIRouter` prefix.
- `services/control_api/routes/daemon.py`, `routes/tickets.py`, `routes/project_map.py`, `routes/issues.py`: replace the direct read of `request.app.state.project_root` with a shared FastAPI dependency `get_project_root(project_id: str, request: Request) → Path` that resolves via the registry; unknown `project_id` returns HTTP 404.
- `services/control_api/routes/providers.py`: update `GET /projects` to delegate to the registry instead of returning the hardcoded single-project list.
- `services/control_api/models/schemas.py`: extend `ProjectInfo` with `active_workers_count: int` field.

**Frontend — project selector**

- `apps/dashboard/src/hooks/useProjects.js` (new): fetches `/api/projects`, returns `{ projects, loading, error }` with simple refresh.
- `apps/dashboard/src/components/ProjectSidebar.jsx` (new): renders the project list from `useProjects`; highlights the currently active project; emits `onSelect(projectId)`.
- `apps/dashboard/src/App.jsx`: add `/:projectId` prefix to all existing routes (`/:projectId/board`, `/:projectId/tickets`, `/:projectId/tickets/:id`, `/:projectId/daemon`, `/:projectId/project-map`, `/:projectId/mapper-activity`); render `ProjectSidebar`; replace the hardcoded "ai-dev-factory" span in the header with the active project name from the URL param; add root `/` redirect to the first project returned by `GET /api/projects`.

**Frontend — API clients**

- `apps/dashboard/src/api/daemon.js`, `apps/dashboard/src/api/tickets.js`, `apps/dashboard/src/api/projectMap.js`: add a `projectId` parameter to every exported function; rewrite all URL strings from `/api/daemon/...` → `/api/projects/{projectId}/daemon/...` (and equivalently for tickets and project-map).

**Tests**

- `tests/test_project_registry.py` (new): unit tests for `project_registry.py` — discover valid projects, ignore non-git subdirectories, handle missing `projects_root`, handle empty directory, resolve known and unknown project_ids.
- `tests/test_project_scoped_routes.py` (new): integration tests using two temporary project roots with distinct `runs/` and `state.json` fixtures; assert `GET /projects/{project_id}/tickets` returns only that project's tickets; assert `GET /projects/{project_id}/daemon/board` returns only that project's board; assert project A data does not appear in project B responses.
- `apps/dashboard/tests/ProjectSidebar.test.jsx` (new): renders project list, highlights active project, fires `onSelect` on click.
- Update `apps/dashboard/tests/api.test.js` and existing page tests to use project-prefixed URLs.

## Excluded

- Multi-user authentication or per-user project access control.
- Cross-project orchestration (shared workers, cross-project dependencies).
- Distributed or remote runtimes (Kubernetes, remote SSH hosts).
- SaaS billing or account management.
- Plugin or extension architecture.
- Changes to the daemon CLI itself or its internal state machine — the daemon remains a per-project process invoked unchanged; only the API layer learns to dispatch to multiple daemons.
- Responsive/mobile layout changes beyond accommodating the sidebar in the existing layout.
- Migrating existing `runs/` state files when `AI_DEV_FACTORY_PROJECTS_ROOT` is newly configured.

## Acceptance criteria

- `GET /api/projects` returns a JSON list containing at least the `ai-dev-factory` project with correct `tickets_count`.
- `GET /api/projects/ai-dev-factory/daemon/status` returns the same data as the current `GET /api/daemon/status` for that project.
- `GET /api/projects/ai-dev-factory/daemon/board` returns only tickets under the `ai-dev-factory` `runs/` directory.
- With two projects A and B configured (separate `runs/` dirs, each with a distinct ticket), `GET /api/projects/A/tickets` returns A's ticket only, and `GET /api/projects/B/tickets` returns B's ticket only — no cross-contamination.
- `GET /api/projects/unknown-project` returns HTTP 404.
- Dashboard sidebar lists all discovered projects.
- Clicking a project in the sidebar navigates to `/:projectId/board` and all visible data refreshes to that project.
- Browser URL path reflects the selected project on every page (`/:projectId/board`, `/:projectId/tickets`, etc.).
- Navigating to `/` redirects to the first project's board.
- Header displays the current project name instead of the hardcoded string "ai-dev-factory".
- `pytest tests/test_project_registry.py tests/test_project_scoped_routes.py` passes with no failures.
- `npm test` in `apps/dashboard/` passes with no failures.
- All existing `pytest tests/` tests continue to pass (backward-compatibility mode, no `AI_DEV_FACTORY_PROJECTS_ROOT` set).

---

## Review

# Plan review — T124

Decision: PLAN_FIX_REQUIRED

The plan is coherent but too large for one safe ticket.

Please reduce T124 to a V1 focused on read-only project discovery and UI selection.

V1 should include:

- project registry service
- GET /api/projects
- default ai-dev-factory project
- dashboard project selector or sidebar
- current project name visible in the UI
- tests for project discovery and /api/projects

V1 should exclude:

- remounting all routers under /projects/{project_id}
- rewriting all frontend API clients
- project-scoped daemon actions
- project-scoped ticket actions
- runtime data migration
- multi-daemon orchestration

Existing /api/daemon, /api/tickets and /api/project-map routes must stay unchanged in V1.

Follow-up ticket:
project-scoped APIs and actions can be implemented later once project discovery and UI selection are stable.

---

## Instructions de fix

# Plan fix request — T124

The original plan is too large for one safe ticket.

Rewrite T124 as a smaller V1.

## V1 objective

Introduce read-only project discovery and a dashboard project selector while keeping existing single-project runtime APIs unchanged.

## Include in V1

- Add project registry service.
- Add GET /api/projects.
- Support existing ai-dev-factory as the default project.
- Add dashboard project selector/sidebar.
- Display current selected project in the UI.
- Keep existing /api/daemon, /api/tickets and /api/project-map routes unchanged.
- Add tests for project discovery and /api/projects.
- Add minimal frontend test for project selector if practical.

## Exclude from V1

- Do not remount all routers under /projects/{project_id}.
- Do not rewrite all frontend API clients.
- Do not make daemon/tickets/actions project-scoped yet.
- Do not migrate runtime data.
- Do not implement multi-daemon orchestration.

## Acceptance criteria

- Dashboard shows project selector with ai-dev-factory.
- Existing daemon/ticket actions continue to work.
- GET /api/projects returns discovered/default projects.
- Tests cover project discovery and backward compatibility.