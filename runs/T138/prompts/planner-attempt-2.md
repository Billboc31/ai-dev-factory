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



# T138 — T138 — Generic AI sandbox auto-fix loop

**Source**: GitHub Issue #124

## Description

# Objective

Add a generic AI-driven sandbox auto-fix loop able to analyze sandbox deployment failures, modify operational artifacts, rerun validation, and converge toward a successful runtime state.

The implementation must remain generic and must NOT contain ai-dev-factory-specific deployment assumptions.

## Context

T134 introduced sandbox deploy validation.

T137 introduces:
- isolated sandbox ports
- sandbox env files
- compose project isolation
- sandbox lifecycle management
- historical sandbox runs

The next step is an automated correction loop:

sandbox validation fails
→ logs captured
→ AI analyzes failure
→ AI modifies scripts/config
→ sandbox reruns
→ repeat until success or retry limit

## Included

### Generic auto-fix orchestration

- Add a sandbox auto-fix orchestrator.
- Retry loop must be bounded with configurable max retries.
- Each iteration must:
  - capture sandbox state
  - capture logs
  - capture operational scripts
  - call the configured AI runtime
  - apply modifications
  - rerun sandbox validation

### Generic project support

The loop must NOT assume:
- ai-dev-factory project structure
- api/web services
- fixed ports
- docker-only projects
- specific frameworks

The loop must rely on:
- deploy.yml
- sandbox state
- generated operational scripts
- runtime logs
- component definitions
- deploy metadata

### AI fix payload

Provide the AI runtime with:
- deploy profile
- sandbox state
- logs
- failing step
- operational scripts
- relevant runtime metadata

### Safe file modification

- Restrict modifications to allowed operational files.
- Track changed files per iteration.
- Persist iteration history.
- Never modify unrelated runtime state.

### Sandbox rerun

- After fixes are applied:
  - rerun validation
  - capture new logs/state
  - compare iterations

### Dashboard UI

Add auto-fix visibility:
- current iteration
- max retries
- iteration status
- changed files
- logs per iteration
- final outcome

### Failure handling

Handle safely:
- invalid AI output
- malformed patches
- repeated failures
- infinite retry risks
- sandbox crashes
- supervisor disconnects

### Tests

Add tests for:
- successful convergence after fix
- retry limit reached
- malformed AI output
- patch application failure
- generic deploy.yml handling
- iteration history persistence

## Excluded

- automatic merge to main
- production deployment
- cloud deployment
- tester-agent business tests
- self-modifying core runtime outside allowed sandbox artifacts

## Acceptance criteria

- sandbox failures can trigger a generic AI correction loop
- the loop works without ai-dev-factory-specific assumptions
- retries are bounded and observable
- iteration history is persisted and visible
- sandbox reruns after fixes
- malformed AI output is safely rejected
- the system never enters infinite retry loops
- successful fixes result in sandbox success state
- failed retries result in clean terminal failed state

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Here is the implementation plan for T138:

---

## Objective

Add a generic AI-driven sandbox auto-fix loop that, on validation failure, captures sandbox state and operational scripts, calls the configured AI runtime, applies patches restricted to allowed operational files, reruns validation, and repeats until success or a configurable retry limit is reached — without any ai-dev-factory-specific assumptions.

## Included

### Models — `services/control_api/models/auto_fix.py`
- `AutoFixStatus` enum: `idle`, `running`, `success`, `failed`, `error`
- `AutoFixIteration`: per-iteration record — iteration number, status, failing step, changed files list, log excerpt, sandbox run ID
- `AutoFixState`: top-level state — project_id, auto_fix_id, status, current_iteration, max_retries, iterations list, started_at, finished_at, final_sandbox_id

### Supervisor orchestrator — `services/supervisor/auto_fix_orchestrator.py`
- `AutoFixOrchestrator` class, async
- `run(project_id, max_retries)`: acquires per-project lock; loop: trigger sandbox run → if success → done; if failed → collect context → call AI → validate patches → apply patches → persist iteration state → repeat; exits with `failed` when max_retries reached
- State written after every iteration to `${RUNTIME_ROOT}/auto-fix/{project_id}/{auto_fix_id}/state.json`
- `_collect_context(sandbox_state, logs, scripts_dir)` → generic dict (deploy.yml content, component list, failing step, logs, scripts, iteration number); no hardcoded service names or ports
- `_call_ai(context)` → list of `{relative_path, content}` patch objects using Claude Messages API (claude-sonnet-4-6)
- `_validate_patches(patches, allowed_files)` → rejects any path outside allowed set
- `_apply_patches(project_root, patches)` → writes files atomically, returns changed paths
- `_allowed_files(project_root)` → restricted to `.ai-dev-factory/scripts/*.sh` only

### Supervisor endpoints added to `services/supervisor/main.py`
- `POST /auto-fix/{project_id}` — `{max_retries: int}`; spawns async task; returns `{auto_fix_id}`
- `GET /auto-fix/{project_id}` — returns current `AutoFixState`
- `GET /auto-fix/{project_id}/history` — list of all past `AutoFixState` records
- `DELETE /auto-fix/{project_id}/{auto_fix_id}` — removes state directory

