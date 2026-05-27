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



# T153 — T153 — Generic smoke tests and bounded auto-fix deployment loop

**Source**: GitHub Issue #158

## Description

Goal: make the Deployer able to converge toward a functional ephemeral environment by running healthchecks, smoke tests, and a bounded AI auto-fix loop.

Context:
The intended Deployer flow is not just `docker compose up`.

Expected Deployer role:
- audit the project
- generate/update deployment scripts
- deploy an ephemeral sandbox environment
- run healthchecks
- run real smoke tests
- if validation fails, ask the configured AI runtime to propose/apply safe fixes
- redeploy and retest
- repeat until success or retry limit
- cleanup/undeploy automatically after success

Current limitation:
- we mostly have healthchecks today
- healthchecks only prove that services respond
- they do not prove that the application actually works
- auto-fixing only against healthchecks risks optimizing for "starts" rather than "works"

Scope:

1. Generic smoke test layer
- define a generic smoke test lifecycle after healthcheck
- support generated project-specific smoke tests
- prefer `.ai-dev-factory/scripts/smoke.sh` or equivalent lifecycle declaration
- smoke tests must use sandbox/proxy URLs when available
- fallback to allocated direct ports only when proxy URLs are absent
- smoke test output must be captured in logs and state

2. Deployer validation pipeline
- deploy ephemeral sandbox
- run healthcheck
- run smoke tests
- collect result state:
  - health status
  - smoke test status
  - failing step
  - logs
  - generated artifacts

3. Bounded AI auto-fix loop
- on failure, collect context and call the configured AI runtime
- no hardcoded provider or Claude-specific SDK
- use existing exec_cmd / AI runtime abstraction
- restrict modifications to allowed deployment artifacts first:
  - `.ai-dev-factory/scripts/*`
  - deploy profile files
  - compose/env/deployment config files explicitly allowed by policy
- apply patch in sandbox/worktree only
- redeploy and retest
- repeat up to configurable max retries
- stop if the same failure repeats without progress
- persist iteration history

4. Safety and observability
- max retry limit required
- each iteration records:
  - failure reason
  - changed files
  - patch summary
  - health result
  - smoke result
  - logs
- never merge automatically
- never modify unrelated application source files in this first version
- final diff must be visible and reviewable

5. Cleanup
- on success, undeploy/cleanup ephemeral validation environment
- on terminal failure, preserve logs/state/artifacts for inspection

Out of scope:
- production deployment
- cloud deployment
- automatic merge to main
- full tester-agent business/UAT tests
- modifying arbitrary product code
- persistent environment management

Acceptance:
- Deployer can run healthcheck plus smoke tests
- smoke tests are clearly distinguished from healthchecks in state/UI
- Deployer can run a bounded auto-fix loop after failures
- AI fixes are constrained to allowed deployment artifacts
- every iteration is persisted and observable
- successful loop ends with a functional ephemeral environment and cleanup
- failed loop ends cleanly with logs and iteration history
- no provider-specific AI SDK is hardcoded
- implementation remains generic and project-agnostic

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have a complete picture of the codebase. Let me write the plan.

## Objective

Add a generic smoke test step to the sandbox/deployer validation pipeline, then build a bounded AI auto-fix deployment loop that collects failure context, calls the configured AI runtime (provider-agnostic), applies patches constrained to allowed deployment artifacts, and repeats until success or retry limit — recording every iteration for observability.

## Included

### 1. Smoke test step — `tools/agent_runner/run_sandbox.py`

- After the `healthcheck` step, check for `.ai-dev-factory/scripts/smoke.sh`
- If present: execute it with the same env vars already in scope (`SANDBOX_ID`, `API_PORT`, `WEB_PORT`, proxy URLs); capture exit code, stdout, stderr
- If absent: record step status as `skipped` (never fail the pipeline for a missing smoke script)
- Extend `state.json` `steps` dict with a `smoke` entry matching the existing step schema: `status`, `exit_code`, `started_at`, `finished_at`
- `smoke.sh` is **not** added to `_REQUIRED_SCRIPTS`; it remains optional

### 2. Smoke test step — `services/control_api/services/deployer_runner.py`

- Add `_run_smoke_tests(project_root: Path, env: dict) -> ActionResult`; runs `smoke.sh` if present, skips otherwise
- Call it immediately after `_run_healthcheck()` succeeds inside `_do_deploy()`
- Extend `DeployProfile` (Pydantic model) with an optional `smoke` block:
  ```yaml
  smoke:
    script: .ai-dev-factory/scripts/smoke.sh   # optional override
    timeout: 60
  ```
