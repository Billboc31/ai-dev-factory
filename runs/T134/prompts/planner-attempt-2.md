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



# T134 — T134 — Deploy and healthcheck fix loop in sandbox

**Source**: GitHub Issue #104

## Description

Add a deploy/test/fix loop inside isolated deployment sandboxes.

Scope:
- execute generated deployment scripts inside sandbox runtime
- run healthcheck.sh after deployment
- capture deployment and healthcheck logs
- detect deployment failures
- send failures/logs back to the configured AI runtime
- allow the AI runtime to update generated scripts and deployment files
- retry deployment after fixes
- configurable retry limit
- update PR branch with fixes
- dashboard visibility for deploy/test/fix iterations
- tests for deploy failure and retry loop

Out of scope:
- tester agent
- production deployment
- remote/cloud deployment
- auto-merge to main
- full E2E business testing

Acceptance:
- sandbox deploy loop can detect a failed deployment
- AI runtime can update scripts after a failed deployment
- deployment retries are visible in the dashboard
- successful healthcheck marks sandbox deploy as healthy
- retry limit stops infinite loops
- main runtime is never impacted by sandbox failures

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

## Objective

Add an automated deploy/test/fix loop inside sandbox deployments: when deployment or healthcheck fails, capture logs, send them to the AI runtime for script correction, apply fixes to the repo branch, and retry — up to a configurable limit — with each iteration visible in the dashboard.

## Included

**`services/control_api/services/deployer_runner.py`**
- Add `fixing` state to the deployment state machine (between `failed` and retry)
- Add `fix_iteration` counter and `max_fix_retries` field to deployment state
- Expose `failed_logs` (combined deploy + healthcheck stderr) as a structured field in state

**`services/control_api/services/fix_loop_manager.py`** *(new)*
- `start_fix_loop(project_id, deploy_yml_path, max_retries)` — orchestrates the full loop
- Reads failure logs from deployer_runner state
- Calls AI runtime (via existing supervisor/analysis_manager pattern) with: failed scripts, deploy config, and captured logs
- Receives and applies AI-returned file patches to the working branch
- Commits and pushes fixes to the PR branch (`git commit + git push`)
- Triggers re-deploy via deployer_runner
- Stops at `max_retries` and sets final state to `failed` with iteration history

**`services/control_api/routes/fix_loop.py`** *(new)*
- `POST /fix-loop/{project_id}/start` — body: `{max_retries: int}` — initiates loop in background thread
- `GET /fix-loop/{project_id}/status` — returns `{state, fix_iteration, max_fix_retries, history: [{iteration, result, log_excerpt}]}`

**`services/control_api/main.py`**
- Register new fix_loop router

**`apps/dashboard/src/api/deployer.js`**
- Add `startFixLoop(projectId, maxRetries)` and `getFixLoopStatus(projectId)` API calls

**`apps/dashboard/src/pages/DeployerPage.jsx`**
- Add "Fix Loop" section: shows current iteration / max, per-iteration result badges (fixing / retrying / success / failed), and a log excerpt per iteration
- "Start Fix Loop" button visible when deploy state is `failed`

**`tests/test_fix_loop.py`** *(new)*
- Test: failed deploy triggers fix loop entry
- Test: AI runtime receives correct payload (logs + scripts)
- Test: applied fix causes re-deploy and success
- Test: retry limit stops the loop and sets state to `failed`
- Test: successful healthcheck after fix marks state `healthy`/`success`

**`.ai-dev-factory/deploy.yml`**
- Add optional `fix_loop.max_retries` field (default: 3) to deploy profile schema

## Excluded

- Tester agent integration
- Production or remote/cloud deployment
- Auto-merge to main after successful fix loop
- Full end-to-end business logic testing
- Changes to the supervisor daemon's own retry policies (`_RETRY_POLICIES` in `run_daemon.py`)
- AI prompt engineering beyond passing logs + scripts as context

## Acceptance criteria

- A sandbox with a deliberately broken deploy script triggers the fix loop automatically after deploy or healthcheck failure
- Each fix iteration is recorded with its outcome and visible in the dashboard under the deploy entry
- The AI runtime receives the captured failure logs and the current script content in each fix request
- The PR branch is updated (commit + push) after each AI-generated fix
- When healthcheck passes after a fix, the deployment state is `success` and the loop stops
- When `max_fix_retries` is reached without success, the state is permanently `failed` with the full iteration history
- `tests/test_fix_loop.py` passes with all five test cases
- The main runtime process is unaffected by sandbox fix-loop failures (loop runs in an isolated thread per project)

---

## Review

# Plan review — T134

Decision: PLAN_FIX_REQUIRED

The current T134 plan is too ambitious for one safe ticket.

It jumps directly to a full AI fix loop:

- failed deploy detection
- AI-generated script fixes
- applying file patches
- committing and pushing fixes
- redeploy retries
- fix loop history
- new fix_loop router
- dashboard iteration UI

This is valuable, but it should come after a simpler sandbox deploy validation workflow exists.

## Requested change

Rewrite T134 as a V1 focused on the Deployer user workflow:

> Deploy & Test in Sandbox

The goal is to let the user click a button in the Deployer page that creates an isolated sandbox, runs the generated operational scripts, executes the healthcheck, captures logs, and reports success/failure.

Do not implement AI auto-fix yet.

See `runs/T134/fixes/plan-fix-1.md` for the requested reduced scope.

---

## Instructions de fix

# Plan fix — T134 V1

## New objective

Implement a first version of sandbox deployment validation from the Deployer UI.

The system must:

- create an isolated sandbox automatically
- create an isolated git worktree automatically
- execute generated operational scripts inside the sandbox
- execute healthcheck.sh
- capture logs and results
- expose deployment status in the dashboard

This ticket is intentionally limited to deployment validation.

AI auto-fix loops are excluded from this version.

---

# Included

## Deployer UI

Add a new action in Deployer page:

```text
Deploy & Test in Sandbox
```

The user must NOT manually provide:

- ticket id
- sandbox id
- runtime path
- worktree path

The system generates them automatically.

## Sandbox creation

Automatically create:

- isolated sandbox runtime
- isolated worktree
- isolated logs directory

under the runtime tree.

## Script execution flow

Execute in order:

1. bootstrap.sh
2. build.sh
3. start.sh
4. healthcheck.sh

Capture:

- stdout
- stderr
- exit codes
- execution timestamps

## Dashboard state

Expose:

- pending
- running
- success
- failed

with logs visible from the Deployer page.

## Runtime safety

The sandbox execution must NOT modify the main runtime environment.

All execution must occur in:

- isolated worktree
- isolated runtime directory
- isolated logs

## Tests

Add tests for:

- sandbox creation
- worktree creation
- successful deploy validation
- failed healthcheck
- log capture
- deploy state transitions

---

# Excluded

- AI-generated fix loops
- automatic script patching
- automatic commit/push after failures
- retry loops
- PR updates
- remote/cloud deployment
- tester-agent integration
- automatic port allocation
- parallel sandbox orchestration

---

# Acceptance criteria

- Deployer page exposes a Deploy & Test in Sandbox action
- A sandbox is automatically created
- A worktree is automatically created
- Generated scripts execute inside the sandbox
- healthcheck.sh determines success/failure
- Logs are visible in the dashboard
- Main runtime environment remains unaffected
- Failed validations stop cleanly with visible errors