### Control API — `services/control_api/services/auto_fix_runner.py` + `routes/auto_fix.py`
- HTTP-proxy client (`AutoFixRunner`) mirroring the `SandboxRunner` pattern
- Routes: `POST/GET /api/projects/{project_id}/auto-fix`, `GET /api/projects/{project_id}/auto-fix/history`
- Registered in `services/control_api/main.py`

### Dashboard — `apps/dashboard/src/components/AutoFixPanel.jsx` + `src/api/autoFix.js`
- Trigger button with max_retries input (default 5)
- Status badge, progress bar (current_iteration / max_retries)
- Iterations accordion: status, failing step, changed files, log excerpt per iteration
- Final outcome section; polls GET every 3 s while `running`
- Registered in `apps/dashboard/src/App.jsx`

### Tests
- `tests/test_auto_fix_orchestrator.py`: successful convergence, retry limit exhausted, malformed AI output rejected, disallowed file path rejected, patch I/O failure handled, generic deploy.yml (no hardcoded services), iteration state persisted mid-loop
- `tests/test_auto_fix_routes.py`: trigger returns auto_fix_id, status returns AutoFixState, history returns list

## Excluded
- Automatic merge to main after successful auto-fix
- Production/cloud deployment support
- Modifying files outside `.ai-dev-factory/scripts/*.sh`
- Tester-agent business-level tests
- Self-modifying core runtime outside allowed sandbox artifacts
- UI display of raw AI prompts/full response payloads
- Multi-project concurrent auto-fix coordination
- Auto-triggering on sandbox failure (manual trigger only in this ticket)

## Acceptance criteria
- `POST /api/projects/{project_id}/auto-fix` triggers the loop and returns an `auto_fix_id`; `GET` reflects live state while running
- Loop terminates at most after `max_retries` iterations; `AutoFixState.status` is `failed` with full iteration history at the limit
- Malformed or out-of-scope AI output is rejected without crashing the orchestrator; affected iteration recorded as `error`
- Iteration state written to disk after every iteration, readable independently of the running process
- Each iteration reruns sandbox validation and captures new logs and state
- Successful fix sets `AutoFixState.status = success` with `final_sandbox_id` populated
- Dashboard renders current_iteration/max_retries progress, per-iteration details, and final outcome
- No ai-dev-factory-specific service names, fixed ports, or project paths hardcoded in orchestrator or models
- `pytest tests/test_auto_fix_orchestrator.py tests/test_auto_fix_routes.py` passes

---

The plan is saved to `runs/T138/plan.md`. The core architectural choice is to place the AI call and orchestration loop in the supervisor (host-side), which already owns path mapping, per-project locking, and subprocess management — the control API and dashboard simply proxy through it as they do for existing sandbox features.

---

## Review

# Plan review — T138

Decision: PLAN_FIX_REQUIRED

The current T138 plan is too ambitious for a first auto-fix iteration.

It combines in a single ticket:

- AI orchestration
- async supervisor runtime
- automatic patch application
- sandbox reruns
- retry loops
- iteration persistence
- dashboard orchestration UI
- history endpoints
- AI provider integration
- automatic convergence logic

This should be split into smaller runtime-safe steps.

The first implementation should focus on a safe and observable dry-run proposal workflow.

Do not automatically modify operational artifacts or rerun sandboxes yet.

See `runs/T138/fixes/plan-fix-1.md`.

---

## Instructions de fix

# Plan fix — T138 V1

## New objective

Implement a safe dry-run AI auto-fix proposal workflow.

The system should:

- collect sandbox failure context
- call the configured AI runtime
- generate operational patch proposals
- validate allowed file paths
- expose proposed changes in the dashboard

The system must NOT automatically apply fixes or rerun validation yet.

This ticket intentionally focuses on:

- observability
- patch proposal generation
- safe validation
- generic project support

before introducing automatic execution loops.

---

# Included

## Failure context collection

Collect:

- sandbox state
- failing step
- sandbox logs
- deploy.yml
- operational scripts
- sandbox metadata

No ai-dev-factory-specific assumptions.

## Generic AI integration

Use the configured AI runtime abstraction.

Do NOT hardcode:

- Claude APIs
- specific models
- ai-dev-factory-specific prompts

The AI request must remain generic and runtime-configurable.

## Patch proposal generation

The AI runtime returns:

- proposed file modifications
- target relative paths
- reasoning summary

## Allowed files validation

Restrict modifications to allowed operational artifacts only.

Reject:

- path traversal
- runtime/core modifications
- unrelated project files

## Dashboard proposal UI

Add a dry-run proposal panel showing:

- sandbox id
- failing step
- proposed changed files
- patch preview
- AI reasoning summary
- proposal status

## Persistence

Persist proposal state to disk.

## Tests

Add tests for:

- generic deploy.yml handling
- malformed AI output
- disallowed paths
- patch proposal persistence
- proposal rendering state

---

# Excluded

- automatic patch application
- sandbox reruns
- retry loops
- automatic convergence
- automatic merge
- production deployment
- tester-agent integration
- async orchestration loops

---

# Acceptance criteria

- sandbox failure context can be collected generically
- the configured AI runtime can generate patch proposals
- invalid or dangerous proposals are rejected safely
- proposals are persisted and visible in the dashboard
- no files are automatically modified
- no sandbox reruns occur automatically
- no ai-dev-factory-specific assumptions exist in the workflow