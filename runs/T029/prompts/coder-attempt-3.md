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


# T029 — T029 — Minimal dashboard UI for runtime orchestration

**Source**: GitHub Issue #27

## Description

# T029 — Minimal dashboard UI for runtime orchestration

## Contexte

Le projet dispose maintenant :

- d’un moteur workflow (`run_ticket.py`)
- d’un daemon d’orchestration (`run_daemon.py`)
- d’un intake GitHub (`run_issue_intake.py`)
- d’un lifecycle PR/checkpoint
- d’une Control API REST (`services/control_api/`)

Le système est pilotable via API mais reste difficile à utiliser sans terminal.

Le prochain cap est une première IHM minimale permettant de piloter les tickets et le daemon.

Architecture cible :

```text
Dashboard UI
↓
Control API REST
↓
run_ticket.py / run_daemon.py / run_issue_intake.py
```

## Objectif

Créer une première interface web minimale mais fonctionnelle pour piloter le runtime IA.

L’objectif n’est PAS le design final.

Le but est :

- visualiser les tickets
- visualiser les états runtime
- lancer des actions workflow
- contrôler le daemon
- consulter rapidement logs et artefacts

## Architecture obligatoire

### 1. Module séparé

Créer un module dédié.

Exemple :

```text
apps/dashboard/
```

### 2. La UI ne doit PAS parler directement au runtime

Toutes les actions passent par :

```text
services/control_api/
```

La UI ne doit jamais :

- modifier directement `state.json`
- appeler Git directement
- appeler `run_ticket.py` directement
- appeler `run_daemon.py` directement
- lire les fichiers runtime directement

## Inclus

### 1. Dashboard tickets

Page listant les tickets :

```text
T028 | TEST_COMPLETE | branch | last update
T029 | CODER_RUNNING | branch | last update
```

Informations minimales :

- ticket id
- état courant
- branche
- dernier update
- dernier log

### 2. Vue détail ticket

Afficher :

- `state.json`
- derniers logs runtime
- plan
- reviews
- tests
- artefacts disponibles

### 3. Actions workflow

Boutons :

```text
Run next
Approve plan
Request plan fix
Approve implementation
Request implementation fix
```

### 4. Actions Git/runtime

Boutons :

```text
Commit
Push
Checkpoint
```

### 5. Contrôle daemon

Page daemon avec :

```text
Status
Start
Stop
Restart
```

Informations minimales :

- running/stopped
- PID
- uptime si disponible

### 6. Logs

Afficher les derniers logs runtime du ticket.

Pas besoin de websocket/live streaming dans ce ticket.

### 7. Stack suggérée

Frontend suggéré :

```text
React + Vite
```

Mais un frontend minimal reste acceptable.

### 8. Tests

Ajouter des tests minimaux :

- rendering principal
- appels API
- gestion erreurs API
- boutons d’action

## Hors scope

- websocket live logs
- auth
- multi-user
- multi-project
- édition des artefacts
- terminal intégré
- design avancé
- mobile app native
- accès distant sécurisé
- RBAC

## Critères d’acceptation

- une UI minimale existe
- les tickets sont visibles
- le daemon est contrôlable
- les artefacts principaux sont visibles
- les actions workflow fonctionnent
- toutes les actions passent par la Control API
- aucune logique workflow n’est dupliquée
- aucune logique Git n’est dupliquée
- les erreurs API sont affichées proprement
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
apps/dashboard/
services/control_api/
tests/
README.md
```

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 37 tests pass. Here's a summary of the changes made:

**`apps/dashboard/src/pages/TicketDetailPage.jsx`**
- Added `'artifacts'` to the `TABS` array
- Added `artifacts: (id) => api.getTicketArtifacts(id)` to `TAB_FETCHERS`
- Added `renderContent()` helper that JSON-stringifies non-string content (handles the array/object artifact response correctly)
- `refreshTicket()` now clears `tabContent` so tabs re-fetch after a workflow action (fixes the cache staleness issue)

**`apps/dashboard/src/pages/TicketsPage.jsx`**
- Added "Last Log" column header
- Added `t.last_log` cell in each row (truncated with `title` tooltip for long entries)
- Updated empty-state `colSpan` from 4 → 5

**`apps/dashboard/tests/TicketDetail.test.jsx`**
- Added test verifying the artifacts tab fetches and renders artifact content

**`apps/dashboard/tests/TicketList.test.jsx`**
- Updated mock data to include `last_log`
- Added test verifying the "Last Log" column header and content are rendered

---

## Review

I now have everything needed to write the review.

---

## Review — T029 Minimal dashboard UI

### Scope and intent

Second review cycle. The first review flagged two blocking issues (missing artifacts tab, missing `last_log` column). The coder added both to the frontend. This review assesses whether the fixes are complete and whether additional issues remain.

---

### Architecture compliance

All UI calls go through `baseURL: '/api'` (Vite proxy → `http://localhost:8080`). No direct access to `state.json`, Git, or runtime scripts. The module is fully isolated in `apps/dashboard/`. This requirement is satisfied.

