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



# T135 — T135 — Isolated analysis and deploy worktrees

**Source**: GitHub Issue #108

## Description

Add isolated worktree and runtime environments for AI analysis, deploy generation and deploy validation workflows.

Scope:
- create dedicated analysis/deploy worktrees per ticket or job
- map Docker container paths to host worktree paths correctly
- isolated runtime roots
- isolated compose project names
- isolated env files and ports
- cleanup of completed/failed worktrees
- dashboard visibility for sandbox/worktree state
- tests for worktree isolation and host path mapping

Out of scope:
- deploy/test/fix retry loop
- tester agent
- production deployment
- remote/cloud deployment

Acceptance:
- analysis jobs never run against the main runtime worktree
- supervisor always receives valid host paths
- generated files are committed from isolated worktrees
- sandbox deploys cannot impact the main runtime
- cleanup works correctly
- existing daemon/runtime workflows continue to work

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have enough context to write the implementation plan.

## Objective

Introduce per-job isolated git worktrees and runtime environments for analysis and deploy workflows so that no analysis or deploy job touches the main runtime worktree, and so that the supervisor always operates on valid host filesystem paths rather than Docker-internal paths.

## Included

### Path mapping — Docker container paths → host paths

- **`services/supervisor/path_mapper.py`** *(new)* — `ContainerToHostMapper` class that reads two env vars (`CONTAINER_RUNTIME_ROOT`, `HOST_RUNTIME_ROOT`) and translates any container-side path to its host equivalent. Used by supervisor before spawning subprocesses.
- **`services/supervisor/main.py`** — import and apply `ContainerToHostMapper` to `project_root` received in `POST /analysis/start` and `POST /scripts/start` before passing paths to subprocesses. Expose current mapper config in `GET /supervisor/status`.
- **`deploy/.env.example`** — add `HOST_RUNTIME_ROOT` and `CONTAINER_RUNTIME_ROOT` vars with documentation.
- **`deploy/start_supervisor.sh`** — forward `HOST_RUNTIME_ROOT` env var to the supervisor process.

### Isolated analysis/deploy worktrees

- **`tools/agent_runner/run_analysis.py`** — at startup, create a dedicated git worktree at `RUNTIME_ROOT/worktrees/analysis-{job_id}/` (using existing `worktree_manager.create_ticket_worktree()` with a synthetic branch name `analysis/{job_id}`); run all scanning, LLM call, file writes and `git commit/push` inside that worktree; write the worktree path into the job state JSON; remove the worktree on exit (both success and failure paths).
- **`tools/agent_runner/run_scripts.py`** — same pattern: isolated worktree `scripts/{job_id}`, lifecycle identical to run_analysis.py.

### Isolated runtime roots per job

- **`services/control_api/services/runtime_resolver.py`** — add `analysis_job_dir(job_id)` and `scripts_job_dir(job_id)` helpers that return `RUNTIME_ROOT/jobs/analysis-{job_id}/` and `.../scripts-{job_id}/` respectively (subdirectories with their own `state.json`, `logs/`).
- **`tools/agent_runner/run_analysis.py`** and **`run_scripts.py`** — write state/log output to the job-specific directory rather than the shared `state/` directory. Keep a symlink or forwarding entry in `state/analysis-{project_id}.json` pointing to the latest job for backwards compatibility with existing API polling routes.

### Isolated compose project names, env files and ports (deploy validation)

- **`services/control_api/services/sandbox_manager.py`** — add `create_deploy_sandbox(job_id, project_root, worktree_path)` that reuses existing slot/port allocation and produces a compose env file inside the job worktree (`RUNTIME_ROOT/jobs/scripts-{job_id}/.env`), setting a unique `COMPOSE_PROJECT_NAME=ai_devfactory_deploy_{job_id}`. Wire this into the deploy validation step in `run_scripts.py`.

### Cleanup

- **`tools/agent_runner/run_analysis.py`** and **`run_scripts.py`** — unconditional `try/finally` cleanup: `remove_ticket_worktree(worktree_path, force=True)` after job exits.
- **`services/supervisor/main.py`** — on `POST /analysis/stop` and `POST /scripts/stop`, issue cleanup signal to running job (SIGTERM); log worktree cleanup confirmation.
- **`services/control_api/routes/deployer.py`** — add `POST /projects/{project_id}/deployer/analysis/cleanup` endpoint that triggers supervisor cleanup for a named job.

### Dashboard visibility

