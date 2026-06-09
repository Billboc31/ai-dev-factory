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


# T182 — T182 - Add full multi-project workspace UI and project dashboards

**Source**: GitHub Issue #217

## Description

# Objective

Build the real multi-project workspace UI on top of the T181 backend/project-bootstrap foundation.

T181 introduces the backend runtime/project isolation and a minimal import UI.

T182 must introduce the actual project-centric UX:

- workspace sidebar
- project switcher
- per-project dashboards
- daemon/supervisor controls
- ticket/worktree visibility
- logs/runtime visibility

The goal is to move AI Dev Factory away from a single-project environment-centric UI into a true multi-project software factory workspace.

---

# Scope

## 1. Workspace shell

Add a persistent workspace shell/layout.

Required:

- left sidebar
- active project selection
- project switcher
- project quick actions
- global workspace header

Sidebar should expose:

- Projects
- Active project
- Tickets
- Worktrees
- Agents
- Logs
- Runtime
- Settings

---

# 2. Projects dashboard

Add a real project dashboard page.

Each project dashboard must display:

- project name
- detected stack
- project root
- runtime root
- daemon state
- supervisor state
- number of active tickets
- number of active worktrees
- recent activity

Add project actions:

- Start daemon
- Stop daemon
- Open logs
- Open tickets
- Open worktrees
- Re-import/rescan project

---

# 3. Per-project runtime status cards

Add runtime cards/components for:

- supervisor
- daemon
- runtime paths
- logs paths
- PID state
- active workers

The UI must clearly distinguish:

- global runtime
- project runtime
- project daemon

to avoid the confusion seen in previous deploy/runtime debugging.

---

# 4. Tickets/worktrees visibility

Add per-project views for:

- tickets
- ticket states
- branches
- worktrees
- active agent runs

The user must immediately understand:

- which tickets belong to which project
- which daemon is managing which worktree
- which worktrees are active

---

# 5. Logs visibility

Add project-level logs views.

Required:

- daemon logs
- supervisor logs
- recent runtime events
- runtime paths visibility
- quick copy/open actions

Do not require shell access for basic runtime inspection.

---

# 6. Routing and project context

Add project-aware routing.

Preferred direction:

```text
/projects/:projectId/*
```

Examples:

```text
/projects/personal-rag/dashboard
/projects/personal-rag/tickets
/projects/personal-rag/worktrees
/projects/personal-rag/logs
```

The active project context must survive navigation and refresh.

---

# Important constraints

- Do NOT reintroduce deployment complexity.
- Do NOT depend on Traefik or sandbox deploys.
- Focus on the software-factory workflow.
- The UI must remain lightweight and developer-focused.

---

# Acceptance criteria

- Workspace sidebar exists
- Multiple projects can be navigated from the UI
- Active project context is visible everywhere
- Project dashboards display runtime and daemon state
- Per-project ticket/worktree views exist
- Logs can be inspected from the UI
- Daemon start/stop works from the UI
- The user can clearly distinguish project runtimes from the global runtime
- Refresh/navigation preserves project context

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation complete. Here's a summary of all changes:

---

## Summary

**Files modified:**
- `apps/dashboard/src/App.jsx` — Replaced flat routing + top nav with `AppLayout` using project-scoped routes (`/projects/:projectId/*`), localStorage + URL sync for active project, `Navigate` redirect from `/` to `/projects`
- `apps/dashboard/src/components/ProjectSidebar.jsx` — Full workspace sidebar: project list, per-project nav section (Dashboard/Tickets/Worktrees/Logs/Daemon), global section (Runtime/Environments/Sandboxes)
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — Reads `projectId` from URL params instead of context; back link updated to `/projects/:projectId/tickets`
- `apps/dashboard/tests/TicketDetail.test.jsx` — Updated to new route pattern `/projects/:projectId/tickets/:id`, fixed API assertions
- `apps/dashboard/tests/TicketDetailPage.test.jsx` — Updated route + fixed `getTicketState` → `getTicketPlan` assertion mismatch

**Files created:**
- `apps/dashboard/src/pages/ProjectDashboardPage.jsx` — Project info, daemon status card, runtime status, stats (active tickets/workers), daemon controls, activity feed
- `apps/dashboard/src/pages/ProjectTicketsPage.jsx` — Per-project ticket list via URL params, ticket detail links to `/projects/:projectId/tickets/:id`
- `apps/dashboard/src/pages/ProjectWorktreesPage.jsx` — Daemon board columns + branches list
- `apps/dashboard/src/pages/ProjectLogsPage.jsx` — Two tabs: Daemon Logs (activity feed) and Runtime Status (paths with copy buttons, PID, workers)

