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



# T127 — T127 — Project deployer profiles and dashboard deployment actions

**Source**: GitHub Issue #93

## Description

# Objective

Introduce a generic project deployer system able to analyze a project, generate a deployment profile, and expose deployment actions in the dashboard.

## Included

- Add a project scanner flow from the dashboard.
- Add a deploy profile format, for example:
  - `.ai-dev-factory/deploy.yml`
- Add a deploy profile generator using Claude-assisted analysis.
- Detect:
  - docker services
  - frontend/backend stacks
  - build commands
  - healthchecks
  - required host tools
  - daemon host-side requirements
- Support host-side and docker-based runtime components.
- Add dashboard actions:
  - Scan project
  - Generate deploy profile
  - Deploy main
  - Deploy current branch
  - Restart services
  - View deployment logs
- Add deterministic Python deployment execution.
- Add deployment logs and deployment status tracking.
- Add healthcheck verification after deployment.
- Support ai-dev-factory as the first deployer-enabled project.

## Excluded

- Kubernetes orchestration.
- Cloud autoscaling.
- Multi-host deployment.
- Production secret management.
- SaaS billing.
- Full CI/CD replacement.

## Acceptance criteria

- A project can be scanned from the dashboard.
- A deploy profile is generated and stored in the target project.
- Dashboard shows deployment actions for deployer-enabled projects.
- Deploy actions execute deterministic Python deployment steps.
- Deployment logs are visible from the dashboard.
- Healthchecks run after deployment.
- ai-dev-factory deployment profile supports:
  - docker services
  - host-side daemon
  - gh dependency
  - Claude dependency
- Deployment failures return structured errors instead of silent failures.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have enough context to write the plan.

## Objective

Introduce a project deployer subsystem: a deploy profile format (`.ai-dev-factory/deploy.yml`), a project scanner, a Claude-assisted profile generator, a deterministic Python deployment executor, and dashboard actions to trigger and observe deployments. The ai-dev-factory project itself ships the first deploy profile.

## Included

### Deploy profile format
- Define `.ai-dev-factory/deploy.yml` schema (version, project name, components list, required\_tools list, deploy steps sequence).
- Components support two types: `docker` (references a docker-compose service + healthcheck URL) and `host` (command + PID/file healthcheck).
- Deploy steps support actions: `git_pull`, `docker_build`, `docker_compose_up`, `host_restart`, `healthcheck`.
- Create `.ai-dev-factory/deploy.yml` for ai-dev-factory covering: `api` (docker), `web` (docker), `daemon` (host), required tools `gh`, `git`, `docker`, `claude`.

### Backend — new router and services
- `services/control_api/routes/deployer.py` — register as `/projects/{project_id}/deployer/`:
  - `POST /scan` — run project scanner, return `ScanResult`
  - `POST /generate-profile` — Claude-assisted profile generation from scan result
  - `POST /deploy` — execute deploy (body: `{ branch: str }`, default `"main"`)
  - `POST /restart` — restart all services defined in profile
  - `GET /logs` — return last N log entries from deployment log file
  - `GET /status` — return current `DeploymentStatus`
- `services/control_api/services/project_scanner.py` — detect: docker-compose services, `package.json` (frontend), `requirements.txt`/`pyproject.toml` (Python backend), healthcheck patterns, host tool requirements (`gh`, `git`, `docker`, `claude`). Returns structured `ScanResult`.
- `services/control_api/services/deployer_service.py` — load and validate `deploy.yml`; execute steps sequentially via `subprocess_runner`; write JSON-lines log to `{runtime_root}/deployments/{project_id}/YYYYMMDD_HHMMSS.log`; expose `get_status()` / `get_logs(n)`.
- `services/control_api/services/profile_generator.py` — call Claude (via subprocess, reusing `run_step.py` patterns) with `ScanResult` as context, write generated YAML to `.ai-dev-factory/deploy.yml` in the project directory.
- Register deployer router in `services/control_api/main.py`.

### Backend — new schema models
- `services/control_api/models/schemas.py` additions:
  - `ScanResult` — detected components, stacks, tools, healthchecks
  - `DeployProfile` — parsed deploy.yml structure
  - `DeploymentStatus` — `{ state: idle|running|success|failed, started_at, finished_at, branch, last_error }`
  - `DeploymentLogEntry` — `{ timestamp, level, message, step }`

### Frontend — deployer page and API client
- `apps/dashboard/src/api/deployer.js` — `scan()`, `generateProfile()`, `deploy(branch)`, `restart()`, `getLogs()`, `getStatus()`.
- `apps/dashboard/src/pages/DeployerPage.jsx` — layout: status badge (idle/running/success/failed), six `ActionButton` components (Scan Project, Generate Profile, Deploy Main, Deploy Branch, Restart Services, View Logs), scrollable log viewer with auto-scroll, branch selector for "Deploy Branch".
- Add route `/projects/:projectId/deployer` in `apps/dashboard/src/App.jsx`.
- Add "Deployer" nav link in `apps/dashboard/src/components/ProjectSidebar.jsx`.
- Poll `getStatus()` and `getLogs()` at 5 s using the existing `usePolling` hook; surface running state as disabled buttons.