- Extend deploy state JSON with `healthcheck_status` and `smoke_status` fields (values: `skipped | success | failed`)
- No change to existing `healthcheck` logic or state fields

### 3. Bounded AI auto-fix loop — `services/control_api/services/deployer_runner.py`

New function:
```python
run_deploy_with_autofix(
    project_id: str,
    project_root: Path,
    exec_cmd: str,
    max_retries: int = 3,
    sandbox_manager=None,
    sandbox=None,
) -> ActionResult
```

Inner loop (up to `max_retries`):
1. Call `_do_deploy()` (or sandboxed variant)
2. If success: cleanup and return
3. On failure:
   a. `_collect_deploy_failure_context(project_root, iteration)` → dict with: failing step, error message, last N lines of `deploy.log`, current deploy state JSON
   b. Read `allowed_fix_paths` from `deploy.yml` (new optional field; defaults to `[".ai-dev-factory/scripts/*", "docker-compose*.yml", ".env*", "deploy.yml"]`)
   c. Compose deployer-fixer prompt from `ai/roles/deployer-fixer.md` + failure context + allowed paths
   d. Call `execute_external_command(exec_cmd, prompt)` — no provider SDK
   e. Parse AI stdout for file patches (unified diff blocks fenced as ` ```diff `)
   f. `_apply_patches(patches, project_root, allowed_fix_paths)` — skip any patch targeting a path outside the allowlist, log skipped paths
   g. If no allowed patches applied → stagnation → break loop early
   h. If same error as previous iteration (identical `error` field) → stagnation → break loop early
   i. Persist iteration record (see §4)

### 4. Iteration history persistence

- Path: `.ai-dev-factory/deploy-iterations/iteration-{N}.json` (project mode) or `$RUNTIME_ROOT/state/deploy-iterations/iteration-{N}.json` (runtime mode); follows same path-resolution pattern as `deploy-state.json`
- Each record:
  ```json
  {
    "iteration": 1,
    "started_at": "...",
    "finished_at": "...",
    "failure_reason": "...",
    "failing_step": "smoke",
    "changed_files": ["..."],
    "patch_summary": "...",
    "health_status": "success|failed|skipped",
    "smoke_status": "success|failed|skipped",
    "log_tail": "..."
  }
  ```
- On terminal failure (all retries exhausted): write `deploy-iterations/summary.json` with outcome, total iterations, final error, artifact paths; do NOT delete intermediate records
- On success: write summary, call `run_undeploy()` + `run_cleanup()`

### 5. Deployer-fixer role file — `ai/roles/deployer-fixer.md`

New file defining:
- Input contract: receives failure context (step, logs, error, allowed paths)
- Output contract: responds with zero or more unified diff blocks (` ```diff `) targeting only files in `allowed_fix_paths`
- Explicit constraints: never modify application source; never propose merge or push operations; produce one patch per file maximum

### 6. `DeployProfile` schema extension — `services/control_api/services/deployer_runner.py`

Add two optional fields to the Pydantic model:
```python
class SmokeCfg(BaseModel):
    script: str = ".ai-dev-factory/scripts/smoke.sh"
    timeout: int = 60

class AutoFixCfg(BaseModel):
    max_retries: int = 3
    allowed_paths: list[str] = [".ai-dev-factory/scripts/*", "docker-compose*.yml", ".env*", "deploy.yml"]

class DeployProfile(BaseModel):
    ...
    smoke: SmokeCfg | None = None
    auto_fix: AutoFixCfg | None = None
```

### 7. REST API exposure — `services/control_api/routes/deployer.py`

- New endpoint: `POST /deployer/deploy-with-autofix`
- Body: `project_id`, `exec_cmd`, `max_retries` (optional, default from config)
- Returns: same `ActionResult` shape as existing `/deployer/deploy`
- New endpoint: `GET /deployer/deploy-iterations` — lists iteration JSON files for the current project

## Excluded

- Production or cloud deployment targets
- Automatic merge to main or any branch after successful loop
- Modifying arbitrary application source files (outside `allowed_fix_paths`)
- Full business/UAT tester-agent tests (tracked separately)
- Persistent environment management beyond the current sandbox lifetime
- Support for patch formats other than unified diff in AI output
- UI changes beyond what is needed to surface the new state fields

## Acceptance criteria