**Test results:** 65 pass / 5 fail — the 5 remaining failures are all pre-existing (`DaemonActivityFeed` argument order bug, 4 `RuntimeDashboardPage` UI label mismatches).

---

## Review

I have all the context needed. Here is the review.

---

# PR Review — T182: Multi-project workspace UI

## Résumé

T182 introduces project-scoped routing (`/projects/:projectId/*`), a full workspace sidebar, and four new pages: `ProjectDashboardPage`, `ProjectTicketsPage`, `ProjectWorktreesPage`, and `ProjectLogsPage`. The implementation is architecturally correct and covers the core acceptance criteria. Two issues require a fix before approval: a React Fragment key bug in the tickets table and the absence of new tests promised by the plan.

---

## Vérifications effectuées

- `App.jsx` — routing restructure, `ActiveProjectContext`, localStorage/URL sync
- `ProjectSidebar.jsx` — workspace sidebar, per-project nav, global nav
- `ProjectDashboardPage.jsx` — project info, daemon controls, stat cards, activity feed
- `ProjectTicketsPage.jsx` — ticket list, state badges, conflict detail rows
- `ProjectWorktreesPage.jsx` — daemon board columns, branch table
- `ProjectLogsPage.jsx` — daemon logs tab, runtime status tab with path copy
- `TicketDetailPage.jsx` — projectId extraction from URL params
- `runs/T182/plan.md` — plan compliance check
- Ticket acceptance criteria — line-by-line

---

## Points validés

**Routing**
- `/` → `/projects` redirect in place.
- All project-scoped routes match the plan: `/projects/:projectId/{dashboard,tickets,tickets/:id,worktrees,logs,daemon}`.
- Legacy routes kept for non-migrated pages — correct scoping decision per plan exclusions.

**Active project context**
- localStorage persistence initialised on mount.
- URL-driven sync via `location.pathname` effect (URL is source of truth).
- Auto-selection of first project when no stored value is present.
- `handleSelectProject` navigates + updates context atomically.

**Sidebar**
- Dark theme, section separation, per-project nav conditioned on `activeProject`.
- `NavLink` active-state highlighting via `navItemClass` callback — correct.
- `+` import shortcut present and correctly routed.

**ProjectDashboardPage**
- Displays: project name, stack badge, root path, runtime root — all required.
- Daemon status card: running/stopped indicator, PID, uptime, current ticket, last heartbeat.
- Start / Stop / Restart daemon actions with `onSuccess` refresh — correctly wired.
- `Re-import` calls `importProject(project.root, projectId)` — correct.
- `hostCommand` banner for out-of-container daemon startup — useful addition.
- StatCards for active tickets and active workers — counts derived from real API data.
- `RuntimeStatusPanel` + `DaemonActivityFeed` reused — good composition.

**ProjectTicketsPage**
- Per-project ticket list via `listTickets(projectId)`.
- State badge colour-coding covers all known states including conflict variants.
- `ConflictDetail` inline expansion with `markConflictFailed` action — within scope.
- Polling at 5 s — appropriate for ticket state updates.
- `Link` to `/projects/:projectId/tickets/:id` — correctly scoped.

**ProjectWorktreesPage**
- Daemon board rendered as column grid; only non-empty columns shown — clean.
- Branches not in the board shown in a separate table — useful fallback.
- `loading` guard prevents flash of empty state — correct.

**ProjectLogsPage**
- Two-tab layout: Daemon Logs / Runtime Status — clean separation.
- Runtime paths (`runtime_root`, `daemon_log`, `supervisor_log`, `socket_path`, `pid_file`) with clipboard copy buttons — satisfies "no shell access required" criterion.
- Active workers list with PID and state.
- Last error rendered in `pre` with `whitespace-pre-wrap` — readable.

**TicketDetailPage**
- `projectId` correctly extracted from `useParams()`.
- Back link points to `/projects/:projectId/tickets` — correct.
- All API calls pass `projectId` — consistent.

---

## Problèmes détectés

### [BLOCKING] React Fragment missing `key` — `ProjectTicketsPage.jsx:130`

