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

## Artifact-only output (strict)

Your response will be written verbatim to `runs/<ticket>/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.

This rule applies to both initial plans and rewrites after a review.
Examples of forbidden openings: "The plan has been rewritten…",
"This plan now covers…", "Plan rewritten as a real implementation
document…", "Key points covered…", "The document now contains…",
"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".

Do not use the Write tool on `plan.md` and then print a status summary —
your stdout IS the artifact. If you do write the file, stdout must still
be the full plan (same four headings), not a report about it.

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



# T229 — Add one-click project deployment for end-to-end validation

**Source**: GitHub Issue #305

## Description

# Context

After AI Dev Factory finishes implementing a project, there is currently no standard workflow to deploy the generated application for functional validation.

Being able to deploy a project with a single action is essential for demonstrations and for the human validation loop before writing UI/non-regression tests.

# Goal

Add a deployment stage allowing a generated project to be deployed easily so it can be tested by a human.

# Description

Implement a first deployment workflow that:

- detects whether a project is deployable;
- executes the project's deployment pipeline;
- exposes the deployment status in the dashboard;
- stores deployment history and logs;
- returns the deployed application URL when successful.

The deployment should become a reusable platform capability so future project templates can integrate with it.

# Out of Scope

- Automatic production deployments.
- Blue/green or canary deployments.
- Rollback strategies.
- Multi-environment management.
- Automatic UI validation.
- Automatic creation of regression tests.

# Acceptance Criteria

- A project can be deployed from AI Dev Factory.
- Deployment progress is visible in the dashboard.
- Success and failure states are persisted.
- Deployment logs are available for troubleshooting.
- The deployed application's URL is stored and displayed.
- Deployment can be retried after a failure.
- Existing workflows remain unchanged when deployment is not used.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T229/plan.md`.
You MUST rewrite that file with the corrected plan. Leaving it
unchanged is rejected by the factory.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

Now I have enough context. Here is the plan:

## Objective

Add a one-click deployment action for workspace projects so a human can deploy and validate a generated application directly from the AI Dev Factory dashboard, without touching the terminal.

## Included

**Supervisor — new deployment endpoint and background job handler**
- `services/supervisor/main.py`: add `POST /workspace/projects/{project_id}/deploy` endpoint, mirroring the `redeploy_project` pattern (T227, lines 3622–3797); add `deploy_project` background handler that:
  1. reads the project's deploy config (checks for `deploy.yml` or `docker-compose.yml` in the repository path defined in `workspace_projects.yml`);
  2. returns `422 Unprocessable Entity` with `not_deployable` reason if no config is found (deployability check);
  3. runs the deployment pipeline (e.g. `docker compose up -d --build` or custom deploy command from config);
  4. captures stdout/stderr line by line into an in-memory log buffer;
  5. resolves the `preview_url` from config once the pipeline succeeds;
  6. writes final state to a new per-project JSON file `.ai-dev-factory/project-deploy-state.json` (status, started_at, completed_at, preview_url, deployed_sha);
  7. appends log lines to `.ai-dev-factory/project-deploy.log`.
- `services/supervisor/main.py`: add `GET /workspace/projects/{project_id}/deploy/{deployment_id}` polling endpoint (same shape as existing deployment status endpoint at lines ~2907-2908).
- `services/supervisor/main.py`: add `GET /workspace/projects/{project_id}/deploy/history` endpoint returning the last N deployment records (read from `project-deploy-state.json`).

**workspace_projects.yml schema extension**
- Add optional `deploy` block to the per-project config schema (alongside existing `redeploy` block):
  ```yaml
  deploy:
    command: docker compose up -d --build   # or path to a deploy script
    preview_url: http://localhost:3000
    healthcheck: curl -sf http://localhost:3000/health
  ```
- Document the new key in `workspace_projects.example.yml`.

**Dashboard frontend**
- `apps/dashboard/src/api/workspace.js`: add `deployProject(projectId)` and `getDeployStatus(projectId, deploymentId)` and `getDeployHistory(projectId)` API functions.
- `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`: add a "Deploy project" button (reuse `ActionButton` pattern); wire polling loop (reuse `usePolling` hook) to display live stage and log tail; show `preview_url` as a clickable link on success; show retry button on failure.
- `apps/dashboard/src/components/DeployHistoryPanel.jsx` *(new small component)*: renders the last N deployments (timestamp, status badge, URL, link to logs) fetched from the history endpoint; embedded inside `ProjectWorkspacePanel`.

