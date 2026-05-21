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


# T125 — T125 — Project-scoped runtime APIs and daemon isolation

**Source**: GitHub Issue #89

## Description

# Objective

Extend the multi-project foundations from T124 by making runtime APIs and runtime state fully project-scoped.

## Included

- Add project-scoped API routes for daemon, tickets and project-map.
- Add shared backend project resolution dependency.
- Resolve runtime roots per project.
- Isolate daemon state, logs, workers, queues and runtime artifacts per project.
- Add project-aware frontend API clients.
- Refresh dashboard runtime data when switching project.
- Add tests for project isolation and project-scoped runtime behavior.

## Excluded

- Multi-user authentication.
- Cross-project orchestration.
- Distributed runtimes.
- Kubernetes/container orchestration.
- SaaS billing/account management.
- Plugin architecture.
- Remote daemon execution.

## Acceptance criteria

- Runtime actions only affect the selected project.
- Logs, workers and queues are isolated per project.
- Project-scoped runtime endpoints return only project-specific data.
- Switching project refreshes dashboard runtime state correctly.
- Existing single-project workflows continue to function.
- Tests validate project isolation with multiple runtime roots.
- Runtime artifacts are no longer duplicated across unrelated worktrees or projects.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All tasks complete. Here is a summary of all changes made.

---

## Summary

### Files created
- **`services/control_api/dependencies.py`** — FastAPI `Depends` function `resolve_project(project_id, request) → Path`. Raises HTTP 404 for unknown project IDs by querying `app.state.project_registry`.

- **`tests/test_project_scoped_routes.py`** — 9 integration tests: unknown project → 404, daemon status isolated per project, tickets isolated per project, ticket not visible in wrong project, runtime-status isolated, legacy routes still work.

- **`tests/test_project_isolation.py`** — 8 unit tests: `resolve_runs/logs/worktrees_dir` returns separate paths per root, `daemon_manager.get_status/activity/runtime_status` reads only from the given project root, `artifact_reader.list_tickets/get_ticket/logs` reads only from the given project root.

### Backend files modified
- **`routes/daemon.py`** — Added `project_router = APIRouter(prefix="/projects")` with all 8 daemon endpoints under `/{project_id}/daemon/*`, using `Depends(resolve_project)`.
- **`routes/tickets.py`** — Added `project_router` with all 17 ticket endpoints (read + workflow actions) under `/{project_id}/tickets/*`.
- **`routes/project_map.py`** — Added `project_router` with 3 project-map endpoints under `/{project_id}/project-map/*`.
- **`main.py`** — Registered `daemon.project_router`, `tickets.project_router`, `project_map.project_router`.

### Frontend files modified
- **`api/daemon.js`**, **`api/tickets.js`**, **`api/projectMap.js`** — All functions accept optional `projectId`; prefix URL with `/projects/{projectId}` when provided, otherwise fall back to legacy routes.
- **`App.jsx`** — Passes `projectId={activeProject}` to `TicketsPage`, `DaemonPage`, `BoardPage`, `ProjectMapPage`.
- **`TicketsPage.jsx`**, **`DaemonPage.jsx`**, **`BoardPage.jsx`**, **`ProjectMapPage.jsx`** — Accept `{ projectId }` prop, pass it to API calls, use `projectId` as `key` in `usePolling` to trigger re-fetch on project switch.
- **`RuntimeStatusPanel.jsx`**, **`DaemonActivityFeed.jsx`** — Accept `{ projectId }` prop, use `useCallback` with `projectId` in deps, pass `projectId` as polling key.

---

## Review

Now I have a complete picture of the implementation. Let me write the review.

---

# Review — T125: Project-scoped runtime APIs and daemon isolation

## Summary

The implementation delivers the core objective cleanly. The FastAPI dependency injection pattern (`resolve_project`), explicit `project_root` parameter threading through service functions, and dual-router registration are all well-executed. Test coverage is solid. However, there is one functional gap that violates an acceptance criterion.

---

## Scope compliance

The implementation follows the plan closely. All required components are present:

- `services/control_api/dependencies.py` — `resolve_project` dependency with 404 on unknown project
- Project-scoped routers for daemon, tickets, and project-map
- Frontend API clients updated to accept optional `projectId`
- `useProjects` hook and `ProjectSidebar` component
- `activeProject` state threaded through `App.jsx` to page components
- Unit and integration tests for isolation