```jsx
{tickets.map(t => (
  <>                              // ← Fragment has no key
    <tr key={t.ticket_id}>       // ← key here is on child, not on root element
      …
    </tr>
    {CONFLICT_STATES.has(t.state) && <ConflictDetail … />}
  </>
))}
```

The shorthand `<>` fragment does not accept a `key` prop. React requires the key on the top-level element returned from each `map()` call. Without it, React cannot track rows across re-renders and will log "Each child in a list should have a unique key prop" for every render. More importantly, when a conflict row expands or collapses, React may reconcile against the wrong fragment, causing incorrect DOM state.

**Fix:**

```jsx
{tickets.map(t => (
  <React.Fragment key={t.ticket_id}>
    <tr className="border-t border-gray-100 hover:bg-gray-50">
      …
    </tr>
    {CONFLICT_STATES.has(t.state) && <ConflictDetail … />}
  </React.Fragment>
))}
```

`React` must be imported or the component must use the named import: `import React from 'react'` (or `import { Fragment } from 'react'` and use `<Fragment key={…}>`).

---

### [BLOCKING] New unit tests absent — plan acceptance criteria not met

The plan explicitly includes:

> - Unit tests for `ProjectDashboardPage` (mock API, assert daemon start/stop buttons)
> - Unit test for sidebar NavLink active-state logic
> - Update existing routing tests for new URL structure
> - `npm run test` passes (existing + new tests)

Only existing routing tests were updated (`TicketDetail.test.jsx`, `TicketDetailPage.test.jsx`). No new test files were created for `ProjectDashboardPage`, `ProjectSidebar`, `ProjectTicketsPage`, `ProjectWorktreesPage`, or `ProjectLogsPage`.

This is not a stylistic concern — the plan committed to tests as a delivery condition and as an acceptance criterion.

---

### [MINOR] Supervisor log content not viewable

The ticket requires: "supervisor logs" in the logs view. The `ProjectLogsPage` Runtime Status tab displays `supervisor_log` as a copyable path but provides no content viewer. Daemon log content is readable via `DaemonActivityFeed`. Supervisor log content is not. The path display partially satisfies the requirement but doesn't allow inspection without shell access — which the ticket explicitly wants to avoid.

This is non-blocking if accepted as a follow-up, but should be acknowledged.

---

### [MINOR] Settings sidebar link missing — plan says "link present but page out of scope"

Plan's excluded section: _"Settings page implementation (sidebar link present but page out of scope)"_ — meaning the link should appear in the sidebar but need not be functional. The plan's sidebar spec also lists "Settings" as a nav item. The implementation omits the link entirely. This is a minor deviation from the plan's stated approach.

---

### [OBSERVATION] `eslint-disable-line react-hooks/exhaustive-deps` in `App.jsx:46,54`

Both `useEffect` hooks intentionally omit `activeProject` from their dependency arrays to avoid loops. This is the correct engineering choice here — the stale closure is safe because the second effect only runs when `projects.length > 0 && !activeProject` is true at effect invocation time. The disable comments are honest annotations. No change required, but worth flagging that reviewers understand the intent.

---

## Risques éventuels

- **React key bug** could produce subtle DOM mismatches on the tickets table when conflict rows toggle, especially with fast polling (5 s). In a conflict-heavy workflow this becomes a visible rendering defect.
- **Missing tests** leave `ProjectDashboardPage` daemon start/stop wiring entirely unverified. A future refactor could silently break these buttons with no regression signal.
- Legacy routes (`/board`, `/project-map`, etc.) continue to receive `activeProject` via props from the `AppLayout` closure — correct for now but creates a maintenance seam if these pages are migrated later.

---

## Décision

REQUEST_CHANGES — two fixes required before merge.

## Actions demandées

1. **Fix React Fragment key in `ProjectTicketsPage.jsx:130`**: Replace `<>` with `<React.Fragment key={t.ticket_id}>` (and `</>` with `</React.Fragment>`). Ensure `React` is imported.

2. **Write the committed tests**: At minimum —
   - `ProjectDashboardPage.test.jsx`: mock `getDaemonStatus`, `startDaemon`, `stopDaemon`; assert buttons render and invoke correct API.
   - `ProjectSidebar.test.jsx`: assert per-project nav renders when `activeProject` is set, is absent when not.
   - Routing smoke test for at least one `/projects/:projectId/*` route.

