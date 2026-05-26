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



# T151 — T151 — Deployment environments dashboard

**Source**: GitHub Issue #149

## Description

Goal: replace the current sandbox-oriented deployment UI with a full deployment environments dashboard supporting branches, persistent environments and deployment lifecycle management.

Context:
The current sandbox UI is still highly technical and runtime-oriented:
- ticket-centric
- manual runtime paths
- sandbox-focused terminology
- limited deployment targeting

As the runtime/deployer stack matures, the product now needs a real environments and deployments experience.

Target examples:
- main
- develop
- integration
- preview
- sandbox
- feature branch deployments
- PR deployments

Scope:
- introduce a dedicated Environments / Deployments page in the dashboard
- support deploying arbitrary refs:
  - branches
  - tags
  - PR refs
  - commits
- support named environments:
  - main
  - develop
  - integration
  - preview
  - sandbox
  - custom
- support deployment modes:
  - Deploy & Test
  - Persistent Environment
- display:
  - deployment status
  - lifecycle state
  - URLs
  - health state
  - branch/ref
  - runtime logs
  - deployment timestamps
- allow:
  - deploy
  - redeploy
  - stop
  - delete
  - refresh
  - open URLs
- support concurrent environments for the same project
- keep environment/deployment concepts generic and project-agnostic
- integrate with isolated runtime roots, supervisor/daemon lifecycle and proxy URLs

Potential future directions:
- environment templates
- automatic preview deployments per PR
- deployment history
- environment snapshots
- environment pinning
- deployment rollback

Tests:
- deploy branch environment
- deploy persistent environment
- concurrent environment deployments
- environment deletion cleanup
- branch/ref display correctness
- environment lifecycle transitions
- dashboard action idempotency

Out of scope:
- Kubernetes
- production rollout orchestration
- cloud deployment
- GitHub Actions integration
- authentication/permissions
- distributed deployment scheduling

Acceptance:
- dashboard exposes a full Environments / Deployments page
- users can deploy arbitrary refs and branches
- users can manage persistent environments from the UI
- multiple environments can coexist simultaneously
- environments expose URLs and lifecycle state clearly
- deployment actions are idempotent
- implementation remains generic and project-agnostic

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have a complete picture of the codebase. Let me write the plan.

## Objective

Introduce a dedicated Environments / Deployments page in the dashboard that lets users deploy arbitrary refs (branches, tags, PR refs, commits) to named, concurrent environments, and manage their full lifecycle (deploy, redeploy, stop, delete, refresh) — integrated with the existing supervisor, docker-compose, worktree and proxy-URL infrastructure.

## Included

### Backend — Control API

**`services/control_api/models/environment.py`** — new file
- `EnvironmentMode` enum: `deploy_and_test`, `persistent`
- `EnvironmentType` enum: `main`, `develop`, `integration`, `preview`, `sandbox`, `feature`, `pr`, `custom`
- `EnvironmentStatus` enum: `creating`, `deploying`, `running`, `stopped`, `failed`, `deleted`
- `EnvironmentState` Pydantic model: `id`, `project_id`, `name`, `env_type`, `mode`, `ref`, `ref_type` (`branch|tag|commit|pr_ref`), `status`, `urls`, `health`, `created_at`, `deployed_at`, `stopped_at`, `last_step`, `error`, `worktree_path`, `compose_project`, `ports`, `supervisor_port`
- `EnvironmentDeployRequest` Pydantic model (POST body for create + deploy)

**`services/control_api/services/environment_manager.py`** — new file
- `create_environment(project_id, name, env_type, mode, ref, ref_type)` → `EnvironmentState`; allocates port slot from `environments-port-registry.json`, writes `{environments_root}/{env_id}/state.json`
- `deploy_environment(env_id)` → sends `POST /environments/start` to supervisor HTTP API; updates status to `deploying`
- `redeploy_environment(env_id)` → stop then deploy; idempotent (no-op if not running)
- `stop_environment(env_id)` → sends `POST /environments/{env_id}/stop` to supervisor; idempotent if already stopped
- `delete_environment(env_id)` → sends `DELETE /environments/{env_id}` to supervisor, removes state dir and port registry entry
- `refresh_environment(env_id)` → reload `state.json` from disk
- `list_environments(project_id=None)` → scan `environments_root` dirs
- `get_environment_logs(env_id, lines)` → tail `{environments_root}/{env_id}/run.log`
- Port slot allocation follows the same `port-registry.json` pattern as `sandbox_manager.py`; proxy URL registration via existing `ProxyManager`