---

### Blocking issues

#### 1. `last_log` column is permanently empty — backend does not supply the field

`TicketsPage.jsx:69` renders `{t.last_log || '—'}`. The ticket explicitly requires a "dernier log" column.

The backend never produces this value:

- `TicketSummary` schema (`schemas.py:26-31`) has five fields: `ticket_id`, `state`, `branch`, `issue_number`, `updated_at`. No `last_log`.
- `artifact_reader.list_tickets()` (`artifact_reader.py:38-44`) constructs `TicketSummary` from those five fields only.
- The API response will never include `last_log`. The column will permanently show `—` for every ticket.

The fix is partial — the frontend column was added but the backend change was not made. The column needs to be populated: read the last non-empty line of `runs/{ticket_id}/runtime.log` in `artifact_reader.list_tickets()`, add `last_log: str | None = None` to `TicketSummary`, and populate it.

#### 2. Overview tab shows a 5-field API subset, not `state.json`

`TicketDetailPage.jsx:110-113` renders `JSON.stringify(ticket, null, 2)` where `ticket` is the `TicketSummary` API response — only the five schema fields above.

The ticket requirement states: _"Afficher state.json"_. The actual `state.json` file may contain step history, coder output, error details, last step attempted, and other fields critical to understanding ticket progress. Showing 5 schema fields is not the same as showing `state.json`.

Fix requires a new read endpoint, e.g. `GET /tickets/{id}/state` returning the raw JSON content of `runs/{ticket_id}/state.json`, which the overview tab then fetches via `TAB_FETCHERS`.

---

### Minor observations (not blocking)

**Stale tab cache on ticket navigation** — `TicketDetailPage.jsx:56-61`, `refreshTicket()` clears `tabContent`, but the `useEffect` on `[id]` (`line 32-37`) does not. Navigating from ticket A to ticket B will show ticket A's tab content until the user switches tabs or triggers an action. Fix: `setTabContent({})` inside the `[id]` effect.

**Silent error suppression in `refreshTicket()`** — `.catch(() => {})` at `line 60` silently discards errors that occur when refreshing ticket state after a workflow action. If the ticket state refresh fails, the UI becomes stale with no user feedback. Pass `setError` to the catch handler.

**Commit and Push don't refresh ticket state** — `TicketDetailPage.jsx:137-138`, both buttons lack `onSuccess={refreshTicket}`. Since these operations may update `state.json` (e.g., checkpoint timestamp), the displayed state doesn't update. Low severity because these actions are less likely to change the visible state than workflow transitions, but the inconsistency is notable.

**Uptime shown as absolute timestamp instead of duration** — `DaemonPage.jsx:43-47` displays `Started: {new Date(status.started_at).toLocaleString()}`. The ticket says _"uptime si disponible"_, which implies a duration (e.g., "3h 42m"). A computed duration from `started_at` to `Date.now()` would satisfy the requirement.

---

### What is working correctly

- All three routes (`/`, `/tickets/:id`, `/daemon`) are present and correctly linked
- All five workflow action buttons present (Run Next, Approve Plan, Request Plan Fix, Approve Implementation, Request Impl Fix)
- All three git/runtime buttons present (Commit, Push, Checkpoint)
- Daemon Start, Stop, Restart controls wired correctly with post-action status refresh
- Tab-based detail view with 6 tabs (overview, logs, plan, review, tests, artifacts), lazy-loaded and cached per session
- `ErrorBanner` with dismissal on all pages
- State badge color coding for COMPLETE, RUNNING, FAILED states
- 37 tests across 4 files, all passing
- API layer fully proxied, no direct runtime access

---

### Verdict

Two acceptance criteria are not met end-to-end:
1. The "dernier log" column is always empty because the backend never provides the field.
2. The detail view does not show `state.json` — it shows a 5-field API projection.

Both require backend changes that were not made in this cycle.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T029/reviews/implementation-review.md
- generated at: 2026-05-15T10:47:46Z