- **`services/control_api/routes/deployer.py`** — extend `GET /projects/{project_id}/deployer/analysis/status` response to include `worktree_path`, `job_runtime_dir`, `compose_project` (if applicable).
- **`apps/dashboard/src/api/deployer.ts`** *(or equivalent API client file)* — add `worktreePath`, `jobRuntimeDir` fields to the analysis status type.
- **`apps/dashboard/src/components/`** — add a small `WorktreeInfo` component displayed within the existing analysis status card, showing worktree path, isolation status (isolated / main), and compose project name when relevant.

### Tests

- **`tests/test_analysis_worktree_isolation.py`** *(new)* — verifies that `run_analysis.py` creates an isolated worktree, never touches the main project root, and cleans up the worktree on both success and failure paths. Uses `tmp_path` and mocked LLM subprocess.
- **`tests/test_host_path_mapping.py`** *(new)* — unit-tests `ContainerToHostMapper`: correct translation, identity when env vars not set, path-within-subdir preservation, no mutation of unrelated paths.
- **`tests/test_scripts_worktree_isolation.py`** *(new)* — same pattern as analysis test but for `run_scripts.py` and deploy sandbox creation.

## Excluded

- Deploy/test/fix retry loop and tester agent (separate ticket).
- Production and remote/cloud deployment.
- Distributed multi-daemon coordination.
- Migrating existing historical state files to the new job-scoped layout.
- Rollback / revert of deployed sandboxes.
- Audit logging, rate limiting, backpressure.

## Acceptance criteria

- Running `run_analysis.py` creates a new directory under `RUNTIME_ROOT/worktrees/analysis-*/` and writes no files directly into `project_root` (verified by test mocking `worktree_manager` and asserting call args).
- `ContainerToHostMapper.map("/runtime/ai-dev-factory/runs/T100")` returns `"/Users/pierre/runtime/ai-dev-factory/runs/T100"` when `CONTAINER_RUNTIME_ROOT=/runtime/ai-dev-factory` and `HOST_RUNTIME_ROOT=/Users/pierre/runtime/ai-dev-factory`.
- After a simulated analysis job exits (success or error), `RUNTIME_ROOT/worktrees/analysis-{job_id}/` no longer exists.
- Two concurrent analysis jobs allocate different ports and different `COMPOSE_PROJECT_NAME` values; stopping one does not affect the other.
- `GET /projects/{project_id}/deployer/analysis/status` response includes a non-null `worktree_path` field while a job is running.
- The dashboard analysis status card displays the worktree path field.
- All existing tests (`pytest tests/`) continue to pass without modification.

---

## Review

# Plan review — T135

Decision: PLAN_FIX_REQUIRED

The current plan is directionally correct, but too large for one safe ticket.

It mixes too many concerns at once:

- Docker-to-host path mapping
- isolated analysis worktrees
- isolated script-generation worktrees
- job-scoped runtime directories
- sandbox compose project names and ports
- cleanup endpoints
- dashboard worktree visibility
- multiple new test suites

This is a critical isolation layer. It should be introduced in a smaller V1 before extending it to scripts and deploy sandboxes.

Requested action:

Rewrite T135 as a minimal V1 focused only on host path mapping and isolated analysis worktrees.

See `runs/T135/fixes/plan-fix-1.md` for the requested reduced scope.

---

## Instructions de fix

# Plan fix request — T135

Please reduce T135 to a minimal isolation V1.

## T135 V1 objective

Introduce safe isolated analysis worktrees and correct Docker-to-host path mapping for supervisor analysis jobs.

The goal of V1 is only:

- analysis jobs never run directly in the main runtime worktree
- supervisor never receives invalid Docker container paths like `/app`

## Include in V1

### Docker → host path mapping

- Add a small path-mapping utility.
- Translate container paths to host paths before supervisor subprocess execution.
- Add tests for path translation.
- Add clear logs showing:
  - container path
  - mapped host path

### Isolated analysis worktrees

- `run_analysis.py` creates a dedicated isolated worktree.
- Analysis, file generation and git operations run only inside the isolated worktree.
- Worktree cleanup runs in `finally` blocks.
- Add tests ensuring analysis jobs never write directly into the main runtime worktree.

### Minimal dashboard visibility

- Expose worktree path in analysis status.
- Display worktree isolation status in the dashboard.

## Exclude from V1

- `run_scripts.py`
- deploy sandbox runtime
- compose project isolation
- dynamic ports
- isolated env files
- cleanup endpoints
- full job runtime layout redesign
- deploy/test/fix loop
- tester agent

## Acceptance criteria

- Supervisor receives valid host filesystem paths instead of `/app`.
- Analysis jobs create isolated worktrees.
- Generated files and commits occur only inside isolated worktrees.
- Worktrees are cleaned after job completion.
- Dashboard displays analysis worktree path.
- Existing daemon/runtime workflows continue to work.