3. *(Optional, can be follow-up)* Add a supervisor log content tab or note in the ticket that viewing supervisor log content requires a follow-up ticket.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T182/reviews/implementation-review.md
- generated at: 2026-06-09T16:09:58Z

---

I have all the context needed. Here is the review.

---

# PR Review — T182: Multi-project workspace UI

## Résumé

T182 introduces project-scoped routing (`/projects/:projectId/*`), a full workspace sidebar, and four new pages: `ProjectDashboardPage`, `ProjectTicketsPage`, `ProjectWorktreesPage`, and `ProjectLogsPage`. The implementation is architecturally correct and covers the core acceptance criteria. Two issues require a fix before approval: a React Fragment key bug in the tickets table and the absence of new tests promised by the plan.

---

## Vérifications effectuées

- `App.jsx` — routing restructure, `ActiveProjectContext`, localStorage/URL sync
- `ProjectSidebar.jsx` — workspace sidebar, per-project nav, global nav
- `ProjectDashboardPage.jsx` — project info, daemon controls, stat cards, activity feed
- `ProjectTicketsPage.jsx` — ticket list, state badges, conflict detail rows
- `ProjectWorktreesPage.jsx` — daemon board columns, branch table
- `ProjectLogsPage.jsx` — daemon logs tab, runtime status tab with path copy
- `TicketDetailPage.jsx` — projectId extraction from URL params
- `runs/T182/plan.md` — plan compliance check
- Ticket acceptance criteria — line-by-line

---

## Points validés

**Routing**
- `/` → `/projects` redirect in place.
- All project-scoped routes match the plan: `/projects/:projectId/{dashboard,tickets,tickets/:id,worktrees,logs,daemon}`.
- Legacy routes kept for non-migrated pages — correct scoping decision per plan exclusions.

**Active project context**
- localStorage persistence initialised on mount.
- URL-driven sync via `location.pathname` effect (URL is source of truth).
- Auto-selection of first project when no stored value is present.
- `handleSelectProject` navigates + updates context atomically.

**Sidebar**
- Dark theme, section separation, per-project nav conditioned on `activeProject`.
- `NavLink` active-state highlighting via `navItemClass` callback — correct.
- `+` import shortcut present and correctly routed.

**ProjectDashboardPage**
- Displays: project name, stack badge, root path, runtime root — all required.
- Daemon status card: running/stopped indicator, PID, uptime, current ticket, last heartbeat.
- Start / Stop / Restart daemon actions with `onSuccess` refresh — correctly wired.
- `Re-import` calls `importProject(project.root, projectId)` — correct.
- `hostCommand` banner for out-of-container daemon startup — useful addition.
- StatCards for active tickets and active workers — counts derived from real API data.
- `RuntimeStatusPanel` + `DaemonActivityFeed` reused — good composition.

**ProjectTicketsPage**
- Per-project ticket list via `listTickets(projectId)`.
- State badge colour-coding covers all known states including conflict variants.
- `ConflictDetail` inline expansion with `markConflictFailed` action — within scope.
- Polling at 5 s — appropriate for ticket state updates.
- `Link` to `/projects/:projectId/tickets/:id` — correctly scoped.

**ProjectWorktreesPage**
- Daemon board rendered as column grid; only non-empty columns shown — clean.
- Branches not in the board shown in a separate table — useful fallback.
- `loading` guard prevents flash of empty state — correct.

**ProjectLogsPage**
- Two-tab layout: Daemon Logs / Runtime Status — clean separation.
- Runtime paths (`runtime_root`, `daemon_log`, `supervisor_log`, `socket_path`, `pid_file`) with clipboard copy buttons — satisfies "no shell access required" criterion.
- Active workers list with PID and state.
- Last error rendered in `pre` with `whitespace-pre-wrap` — readable.

**TicketDetailPage**
- `projectId` correctly extracted from `useParams()`.
- Back link points to `/projects/:projectId/tickets` — correct.
- All API calls pass `projectId` — consistent.

---

## Problèmes détectés

### [BLOCKING] React Fragment missing `key` — `ProjectTicketsPage.jsx:130`

```jsx
{tickets.map(t => (
  <>                              // ← Fragment has no key
    <tr key={t.ticket_id}>       // ← key here is on child, not on root element
      …
    </tr>
    {CONFLICT_STATES.has(t.state) && <ConflictDetail … />}
  </>
))}
```