**`services/control_api/routes/environments.py`** — new file
```
POST   /environments                          → EnvironmentState   (create; optional ?deploy=true)
GET    /environments                          → list[EnvironmentState]  (?project_id filter)
GET    /environments/{env_id}                 → EnvironmentState
POST   /environments/{env_id}/deploy          → ActionResult
POST   /environments/{env_id}/redeploy        → ActionResult
POST   /environments/{env_id}/stop            → ActionResult
DELETE /environments/{env_id}                 → 204
POST   /environments/{env_id}/refresh         → EnvironmentState
GET    /environments/{env_id}/logs            → LogsResponse  (?lines=200)
```

**`services/control_api/main.py`** — modify: register `environments` router

---

### Backend — Supervisor

**`services/supervisor/main.py`** — add new routes:
```
POST   /environments/start                    → spawn run_environment.py worker
GET    /environments/{env_id}/status          → read state.json from disk
GET    /environments/{env_id}/logs            → tail run.log (line-buffered)
POST   /environments/{env_id}/stop            → SIGTERM worker process
DELETE /environments/{env_id}                 → stop + cleanup worktree + remove dir
```

Worker process tracked by PID in `{environments_root}/{env_id}/worker.pid`

**`tools/agent_runner/run_environment.py`** — new file
- CLI: `--env-id`, `--project-id`, `--ref`, `--ref-type`, `--mode`, `--environments-root`
- Steps executed and recorded in `state.json` (`last_step`):
  1. `checkout` — create isolated git worktree at the requested ref (`git worktree add --detach ... {ref}`)
  2. `bootstrap` — run project bootstrap script
  3. `build` — run project build
  4. `start` — `docker compose up -d` with allocated env vars + ports
  5. `healthcheck` — poll project healthcheck URL
- For `mode=deploy_and_test`: after successful healthcheck, mark `status=running`; stop is triggered externally or after dashboard action
- For `mode=persistent`: same pipeline but environment stays running after healthcheck passes
- Writes `run.log` throughout; updates `state.json` status, `deployed_at`, `error`, `last_step`
- On failure: run undeploy (docker compose down), set `status=failed`

---

### Frontend

**`apps/dashboard/src/api/environments.js`** — new file
- `listEnvironments(projectId?)`, `getEnvironment(id)`, `createEnvironment(data)`
- `deployEnvironment(id)`, `redeployEnvironment(id)`, `stopEnvironment(id)`
- `deleteEnvironment(id)`, `refreshEnvironment(id)`, `getEnvironmentLogs(id, lines)`

**`apps/dashboard/src/pages/EnvironmentsPage.jsx`** — new file
- Top bar: project filter dropdown, environment type filter, status filter, "New Environment" button
- Environment list: one `EnvironmentCard` per environment, auto-refreshed every 5s
- "New Environment" opens `CreateEnvironmentModal`
- Log drawer: inline log viewer per environment (reuses `LogViewerDrawer` pattern from `runtime-dashboard/`)
- Empty state when no environments exist

**`apps/dashboard/src/components/environments/EnvironmentCard.jsx`** — new file
- Displays: name, env type badge, status badge, ref + ref_type chip, URLs as clickable links, health indicator, `created_at` / `deployed_at` timestamps, `last_step` progress hint, error message if failed
- Action buttons: Deploy (if stopped/failed), Redeploy (if running), Stop (if running), Delete, Refresh, View Logs toggle
- Action buttons disabled while status is `creating` or `deploying` (prevent double-submit)

**`apps/dashboard/src/components/environments/CreateEnvironmentModal.jsx`** — new file
- Fields: Project (selector), Name (text), Environment type (dropdown), Mode (radio: Deploy & Test / Persistent Environment), Ref (text input), Ref type (dropdown: branch / tag / commit / pr_ref)
- Submit calls `createEnvironment` then optionally `deployEnvironment` if mode warrants immediate deploy

**`apps/dashboard/src/App.jsx`** — modify: add route `/environments` → `EnvironmentsPage`

**`apps/dashboard/src/components/ProjectSidebar.jsx`** (or equivalent nav component) — modify: add "Environments" navigation link pointing to `/environments`

---

### Tests

**`tests/test_environment_manager.py`** — new file, covering:
- `test_deploy_branch_environment` — create + deploy a branch environment; assert `status=running`
- `test_deploy_persistent_environment` — create with `mode=persistent`; assert environment remains running after healthcheck
- `test_concurrent_environment_deployments` — deploy two environments for the same project; assert both coexist with distinct port allocations
- `test_environment_deletion_cleanup` — delete a running environment; assert worktree removed and port registry entry freed
- `test_branch_ref_display_correctness` — assert `ref` and `ref_type` stored and returned correctly for branch, tag, commit, pr_ref inputs
- `test_environment_lifecycle_transitions` — drive state machine through: creating → deploying → running → stopped → deleted
- `test_dashboard_action_idempotency` — call deploy twice, stop twice, delete twice; assert no errors and final state is consistent

## Excluded