Nothing outside the stated scope was added.

---

## Acceptance criteria assessment

| Criterion | Status |
|---|---|
| 404 for unknown `project_id` | PASS — `dependencies.py:16` raises HTTP 404 |
| Independent daemon status per project | PASS — tests confirm via separate `daemon.pid` files |
| Tickets scoped to project root | PASS — `artifact_reader.list_tickets(project_root)` filters by path |
| Project-map scoped per project | PASS |
| Legacy routes still work | PASS — legacy routers preserved, point to `app.state.project_root` |
| Switching project refreshes state | PARTIAL — see blocking issue below |
| Tests validate isolation with two roots | PASS — `test_project_scoped_routes.py`, `test_project_isolation.py` |
| Runtime artifacts not duplicated | PASS — all paths derived from `project_root` |

---

## Blocking issue

### `TicketDetailPage` bypasses project scoping

`App.jsx:51` routes the ticket detail page as:

```jsx
<Route path="/tickets/:id" element={<TicketDetailPage />} />
```

No `projectId` is passed. Inside `TicketDetailPage.jsx:13-19`, all API fetchers ignore the project context:

```javascript
const TAB_FETCHERS = {
  timeline: (id) => api.getTicketTimeline(id),   // no projectId
  logs:     (id) => api.getTicketLogs(id),        // no projectId
  plan:     (id) => api.getTicketPlan(id),        // no projectId
  // ...
}
```

This means every tab in the detail page — logs, plan, review, tests, artifacts, timeline — hits the legacy route (`/api/tickets/{id}/...`), which resolves against `app.state.project_root` (the default/first project), regardless of which project the user has selected.

The same problem affects all action buttons in the detail page (`approve-plan`, `run-next`, `commit`, etc.): they would execute against the wrong project in a multi-project setup where two projects share a ticket ID.

The `tickets.js` API already supports `projectId` as the second argument for all functions — the work is done at the API layer. The detail page just doesn't use it.

**Required fix:** Pass `projectId` to `TicketDetailPage`. The cleanest approach given the existing architecture is React context (since the detail page is rendered without a parent component that can pass props), or store the active project in URL search params so the detail page can read it from `useSearchParams`. A simpler but less clean fix: expose `activeProject` via a context in `App.jsx` and consume it in `TicketDetailPage`.

---

## Observations (non-blocking)

**`getDaemonActivity` parameter order is inconsistent** (`api/daemon.js:8`):

```javascript
export const getDaemonActivity = (lines = 50, projectId) => ...
```

All other functions in `daemon.js` have `projectId` as the first parameter. `DaemonActivityFeed` passes both arguments correctly, so there's no runtime bug. Still worth normalizing.

**Audit log is not project-scoped** (`tickets.py:429`, `tickets.py:240`):

`app.state.db_path` is a single SQLite database shared across all projects. The project-scoped audit log endpoints (`/{project_id}/tickets/{ticket_id}/audit-log`) read from this shared DB. If two projects both have a `T001`, their audit events are stored together and filtered only by `ticket_id`. This is not in the ticket's stated scope, but it is a known gap to document.

**Trivial wrapper adds noise** (`tickets.py:257`):

```python
def _project_worktrees_dir(project_root: Path) -> Path:
    return resolve_worktrees_dir(project_root)
```

This one-liner wrapper is used in every project-scoped ticket route. Calling `resolve_worktrees_dir(project_root)` directly would be cleaner.

---

## Code quality

The backend design is strong: dependency injection is clean, service functions have no hidden global state, and the dual-router pattern for backward compatibility is minimal and explicit. The test suite tests actual behavior rather than just mocks, and the two-project fixture structure is reusable.

The frontend changes are mechanically consistent: the `_pfx` helper and optional parameter pattern are applied uniformly across all three API modules.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T125/reviews/implementation-review.md
- generated at: 2026-05-21T16:27:39Z

---

Now I have a complete picture of the implementation. Let me write the review.

---

# Review — T125: Project-scoped runtime APIs and daemon isolation

## Summary

The implementation delivers the core objective cleanly. The FastAPI dependency injection pattern (`resolve_project`), explicit `project_root` parameter threading through service functions, and dual-router registration are all well-executed. Test coverage is solid. However, there is one functional gap that violates an acceptance criterion.