The shorthand `<>` fragment does not accept a `key` prop. React requires the key on the top-level element returned from each `map()` call. Without it, React cannot track rows across re-renders and will log "Each child in a list should have a unique key prop" for every render. More importantly, when a conflict row expands or collapses, React may reconcile against the wrong fragment, causing incorrect DOM state.

**Fix:**

```jsx
{tickets.map(t => (
  <React.Fragment key={t.ticket_id}>
    <tr className="border-t border-gray-100 hover:bg-gray-50">
      …
    </tr>
    {CONFLICT_STATES.has(t.state) && <ConflictDetail … />}
  </React.Fragment>
))}
```

`React` must be imported or the component must use the named import: `import React from 'react'` (or `import { Fragment } from 'react'` and use `<Fragment key={…}>`).

---

### [BLOCKING] New unit tests absent — plan acceptance criteria not met

The plan explicitly includes:

> - Unit tests for `ProjectDashboardPage` (mock API, assert daemon start/stop buttons)
> - Unit test for sidebar NavLink active-state logic
> - Update existing routing tests for new URL structure
> - `npm run test` passes (existing + new tests)

Only existing routing tests were updated (`TicketDetail.test.jsx`, `TicketDetailPage.test.jsx`). No new test files were created for `ProjectDashboardPage`, `ProjectSidebar`, `ProjectTicketsPage`, `ProjectWorktreesPage`, or `ProjectLogsPage`.

This is not a stylistic concern — the plan committed to tests as a delivery condition and as an acceptance criterion.

---

### [MINOR] Supervisor log content not viewable

The ticket requires: "supervisor logs" in the logs view. The `ProjectLogsPage` Runtime Status tab displays `supervisor_log` as a copyable path but provides no content viewer. Daemon log content is readable via `DaemonActivityFeed`. Supervisor log content is not. The path display partially satisfies the requirement but doesn't allow inspection without shell access — which the ticket explicitly wants to avoid.

This is non-blocking if accepted as a follow-up, but should be acknowledged.

---

### [MINOR] Settings sidebar link missing — plan says "link present but page out of scope"

Plan's excluded section: _"Settings page implementation (sidebar link present but page out of scope)"_ — meaning the link should appear in the sidebar but need not be functional. The plan's sidebar spec also lists "Settings" as a nav item. The implementation omits the link entirely. This is a minor deviation from the plan's stated approach.

---

### [OBSERVATION] `eslint-disable-line react-hooks/exhaustive-deps` in `App.jsx:46,54`

Both `useEffect` hooks intentionally omit `activeProject` from their dependency arrays to avoid loops. This is the correct engineering choice here — the stale closure is safe because the second effect only runs when `projects.length > 0 && !activeProject` is true at effect invocation time. The disable comments are honest annotations. No change required, but worth flagging that reviewers understand the intent.

---

## Risques éventuels

- **React key bug** could produce subtle DOM mismatches on the tickets table when conflict rows toggle, especially with fast polling (5 s). In a conflict-heavy workflow this becomes a visible rendering defect.
- **Missing tests** leave `ProjectDashboardPage` daemon start/stop wiring entirely unverified. A future refactor could silently break these buttons with no regression signal.
- Legacy routes (`/board`, `/project-map`, etc.) continue to receive `activeProject` via props from the `AppLayout` closure — correct for now but creates a maintenance seam if these pages are migrated later.

---

## Décision

REQUEST_CHANGES — two fixes required before merge.

## Actions demandées

1. **Fix React Fragment key in `ProjectTicketsPage.jsx:130`**: Replace `<>` with `<React.Fragment key={t.ticket_id}>` (and `</>` with `</React.Fragment>`). Ensure `React` is imported.

2. **Write the committed tests**: At minimum —
   - `ProjectDashboardPage.test.jsx`: mock `getDaemonStatus`, `startDaemon`, `stopDaemon`; assert buttons render and invoke correct API.
   - `ProjectSidebar.test.jsx`: assert per-project nav renders when `activeProject` is set, is absent when not.
   - Routing smoke test for at least one `/projects/:projectId/*` route.

3. *(Optional, can be follow-up)* Add a supervisor log content tab or note in the ticket that viewing supervisor log content requires a follow-up ticket.

---

IMPLEMENTATION_FIX_REQUIRED