---

I now have everything needed to write the review.

---

## Review — T029 Minimal dashboard UI

### Scope and intent

Second review cycle. The first review flagged two blocking issues (missing artifacts tab, missing `last_log` column). The coder added both to the frontend. This review assesses whether the fixes are complete and whether additional issues remain.

---

### Architecture compliance

All UI calls go through `baseURL: '/api'` (Vite proxy → `http://localhost:8080`). No direct access to `state.json`, Git, or runtime scripts. The module is fully isolated in `apps/dashboard/`. This requirement is satisfied.

---

### Blocking issues

#### 1. `last_log` column is permanently empty — backend does not supply the field

`TicketsPage.jsx:69` renders `{t.last_log || '—'}`. The ticket explicitly requires a "dernier log" column.

The backend never produces this value:

- `TicketSummary` schema (`schemas.py:26-31`) has five fields: `ticket_id`, `state`, `branch`, `issue_number`, `updated_at`. No `last_log`.
- `artifact_reader.list_tickets()` (`artifact_reader.py:38-44`) constructs `TicketSummary` from those five fields only.
- The API response will never include `last_log`. The column will permanently show `—` for every ticket.

The fix is partial — the frontend column was added but the backend change was not made. The column needs to be populated: read the last non-empty line of `runs/{ticket_id}/runtime.log` in `artifact_reader.list_tickets()`, add `last_log: str | None = None` to `TicketSummary`, and populate it.

#### 2. Overview tab shows a 5-field API subset, not `state.json`

`TicketDetailPage.jsx:110-113` renders `JSON.stringify(ticket, null, 2)` where `ticket` is the `TicketSummary` API response — only the five schema fields above.

The ticket requirement states: _"Afficher state.json"_. The actual `state.json` file may contain step history, coder output, error details, last step attempted, and other fields critical to understanding ticket progress. Showing 5 schema fields is not the same as showing `state.json`.

Fix requires a new read endpoint, e.g. `GET /tickets/{id}/state` returning the raw JSON content of `runs/{ticket_id}/state.json`, which the overview tab then fetches via `TAB_FETCHERS`.

---

### Minor observations (not blocking)

**Stale tab cache on ticket navigation** — `TicketDetailPage.jsx:56-61`, `refreshTicket()` clears `tabContent`, but the `useEffect` on `[id]` (`line 32-37`) does not. Navigating from ticket A to ticket B will show ticket A's tab content until the user switches tabs or triggers an action. Fix: `setTabContent({})` inside the `[id]` effect.

**Silent error suppression in `refreshTicket()`** — `.catch(() => {})` at `line 60` silently discards errors that occur when refreshing ticket state after a workflow action. If the ticket state refresh fails, the UI becomes stale with no user feedback. Pass `setError` to the catch handler.

**Commit and Push don't refresh ticket state** — `TicketDetailPage.jsx:137-138`, both buttons lack `onSuccess={refreshTicket}`. Since these operations may update `state.json` (e.g., checkpoint timestamp), the displayed state doesn't update. Low severity because these actions are less likely to change the visible state than workflow transitions, but the inconsistency is notable.

**Uptime shown as absolute timestamp instead of duration** — `DaemonPage.jsx:43-47` displays `Started: {new Date(status.started_at).toLocaleString()}`. The ticket says _"uptime si disponible"_, which implies a duration (e.g., "3h 42m"). A computed duration from `started_at` to `Date.now()` would satisfy the requirement.

---

### What is working correctly

- All three routes (`/`, `/tickets/:id`, `/daemon`) are present and correctly linked
- All five workflow action buttons present (Run Next, Approve Plan, Request Plan Fix, Approve Implementation, Request Impl Fix)
- All three git/runtime buttons present (Commit, Push, Checkpoint)
- Daemon Start, Stop, Restart controls wired correctly with post-action status refresh
- Tab-based detail view with 6 tabs (overview, logs, plan, review, tests, artifacts), lazy-loaded and cached per session
- `ErrorBanner` with dismissal on all pages
- State badge color coding for COMPLETE, RUNNING, FAILED states
- 37 tests across 4 files, all passing
- API layer fully proxied, no direct runtime access

---

### Verdict

Two acceptance criteria are not met end-to-end:
1. The "dernier log" column is always empty because the backend never provides the field.
2. The detail view does not show `state.json` — it shows a 5-field API projection.

Both require backend changes that were not made in this cycle.

IMPLEMENTATION_FIX_REQUIRED