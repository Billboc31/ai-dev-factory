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



# T139 — T139 — Runtime dashboard for sandboxes and proposals

**Source**: GitHub Issue #127

## Description

Create a runtime dashboard to manage sandbox runs, proposal runs, logs and cleanup operations.

Context:
The platform now creates many runtime artifacts such as sandboxes, worktrees, logs, compose projects, pid files and proposal runs. A dedicated operational dashboard is needed.

Scope:
- list sandbox runs with status, timestamps, ports, worktree path and logs
- actions to refresh, rerun validation, stop and cleanup a sandbox
- list proposal runs with proposal id, sandbox id, status and changed files
- actions to open proposal, inspect patches and delete proposals
- runtime health section with supervisor status, active jobs, stale pid files and stale locks
- cleanup tools for stale worktrees, stale sandbox directories and orphan runtime artifacts
- live log refresh and tailing
- generic metadata-driven UI with no project-specific assumptions
- cleanup safety checks preventing deletion of active jobs or main runtime artifacts

Out of scope:
- automatic proposal apply
- automatic merge
- cloud deployment
- tester-agent orchestration

Acceptance:
- dashboard shows sandbox runs and proposal runs
- logs are accessible from the UI
- stale runtime artifacts can be cleaned safely
- runtime health is visible
- cleanup never impacts the main runtime
- active jobs cannot be deleted accidentally
- no project-specific assumptions exist

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have a thorough picture of the existing stack. Here is the implementation plan.

---

## Objective

Add a dedicated **Runtime Dashboard** page to the existing React SPA that gives operators a unified view of sandbox runs, proposal runs, and runtime health, with safe cleanup actions and live log tailing — all driven by generic metadata with no project-specific assumptions.

---

## Included

### Backend — `services/control_api/routes/`