- `run_sandbox.py` executes `smoke.sh` when present; records a `smoke` step in `state.json` with `status`, `exit_code`, `started_at`, `finished_at`; step is absent (not failed) when script is missing
- `deployer_runner.py` deploys → healthcheck → smoke tests in sequence; deploy state JSON exposes `healthcheck_status` and `smoke_status` as distinct fields
- `run_deploy_with_autofix()` invokes `execute_external_command(exec_cmd, prompt)` with no import of any AI provider SDK
- AI patches that target paths outside `allowed_fix_paths` are silently skipped; at least one skipped-path warning is logged
- Loop halts before `max_retries` if the same `error` string repeats across consecutive iterations (stagnation guard)
- Each iteration produces a valid `iteration-{N}.json` under the iterations directory before the next iteration begins
- Successful loop: `run_undeploy()` is called, `summary.json` records `outcome: success`
- Failed loop (retries exhausted): all `iteration-{N}.json` files are preserved, `summary.json` records `outcome: failed` with final error
- `ai/roles/deployer-fixer.md` exists and defines the input/output contract
- `POST /deployer/deploy-with-autofix` endpoint accepts `exec_cmd` and `max_retries` and returns an `ActionResult`
- `GET /deployer/deploy-iterations` returns the list of iteration records for the active project

---

## Review

# Plan review — T153

Decision: PLAN_FIX_REQUIRED

The current direction is good, but the plan should be simplified before approval.

The long-term product goal is correct:

```text
Deployer = audit → generate/fix scripts → deploy ephemeral sandbox → healthcheck → smoke tests → auto-fix → retry → cleanup
```

However, implementing the full smoke-test layer and the complete auto-fix loop in one ticket is risky.

## Main concern

T153 must not become a large all-at-once implementation that mixes:

- smoke test generation
- smoke test execution
- AI patch generation
- AI patch application
- redeploy loop
- progress detection
- failure classification
- UI/state changes
- cleanup behavior

That is too much for a single safe implementation step.

## Required simplification

T153 should be split into a smaller V1 focused on:

1. adding a generic smoke-test lifecycle after healthcheck
2. executing `smoke.sh` when present
3. persisting healthcheck and smoke-test results separately
4. preparing iteration artifacts for a future auto-fix loop
5. optionally generating an AI fix proposal, but not applying it automatically yet

The full apply-patch-and-rerun auto-fix loop should be a follow-up ticket after smoke tests are stable.

See `runs/T153/fixes/plan-fix-1.md`.

---

## Instructions de fix

# Plan fix — T153 simplified staged implementation

## Objective

Reduce the implementation scope of T153 to a safe and observable V1.

The goal of V1 is:

```text
healthcheck
→ smoke tests
→ observable validation artifacts
→ optional AI fix suggestion
```

NOT yet:

```text
full autonomous self-healing deployment loop
```

## V1 Scope

### 1. Generic smoke test lifecycle

Add support for:

```text
.ai-dev-factory/scripts/smoke.sh
```

Execution order:

```text
start
→ healthcheck
→ smoke tests
```

Smoke tests must:

- prefer proxy URLs when available
- fallback to direct allocated ports
- return clear exit codes
- stream logs to runtime artifacts

### 2. Persist validation artifacts

Persist:

- healthcheck result
- smoke result
- logs
- runtime URLs
- timestamps

Suggested structure:

```text
runs/<ticket>/validation/
```

### 3. Distinguish health vs smoke

State/UI/logs must clearly show:

```text
HEALTHCHECK_PASSED
SMOKE_FAILED
```

and not collapse everything into a single boolean.

### 4. AI fix proposal only

On smoke-test failure:

- collect logs
- collect deployment artifacts
- optionally ask AI runtime for a fix proposal
- persist proposal/diff
- DO NOT auto-apply yet

This keeps the first implementation safe and observable.

### 5. Cleanup remains automatic

Ephemeral validation environments must still stop and cleanup automatically.

## Explicitly deferred to future ticket

The following should be deferred:

- automatic patch application
- redeploy loop
- progress detection
- failure classifier
- retry orchestration
- convergence engine
- automatic smoke test generation
- tester-agent/UAT flows

## Acceptance criteria

- smoke.sh executes after healthcheck
- health and smoke results are distinct
- validation artifacts are persisted
- AI fix proposal can be generated and stored
- no automatic patch application occurs yet
- cleanup still works
- implementation remains generic and project-agnostic