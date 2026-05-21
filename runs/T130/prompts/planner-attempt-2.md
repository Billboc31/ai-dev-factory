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



# T130 — T130 — AI-assisted operational project analysis and deploy profile generation

**Source**: GitHub Issue #99

## Description

# T130 — AI-assisted operational project analysis and deploy profile generation

## Objective

Add an AI-assisted deployer workflow able to analyze any managed repository and generate reviewable operational documentation and deployment profiles.

The workflow must use the LLM runtime configured by the daemon/executor environment instead of hardcoding a specific AI provider.

## Included

- Add an “Analyze Project” action to the deployer UI.
- Use deterministic Python project scanning as structured context input.
- Send repository structure + scan result to the configured LLM runtime.
- Generate:
  - `.ai-dev-factory/deploy.yml`
  - `.ai-dev-factory/deployment.md`
  - optional `.ai-dev-factory/runtime-notes.md`
- Infer:
  - required tools
  - docker services
  - host-side processes
  - build commands
  - startup commands
  - restart commands
  - healthchecks
  - runtime dependencies
  - environment variables
  - known operational constraints
- Commit generated operational files to a dedicated branch.
- Create or update a PR for human review.
- Show analysis progress, logs and failures in the dashboard.
- Add tests for:
  - prompt generation
  - AI execution orchestration
  - file generation
  - Git branch workflow
  - PR creation/update

## Excluded

- Automatic deployment execution.
- Automatic install of missing dependencies.
- Automatic merge.
- Secrets management.
- Remote/cloud deployment orchestration.

## Acceptance criteria

- A user can trigger repository operational analysis from the dashboard.
- The configured LLM runtime analyzes the repository and generates reviewable operational files.
- Generated deploy.yml is valid and compatible with the deployer runtime.
- Generated documentation explains how to build/start/restart/check the project.
- Generated files are committed to a dedicated branch.
- A PR is created or updated automatically.
- Existing deployer/runtime workflows remain functional.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have a clear picture of the codebase. Here is the implementation plan.

---

## Objective

Add an AI-assisted "Analyze Project" workflow to the deployer: scan the repository deterministically, build a structured prompt, invoke the environment-configured LLM runtime, generate reviewable operational files (deploy.yml, deployment.md, optional runtime-notes.md), commit them to a dedicated branch, and open a PR — with full progress visibility in the dashboard.

## Included

### Backend — new schemas

**`services/control_api/models/schemas.py`**
- `AnalysisStatus` schema: `state` (idle/running/success/failed), `started_at`, `finished_at`, `error`, `branch`, `pr_url`
- `AnalysisResult` schema: list of generated file paths, inferred tools, services, env vars

### Backend — new services

**`services/control_api/services/analysis_prompt_builder.py`** (new)
- `build_analysis_prompt(project_root, scan_result) -> str`
- Assembles: repository file tree + existing `project_scanner.py` scan output + `DeployProfile` JSON schema spec + explicit generation instructions for `deploy.yml`, `deployment.md`, and optionally `runtime-notes.md`
- No LLM dependency; pure string construction (enables isolated unit testing)