**New file: `runtime_dashboard.py`** — registers a `/runtime-dashboard` router with these endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/runtime-dashboard/sandbox-runs` | List all sandbox runs: id, status, timestamps, ports, worktree path |
| `GET` | `/runtime-dashboard/sandbox-runs/{id}/logs` | Stream or page sandbox run logs |
| `POST` | `/runtime-dashboard/sandbox-runs/{id}/rerun` | Trigger rerun of sandbox validation |
| `POST` | `/runtime-dashboard/sandbox-runs/{id}/stop` | Stop a running sandbox |
| `DELETE` | `/runtime-dashboard/sandbox-runs/{id}` | Cleanup sandbox (safety check: reject if active) |
| `GET` | `/runtime-dashboard/proposal-runs` | List all proposal runs: proposal id, sandbox id, status, changed files |
| `GET` | `/runtime-dashboard/proposal-runs/{id}/patch` | Return raw patch for a proposal |
| `DELETE` | `/runtime-dashboard/proposal-runs/{id}` | Delete a proposal (safety check: reject if active) |
| `GET` | `/runtime-dashboard/health` | Supervisor status, active jobs count, stale pid files, stale locks |
| `POST` | `/runtime-dashboard/cleanup/stale-worktrees` | Delete worktrees with no active lock (dry-run flag) |
| `POST` | `/runtime-dashboard/cleanup/stale-sandboxes` | Delete sandbox dirs with no active lock (dry-run flag) |
| `POST` | `/runtime-dashboard/cleanup/orphan-artifacts` | Delete pid/lock files whose PID is dead (dry-run flag) |

Safety rules enforced in all DELETE/cleanup handlers:
- Reject if target has an active `daemon.lock` (PID alive)
- Reject if target is the main runtime root (`runs/`, `sandboxes/`, repo clone)
- Return `409 Conflict` with reason on safety failure

Data sources: read `runs/*/state.json`, `runs/daemon.pid`, `runs/*/daemon.lock`, supervisor HTTP (`/supervisor/status`, `/auto-fix/{id}/proposals`).

**`services/control_api/main.py`** — register the new router.

---

### Frontend — `apps/dashboard/src/`

**New page: `src/pages/RuntimeDashboardPage.tsx`**

Sections rendered as collapsible panels:
1. **Sandbox Runs** — table with columns: id, status badge, started\_at, finished\_at, ports, worktree path; per-row actions: Refresh, Rerun, Stop, Delete (disabled if active)
2. **Proposal Runs** — table with columns: proposal id, sandbox id, status badge, changed files count; per-row actions: Open (link to ticket), View Patch (modal), Delete (disabled if active)
3. **Runtime Health** — cards for: supervisor up/down, active job count, stale pid file list, stale lock file list
4. **Cleanup Tools** — three buttons (Stale Worktrees, Stale Sandboxes, Orphan Artifacts), each with a Dry Run toggle and a confirmation dialog before destructive execution; results shown inline
5. **Log Viewer** — slide-out panel, triggered by clicking a sandbox run row; polls `GET /runtime-dashboard/sandbox-runs/{id}/logs?offset=N` every 2 s, auto-scrolls to bottom; Stop button halts polling

**New components** (under `src/components/runtime-dashboard/`):
- `SandboxRunsTable.tsx`
- `ProposalRunsTable.tsx`
- `RuntimeHealthPanel.tsx`
- `CleanupToolsPanel.tsx`
- `LogViewerDrawer.tsx`
- `ConfirmDialog.tsx` (reusable if not already present)

**Route registration: `src/App.tsx`** — add `/runtime-dashboard` route pointing to `RuntimeDashboardPage`.

**Navigation: `src/components/Sidebar.tsx`** (or equivalent nav file) — add "Runtime Dashboard" link.

**API client: `src/api/runtimeDashboard.ts`** — typed Axios wrappers for all new endpoints, using the existing Axios base client.

---

### Tests

- `tests/test_runtime_dashboard_api.py` — pytest unit tests for each new endpoint covering: happy path, safety rejection (active lock), missing resource (404), dry-run cleanup
- `apps/dashboard/src/pages/RuntimeDashboardPage.test.tsx` — Vitest + React Testing Library: renders sections, shows "active" badge disabling delete button, cleanup confirm dialog flow

---

## Excluded

- Automatic proposal apply or merge
- Cloud deployment or remote environment support
- Tester-agent orchestration
- Modifying existing ticket workflow pages (TicketsPage, DeployerPage, etc.)
- Any project-specific column or assumption (all metadata comes from generic state files)
- Real-time WebSocket/SSE streaming (polling every 2 s is sufficient for this ticket)
- Authentication or access control on new endpoints

---

## Acceptance criteria

1. `GET /runtime-dashboard/sandbox-runs` returns a list containing at minimum: `id`, `status`, `started_at`, `worktree_path`; an empty list when no runs exist.
2. `DELETE /runtime-dashboard/sandbox-runs/{id}` returns `409` when `runs/{id}/daemon.lock` holds a live PID; returns `204` when the lock is absent or stale.
3. `POST /runtime-dashboard/cleanup/stale-worktrees` with `dry_run=true` returns the list of candidate paths without deleting anything.
4. `GET /runtime-dashboard/health` returns `supervisor_status`, `active_jobs`, `stale_pid_files`, `stale_locks` keys.
5. The React page renders at `/runtime-dashboard` and displays at least the four sections (Sandbox Runs, Proposal Runs, Runtime Health, Cleanup Tools).
6. Delete and Stop action buttons are disabled (visually and functionally) for rows whose status is active/running.
7. The Log Viewer panel opens for a sandbox run row, displays log content, and stops polling when closed.
8. All new pytest tests pass (`pytest tests/test_runtime_dashboard_api.py`).
9. All new Vitest tests pass (`npm run test` in `apps/dashboard/`).
10. No existing test suite regresses.

---

## Review

# Plan review — T139

Decision: PLAN_FIX_REQUIRED

The current T139 plan is too large for one safe ticket.

It includes in one implementation:

- a new full runtime dashboard page
- many backend endpoints
- sandbox rerun
- sandbox stop
- proposal patch viewer
- runtime health aggregation
- global stale worktree cleanup
- global stale sandbox cleanup
- orphan pid/lock cleanup
- destructive cleanup flows
- frontend log polling
- backend and frontend tests

This is valuable, but too much for a first runtime operations UI.

The first version should be mostly read-only and safe, with only very limited cleanup.

See `runs/T139/fixes/plan-fix-1.md` for the reduced V1 scope.

---

## Instructions de fix

# Plan fix — T139 V1

## New objective

Implement a safe first version of the Runtime Dashboard.

The first version should focus on:
- runtime observability
- sandbox visibility
- proposal visibility
- log access
- limited safe cleanup

Avoid advanced runtime orchestration or destructive cleanup automation in this ticket.

## Included

### Runtime dashboard page

Add a dedicated Runtime Dashboard page.

### Sandbox runs section

Display:
- sandbox id
- project id
- status
- timestamps
- ports
- worktree path
- compose project name

Actions:
- refresh
- open logs
- cleanup completed sandbox only

No rerun or stop actions in this ticket.

### Proposal runs section

Display:
- proposal id
- sandbox id
- status
- changed files count
- timestamps

Actions:
- open proposal summary
- delete completed proposal only

No patch apply or rerun logic.

### Runtime health section

Read-only display:
- supervisor status
- active jobs count
- stale pid files
- stale lock files

No automatic cleanup actions.

### Logs viewer

Add:
- sandbox log viewer
- polling refresh
- stop polling when closed

### Limited cleanup

Allow cleanup only for:
- completed sandboxes
- failed sandboxes
- completed proposals

Cleanup must reject:
- running jobs
- active locks
- main runtime paths

### Generic metadata-driven architecture

No project-specific assumptions.
All rendering must rely on generic runtime metadata.

### Tests

Add tests for:
- sandbox listing
- proposal listing
- cleanup rejection for active jobs
- log retrieval
- runtime health display

## Excluded

- sandbox rerun
- sandbox stop
- global stale cleanup automation
- orphan artifact cleanup
- patch apply
- proposal execution
- automatic merge
- cloud deployment
- tester-agent orchestration

## Acceptance criteria

- Runtime Dashboard page renders correctly
- sandbox runs and proposal runs are visible
- logs are accessible
- runtime health is visible
- cleanup works only for completed or failed artifacts
- active jobs cannot be deleted
- no project-specific assumptions exist