### Tests
- `tests/test_project_scanner.py` — unit tests for each detector (docker-compose, package.json, pyproject.toml, tool detection) using temp filesystem fixtures.
- `tests/test_deployer_service.py` — unit tests for step execution (mocked subprocess), log writing, `get_status()`, structured error on step failure.
- `tests/test_deployer_routes.py` — FastAPI test-client integration tests for all six endpoints: scan, generate-profile, deploy, restart, logs, status.

## Excluded

- Kubernetes, cloud autoscaling, multi-host deployment.
- Production secret management or encrypted credentials in `deploy.yml`.
- SaaS billing or licensing.
- Full CI/CD replacement (no webhook triggers, no PR-gating on deploy).
- Daemon state-machine changes — deployment is orthogonal to the ticket workflow.
- New SQLite tables — log storage is filesystem JSON-lines only.
- Concurrent branch deploys (single lock per project; second deploy request returns 409 while one is running).
- Multi-project parallel deploys (out of scope; each project deploys independently via its own route).
- Dashboard build/serve changes — only new React files and route registration.

## Acceptance criteria

- `GET /projects/{id}/deployer/status` returns `{ state: "idle" }` when no deploy has run.
- `POST /projects/{id}/deployer/scan` returns a `ScanResult` listing detected components and tools for ai-dev-factory.
- `POST /projects/{id}/deployer/generate-profile` writes `.ai-dev-factory/deploy.yml` into the target project directory and returns the parsed profile.
- `POST /projects/{id}/deployer/deploy` with `{ branch: "main" }` executes all steps in the profile sequentially; status transitions to `running` then `success` on clean run.
- A step failure returns `{ state: "failed", last_error: "<structured message>" }` — no silent failures.
- `GET /projects/{id}/deployer/logs` returns ordered log entries covering the last deploy run.
- Healthcheck steps are executed after docker/host service steps; a failing healthcheck causes the deploy to fail with a structured error.
- Dashboard `/projects/:id/deployer` page renders all six action buttons; buttons are disabled while state is `running`.
- `DeployerPage` polls status every 5 s and updates the log viewer without page reload.
- The ai-dev-factory `.ai-dev-factory/deploy.yml` file declares: `api` (docker), `web` (docker), `daemon` (host), required tools `gh`, `git`, `docker`, `claude`.
- `pytest tests/test_project_scanner.py tests/test_deployer_service.py tests/test_deployer_routes.py` passes.

---

## Review

# Plan review — T127

Decision: PLAN_FIX_REQUIRED

The deployer plan is promising but too large for one safe ticket.

Please reduce T127 to a V1 focused on:
- deploy profile format
- project scanner
- read-only deployer status
- no real deploy execution yet

See runs/T127/fixes/plan-fix-1.md for the requested smaller V1 scope.

---

## Instructions de fix

# Plan fix request — T127

The current deployer plan is promising but too large for one safe ticket.

Please reduce T127 to a smaller V1.

## T127 V1 objective

Introduce a minimal deployer foundation:
- deploy profile format
- project scanner
- read-only deployer status page
- no real deployment execution yet

## Include in V1

- Define `.ai-dev-factory/deploy.yml` schema.
- Add `.ai-dev-factory/deploy.yml` for ai-dev-factory.
- Add project scanner service.
- Add `GET /projects/{id}/deployer/status`.
- Add `POST /projects/{id}/deployer/scan`.
- Add minimal `DeployerPage` with:
  - Scan Project button
  - status display
  - detected components/tools display
- Add tests for:
  - scanner
  - deploy profile loading
  - deployer status route

## Exclude from V1

- No real deploy execution.
- No restart execution.
- No subprocess orchestration.
- No Claude profile generation.
- No deployment logs JSONL.
- No concurrent deployment locking.
- No branch deployment.
- No healthcheck execution.
- No host process management.

## Follow-up tickets

Later tickets can introduce:
- deploy execution
- restart execution
- healthchecks
- deployment logs
- Claude-assisted profile generation
- deploy orchestration
- environment bootstrap/install

## Acceptance criteria for fixed plan

- ai-dev-factory contains a valid `.ai-dev-factory/deploy.yml`.
- Scanner detects docker services and required tools.
- `/projects/{id}/deployer/status` returns a valid idle status.
- `/projects/{id}/deployer/scan` returns detected components.
- Dashboard deployer page loads successfully.
- Existing dashboard/runtime workflows are not broken.