**`services/control_api/services/project_analysis_service.py`** (new)
- `start_analysis(project_id, project_root) -> None` — acquires per-project `threading.Lock` (mirrors `deployer_runner.py`), spawns background thread, raises `409` if already running
- `_run_analysis(project_root) -> None` — orchestrates: scan → prompt build → LLM invocation → parse LLM output → write generated files → git branch/commit/push → gh pr create/update
- `get_analysis_status(project_id) -> AnalysisStatus` — reads `.ai-dev-factory/analysis-state.json`
- `get_analysis_logs(project_id, lines) -> list[str]` — tails `.ai-dev-factory/analysis.log`
- LLM exec_cmd read from `EXEC_CMD` env var (same pattern as daemon's `--exec-cmd` flag; no hardcoded provider)
- State written atomically to `.ai-dev-factory/analysis-state.json` (write-to-tmp + rename, matching existing state file conventions)
- Logs written to `.ai-dev-factory/analysis.log`

**`services/control_api/services/analysis_git_service.py`** (new)
- `commit_generated_files(project_root, branch_name, file_paths) -> None` — `git checkout -b {branch}`, `git add`, `git commit`
- `push_branch(project_root, branch_name) -> None` — `git push -u origin {branch}`
- `create_or_update_pr(project_root, branch_name, project_id) -> str` — `gh pr create` or `gh pr edit` if branch already has an open PR; returns PR URL

Branch naming convention: `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}`

### Backend — new routes

**`services/control_api/routes/deployer.py`** (extend existing)
- `POST /projects/{project_id}/deployer/analyze` — triggers analysis, returns `202 Accepted` + `AnalysisStatus`
- `GET /projects/{project_id}/deployer/analysis/status` — returns `AnalysisStatus`
- `GET /projects/{project_id}/deployer/analysis/logs?lines=100` — returns log tail

### Frontend — API client

**`apps/dashboard/src/api/deployer.js`** (extend existing)
- `analyzeProject(projectId)` — `POST /projects/{id}/deployer/analyze`
- `getAnalysisStatus(projectId)` — `GET /projects/{id}/deployer/analysis/status`
- `getAnalysisLogs(projectId, lines)` — `GET /projects/{id}/deployer/analysis/logs`

### Frontend — dashboard page

**`apps/dashboard/src/pages/DeployerPage.jsx`** (extend existing)
- "Analyze Project" action button, styled and positioned alongside existing "Deploy" / "Scan" / "Restart" buttons
- Analysis status panel: state badge, branch name, clickable PR link
- Scrollable analysis log tail (mirrors existing deploy log panel)
- Polling on 5 s interval while state is `running`, idle otherwise

### Tests

**`tests/test_analysis_prompt_builder.py`** (new)
- `test_prompt_contains_file_tree` — scan result tree present in output
- `test_prompt_contains_deploy_schema` — deploy.yml schema spec present
- `test_prompt_instructs_file_generation` — generation instructions for all three target files present
- `test_prompt_is_deterministic` — same inputs produce identical output

**`tests/test_project_analysis_service.py`** (new)
- `test_analysis_transitions_to_running` — state file shows `running` immediately after trigger
- `test_analysis_locking_rejects_concurrent_run` — second trigger raises `409`
- `test_analysis_writes_generated_files` — mock LLM output → verify `deploy.yml` + `deployment.md` written to project root
- `test_generated_deploy_yml_validates_against_schema` — output parseable as `DeployProfile`
- `test_analysis_failure_writes_failed_state` — mock LLM error → assert `failed` state + error message

**`tests/test_analysis_git_workflow.py`** (new)
- `test_commit_creates_correct_branch_name` — assert `git checkout -b ai-analysis/…` called with expected branch
- `test_pr_created_on_new_branch` — mock `gh`; assert `gh pr create` called, URL stored in state
- `test_pr_updated_on_existing_branch` — mock `gh pr list` returning open PR; assert `gh pr edit` called instead

## Excluded

- Automatic deployment execution after analysis completes
- Automatic install of missing runtime dependencies detected by the analysis
- Automatic merge of the generated PR
- Secrets detection or management
- Remote or cloud deployment orchestration
- Modification of the existing daemon ticket state machine or step types
- Analysis of non-Python/non-Node stacks beyond what `project_scanner.py` already detects

## Acceptance criteria

- `POST /projects/{id}/deployer/analyze` returns `202` and sets analysis state to `running`; a concurrent call returns `409`
- `GET /projects/{id}/deployer/analysis/status` reflects correct state transitions: `idle → running → success` (or `failed`)
- On success: `.ai-dev-factory/deploy.yml` and `.ai-dev-factory/deployment.md` exist in the project root; they are non-empty and UTF-8 valid
- Generated `deploy.yml` parses without error as `DeployProfile` using the existing Pydantic schema in `schemas.py`
- Generated files are committed to a branch named `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}`
- A PR is created (or updated) targeting the project default branch; `pr_url` is non-null in `AnalysisStatus`
- Dashboard renders "Analyze Project" button; clicking it triggers the endpoint; state and PR link update without page reload
- LLM runtime is resolved exclusively from the `EXEC_CMD` environment variable; no provider name or model is hardcoded in source
- `pytest tests/test_analysis_prompt_builder.py tests/test_project_analysis_service.py tests/test_analysis_git_workflow.py` passes
- All pre-existing deployer and daemon tests continue to pass (`pytest tests/` green)

---

## Review

# Plan review — T130

Decision: PLAN_FIX_REQUIRED

The plan is strong, but the execution location is wrong.

The current plan runs the AI analysis process directly from the control API.

That is not correct when the API runs inside Docker because it may not have access to the host AI runtime, gh, git worktrees, credentials, or the canonical runtime environment.

Requested fix:

Rewrite the plan so the dashboard/control API delegates Analyze Project to the host supervisor.

The supervisor should launch the host-side analysis job. The control API should only trigger it, read status, read logs, and display results.

See runs/T130/fixes/plan-fix-1.md for the reduced architectural correction.

---

## Instructions de fix

# Plan fix request — T130

Please update the architecture so AI project analysis runs through the host supervisor.

Required architecture:

Dashboard
→ Control API
→ Host supervisor
→ Host-side analysis worker
→ Git branch and PR

## Include in revised plan

- Add supervisor endpoints for analysis jobs.
- Supervisor launches the analysis worker host-side.
- Analysis worker uses the configured host AI runtime.
- Analysis worker has access to gh, git worktrees, host credentials and canonical runtime paths.
- Control API only triggers analysis, polls status, reads logs and exposes PR URLs.
- Analysis status and logs remain visible in the dashboard.
- Generated files are still committed and pushed from the host runtime.

## Exclude

- Direct LLM execution from Docker control API.
- Docker-side git branch creation.
- Docker-side PR creation.

## Acceptance criteria update

- Analysis jobs execute host-side through the supervisor.
- Generated files are committed using the host git runtime.
- PR creation uses the host gh runtime.
- Dashboard still provides analysis visibility.
- Existing supervisor and daemon architecture stays consistent.