**Existing workflows left unchanged**
- The existing `deployer_runner.py` / `DeployerPage.jsx` (which deploys ai-dev-factory itself) is not modified.
- The T227 `redeploy_project` handler is not modified.

## Excluded

- Automatic production deployments.
- Blue/green, canary, or rollback strategies.
- Multi-environment management.
- Automatic UI validation or regression test generation.
- Kubernetes / cloud-provider integrations.
- Deployment config generation for projects that do not already have a `deploy.yml` or `docker-compose.yml` (a separate ticket should handle scaffolding).
- Migrating existing deployment history from another source.
- Authentication / access control on the new endpoints (inherits whatever the supervisor currently uses).

## Acceptance criteria

- `POST /workspace/projects/{project_id}/deploy` returns `422` with `not_deployable` if the project has no detected deploy config; returns `200` with a `deployment_id` otherwise.
- `GET /workspace/projects/{project_id}/deploy/{deployment_id}` returns a status object with `stage`, `status` (`running` / `succeeded` / `failed`), `log_tail` (last 50 lines), and `preview_url` (populated on success).
- On success, `.ai-dev-factory/project-deploy-state.json` is written with `status=succeeded`, `preview_url`, `deployed_sha`, and timestamps.
- On failure, status is `failed` and the log tail contains the relevant error output.
- The dashboard "Deploy project" button triggers the endpoint, shows live stage progression, and displays the URL as a clickable link when done.
- A failed deployment can be retried by clicking the button again (no 409 conflict once the previous job is finished).
- `GET /workspace/projects/{project_id}/deploy/history` returns the last 5 deployment records.
- All existing workspace actions (pull, redeploy) work without change.
- `workspace_projects.example.yml` documents the new `deploy` block.

---

## Review

# PLAN_FIX_REQUIRED

## Summary

The deployment plan is directionally correct, but several issues must be fixed before implementation because they affect execution safety, concurrency, deployment correctness, history persistence, and end-to-end validation semantics.

## Blocking issues

### 1. Do not execute free-form shell commands from deploy config

The proposed schema allows arbitrary values such as:

```yaml
deploy:
  command: docker compose up -d --build
  healthcheck: curl -sf http://localhost:3000/health
```

This must not become `shell=True` or equivalent free-form command execution.

Prefer a declarative deployment configuration, for example:

```yaml
deploy:
  type: docker-compose
  compose_file: docker-compose.yml
  preview_url: http://localhost:3000
  healthcheck_url: http://localhost:3000/health
```

If custom scripts are supported, they must be repository-relative, validated after path normalization, already present in the repository, and executed without `shell=True`. Frontend or LLM input must never provide arbitrary command strings, paths, service names, or shell arguments.

### 2. `docker-compose.yml` presence alone must not imply deployability

A repository containing a compose file is not automatically safe or meaningful to deploy. Define an explicit deployment policy and precedence. Prefer an explicit `deploy` config as the source of truth, with any compose auto-detection limited to a conservative documented fallback.

### 3. Deployment history needs a real persistence model

`project-deploy-state.json` cannot simultaneously represent only the latest state and also provide the last five deployment records unless its schema explicitly contains history.

Define either:

- separate `project-deploy-state.json` and `project-deploy-history.json`, or
- one structured document containing `latest` plus bounded `history`.

Retention and atomic writes must be defined.

### 4. Add atomic per-project deployment concurrency protection

Only one deployment may run per project at a time. A second POST while one is active must return HTTP 409 with a structured `DEPLOYMENT_IN_PROGRESS` response. The check-and-register operation must be atomic and cleanup must happen in `finally`, including after exceptions or timeouts.

### 5. Define deployed SHA and dirty-working-tree policy

Capture `git rev-parse HEAD` before starting the deployment and attach it to the deployment record. Define what happens when the working tree is dirty. The plan should reject dirty deployments by default unless an explicit project-level policy allows them.

### 6. Define the deployment job registry contract

Each job should have a stable `deployment_id` and server-side state containing at least:

- `deployment_id`
- `project_id`
- `stage`
- `status`
- `started_at`
- `completed_at`
- `deployed_sha`
- `log_tail`
- `preview_url`
- `error`

Polling must validate that a deployment belongs to the requested `project_id`.

### 7. Healthcheck must be part of deployment success

A successful build/start command alone is not sufficient for an end-to-end validation deployment. Define stages such as:

`BUILDING -> STARTING -> HEALTHCHECK -> SUCCEEDED`

If a healthcheck is configured, the deployment must only become `succeeded` after it passes. Define timeout, retry interval, retry count, and clear failure reporting.

### 8. Bound and sanitize deployment logs

Do not keep unlimited stdout/stderr in memory or return unbounded logs through polling. Keep only a bounded tail in memory (at least the acceptance-criterion 50 lines), define file rotation/retention, and redact obvious secret values before exposing logs in the dashboard.

## Required tests

Add tests covering at minimum:

- no deploy config -> 422 `not_deployable`;
- invalid deploy config -> explicit 422;
- concurrent deployment -> second request returns 409;
- per-project lock/session released after exception;
- deployed SHA captured before launch;
- dirty repository follows the chosen policy;
- arbitrary command/script/path/service values are rejected;
- successful healthcheck;
- deploy command success + healthcheck failure -> failed;
- healthcheck timeout -> failed;
- history retains and returns the last five deployments;
- deployment ID cannot be queried under another project;
- polling `log_tail` is bounded to 50 lines;
- retry is allowed after a terminal state;
- frontend disables/restricts duplicate deploy while active;
- frontend displays preview URL only after success;
- frontend renders `not_deployable` cleanly.

## Decision

PLAN_FIX_REQUIRED

---

## Instructions de fix

# Plan Fix Instructions — T229

Revise `runs/T229/plan.md` to incorporate all blocking points from `runs/T229/reviews/plan-review-01.md`.

## Required changes

1. Replace free-form `deploy.command` / shell-style `healthcheck` execution with a declarative, server-controlled deployment model. Prefer structured fields such as deployment type, repository-relative compose/script selection, `preview_url`, and `healthcheck_url`. Do not allow frontend/LLM-supplied shell commands or arbitrary filesystem paths. If custom scripts are supported, constrain them to validated repository-relative files and execute without `shell=True`.

2. Define deployability explicitly. Do not treat the mere existence of `docker-compose.yml` as sufficient. Specify source-of-truth precedence, preferably explicit project `deploy` config first, with only a conservative documented fallback if retained.

3. Define persistent deployment history correctly. Use either separate latest-state/history files or one bounded structure containing both. The history endpoint must deterministically return the last five deployment records, and writes must not corrupt previous history.

4. Add atomic per-project concurrency protection. Only one deployment may be active per project. A concurrent POST must return HTTP 409 `DEPLOYMENT_IN_PROGRESS`. Register/check under a lock and guarantee cleanup in `finally` after success, failure, timeout, or unexpected exception.

5. Capture `git rev-parse HEAD` before deployment and persist it as `deployed_sha`. Explicitly define the working-tree dirty policy; default to refusing dirty deployments unless a project-level option deliberately allows them.

6. Define a deployment job/session registry with stable `deployment_id`, `project_id`, `stage`, `status`, timestamps, SHA, bounded log tail, preview URL, and error. Polling must verify that the deployment belongs to the project in the route.

7. Make healthcheck part of success semantics. Define deployment stages such as `BUILDING`, `STARTING`, `HEALTHCHECK`, then `SUCCEEDED`/`FAILED`. If configured, healthcheck failure or timeout must make the deployment fail even if the build/start command succeeded. Specify timeout/retry/interval behaviour.

8. Bound deployment logs. Keep the polling tail to the last 50 lines, define persistent log retention/rotation, and avoid exposing obvious secrets in dashboard-visible logs.

9. Add explicit backend and frontend tests for all of the above, including 422 non-deployable/invalid config, 409 concurrency, lock release on exception, dirty-tree policy, SHA capture, unsafe config rejection, healthcheck success/failure/timeout, five-entry history retention, cross-project deployment-id rejection, bounded logs, retry after terminal state, and dashboard behaviour.

## Preserve

Keep the good parts of the current plan:

- workspace project deployment remains separate from AI Dev Factory's own deployer;
- T227 redeploy behaviour is not changed;
- execution remains asynchronous with polling;
- production/cloud/Kubernetes/rollback/multi-environment features remain out of scope;
- the dashboard exposes a one-click action, progress, logs, retry, and preview URL.

## Expected result

Rewrite `runs/T229/plan.md` with a materially revised plan that incorporates these constraints and includes verifiable acceptance criteria and tests. Do not merely describe these requested fixes in prose outside the plan.