- Kubernetes, cloud deployment, GitHub Actions integration
- Authentication, access control, permissions
- Automatic PR preview deployments (future ticket)
- Deployment history / audit trail beyond current run log
- Environment templates, snapshots, pinning, rollback
- Distributed deployment scheduling
- Any changes to existing sandbox (`/sandboxes/*`), deployer (`/deployer/*`), or runtime dashboard routes — those remain untouched
- Multi-host or remote deployment targets

## Acceptance criteria

- `GET /environments` returns all environments across projects; filtered correctly by `?project_id=`
- A new environment created via `POST /environments` with `ref=my-branch&ref_type=branch` shows `ref=my-branch` and `ref_type=branch` in subsequent GET responses
- Two environments for the same project can be deployed concurrently; each has distinct port allocations and distinct URLs
- `POST /environments/{env_id}/deploy` called twice while already deploying is a no-op (returns current state, no duplicate worker spawned)
- `DELETE /environments/{env_id}` removes the worktree directory and frees the port registry slot; a subsequent `GET` returns 404
- `mode=persistent` environment remains `status=running` after healthcheck succeeds without any further API call
- `mode=deploy_and_test` environment transitions to `status=running` and can be stopped via `POST /environments/{env_id}/stop`
- Dashboard `/environments` page renders all environments with name, type badge, status badge, ref chip, URLs, timestamps and action buttons
- Action buttons are disabled while status is `creating` or `deploying`
- Log drawer for an environment tails `run.log` with offset-based streaming (same pattern as existing `LogViewerDrawer`)
- All seven integration tests in `test_environment_manager.py` pass
- No existing routes (`/sandboxes/*`, `/projects/{id}/sandbox/*`, `/runtime-dashboard/*`) are broken

---

## Review

# Plan review — T151

Decision: PLAN_FIX_REQUIRED

The current plan correctly identifies the need for a dedicated Environments / Deployments dashboard, but it is too broad and introduces a second orchestration stack parallel to the existing sandbox runtime.

## Main concern

The plan proposes new backend primitives:

- `EnvironmentManager`
- `run_environment.py`
- new supervisor environment routes
- a new environment port registry
- a new deployment state model
- a new worker lifecycle

This duplicates existing capabilities already present or being built in the sandbox runtime:

- isolated worktrees
- isolated ports
- compose project isolation
- proxy URLs
- lifecycle modes
- undeploy/cleanup
- supervisor-side execution
- sandbox run state

Duplicating this stack will create long-term divergence between:

- sandbox deploy pipeline
- environment deploy pipeline

That should be avoided.

## Required direction

T151 should be an environment-management UX/API layer built on top of the existing sandbox/runtime lifecycle.

It should NOT create a separate deployment engine.

See `runs/T151/fixes/plan-fix-1.md` for the requested reduced/refactored scope.

---

## Instructions de fix

# Plan fix — T151

## Objective

Refactor T151 so that Environments / Deployments become a higher-level product abstraction built on top of the existing sandbox/runtime infrastructure.

T151 must not introduce a second orchestration pipeline.

## Required changes

### 1. Reuse existing sandbox/runtime lifecycle

Do NOT introduce:

- `run_environment.py`
- a second worker orchestration pipeline
- a second port registry implementation
- a parallel deployment state machine
- a separate deploy execution engine

Instead:

- environments should internally reuse the existing sandbox/runtime lifecycle
- environment lifecycle modes should map to existing sandbox lifecycle modes
- existing supervisor orchestration should remain the execution backend
- existing deploy/undeploy/cleanup logic should remain canonical

## 2. Reposition T151 as UX + abstraction layer

T151 should primarily introduce:

- environment-oriented dashboard UX
- environment metadata abstraction
- branch/ref deployment selection
- persistent environment management
- deployment views and actions

The runtime engine itself should remain shared.

## 3. Reuse existing infrastructure

Reuse existing:

- sandbox manager/runtime manager
- proxy manager
- undeploy lifecycle
- runtime root isolation
- supervisor orchestration
- lifecycle modes
- logs/state files
- port allocation system
- cleanup pipeline

Avoid creating duplicate implementations.

## 4. Environment abstraction

An environment should conceptually become:

- a named runtime deployment
- backed by the existing sandbox/runtime infrastructure
- with additional metadata:
  - branch/ref
  - environment type
  - deployment mode
  - URLs
  - timestamps

## 5. Minimize backend surface expansion

Prefer:

- adapting existing routes
- extending existing runtime state models
- wrapping existing lifecycle APIs

instead of introducing a fully separate backend stack.

## Acceptance update

- only one runtime orchestration pipeline exists in the system
- environments reuse existing sandbox/runtime execution logic
- no duplicate deploy engine is introduced
- dashboard presents environments as a product abstraction over existing runtime infrastructure
- lifecycle behavior remains centralized and consistent
- implementation remains generic and maintainable