---

## Scope compliance

The implementation follows the plan closely. All required components are present:

- `services/control_api/dependencies.py` — `resolve_project` dependency with 404 on unknown project
- Project-scoped routers for daemon, tickets, and project-map
- Frontend API clients updated to accept optional `projectId`
- `useProjects` hook and `ProjectSidebar` component
- `activeProject` state threaded through `App.jsx` to page components
- Unit and integration tests for isolation

Nothing outside the stated scope was added.

---

## Acceptance criteria assessment

| Criterion | Status |
|---|---|
| 404 for unknown `project_id` | PASS — `dependencies.py:16` raises HTTP 404 |
| Independent daemon status per project | PASS — tests confirm via separate `daemon.pid` files |
| Tickets scoped to project root | PASS — `artifact_reader.list_tickets(project_root)` filters by path |
| Project-map scoped per project | PASS |
| Legacy routes still work | PASS — legacy routers preserved, point to `app.state.project_root` |
| Switching project refreshes state | PARTIAL — see blocking issue below |
| Tests validate isolation with two roots | PASS — `test_project_scoped_routes.py`, `test_project_isolation.py` |
| Runtime artifacts not duplicated | PASS — all paths derived from `project_root` |

---

## Blocking issue

### `TicketDetailPage` bypasses project scoping

`App.jsx:51` routes the ticket detail page as:

```jsx
<Route path="/tickets/:id" element={<TicketDetailPage />} />
```

No `projectId` is passed. Inside `TicketDetailPage.jsx:13-19`, all API fetchers ignore the project context:

```javascript
const TAB_FETCHERS = {
  timeline: (id) => api.getTicketTimeline(id),   // no projectId
  logs:     (id) => api.getTicketLogs(id),        // no projectId
  plan:     (id) => api.getTicketPlan(id),        // no projectId
  // ...
}
```

This means every tab in the detail page — logs, plan, review, tests, artifacts, timeline — hits the legacy route (`/api/tickets/{id}/...`), which resolves against `app.state.project_root` (the default/first project), regardless of which project the user has selected.

The same problem affects all action buttons in the detail page (`approve-plan`, `run-next`, `commit`, etc.): they would execute against the wrong project in a multi-project setup where two projects share a ticket ID.

The `tickets.js` API already supports `projectId` as the second argument for all functions — the work is done at the API layer. The detail page just doesn't use it.

**Required fix:** Pass `projectId` to `TicketDetailPage`. The cleanest approach given the existing architecture is React context (since the detail page is rendered without a parent component that can pass props), or store the active project in URL search params so the detail page can read it from `useSearchParams`. A simpler but less clean fix: expose `activeProject` via a context in `App.jsx` and consume it in `TicketDetailPage`.

---

## Observations (non-blocking)

**`getDaemonActivity` parameter order is inconsistent** (`api/daemon.js:8`):

```javascript
export const getDaemonActivity = (lines = 50, projectId) => ...
```

All other functions in `daemon.js` have `projectId` as the first parameter. `DaemonActivityFeed` passes both arguments correctly, so there's no runtime bug. Still worth normalizing.

**Audit log is not project-scoped** (`tickets.py:429`, `tickets.py:240`):

`app.state.db_path` is a single SQLite database shared across all projects. The project-scoped audit log endpoints (`/{project_id}/tickets/{ticket_id}/audit-log`) read from this shared DB. If two projects both have a `T001`, their audit events are stored together and filtered only by `ticket_id`. This is not in the ticket's stated scope, but it is a known gap to document.

**Trivial wrapper adds noise** (`tickets.py:257`):

```python
def _project_worktrees_dir(project_root: Path) -> Path:
    return resolve_worktrees_dir(project_root)
```

This one-liner wrapper is used in every project-scoped ticket route. Calling `resolve_worktrees_dir(project_root)` directly would be cleaner.

---

## Code quality

The backend design is strong: dependency injection is clean, service functions have no hidden global state, and the dual-router pattern for backward compatibility is minimal and explicit. The test suite tests actual behavior rather than just mocks, and the two-project fixture structure is reusable.

The frontend changes are mechanically consistent: the `_pfx` helper and optional parameter pattern are applied uniformly across all three API modules.

---

IMPLEMENTATION_FIX_REQUIRED