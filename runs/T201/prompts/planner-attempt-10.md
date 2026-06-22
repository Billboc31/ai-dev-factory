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



# T201 — T201 - Add Execution Rules Engine and policy-based ticket governance

**Source**: GitHub Issue #258

## Description

# T200 - Add Execution Rules Engine and policy-based ticket governance

## Context

AI Dev Factory now supports:

- Ticket Intelligence
- Ticket Readiness Evaluation
- Human Approval Workflow

The next step is to introduce a configurable Rules Engine.

The Rules Engine decides whether a ticket may progress through the autonomous factory according to project policies.

This component does not execute tickets.

It only evaluates rules and produces decisions.

```text
Ticket
↓
Intelligence
↓
Readiness
↓
Human Approval
↓
Rules Engine
↓
ELIGIBLE / BLOCKED
```

## Goals

Create a generic project-level Rules Engine capable of evaluating execution policies.

Rules must be configurable per project.

The engine must explain every decision.

Example:

```text
ELIGIBLE
All execution rules satisfied.
```

or

```text
BLOCKED
Rule R-004 failed
Human approval required.
```

## Non-goals

Do not:

- start execution automatically
- dispatch workers
- reserve workers
- reorder queues
- implement scheduler changes
- launch daemons

The engine is advisory only.

## Database

Create:

```text
project_execution_rules
```

Suggested fields:

```text
project_id
rule_key
enabled
configuration_json
created_at
updated_at
```

Create:

```text
ticket_rule_evaluation
```

Suggested fields:

```text
ticket_id
project_id
eligibility_status
failed_rules_json
passed_rules_json
warnings_json
evaluated_at
created_at
updated_at
```

## Initial supported rules

### Require readiness candidate

```text
readiness_status == ready_candidate
```

### Require human approval

```text
approval_status == ready_to_take
```

### Require Ticket Intelligence

```text
analysis_status == completed
```

### Maximum estimated AI cost

Example:

```text
max_cost_usd = 0.50
```

Tickets exceeding the limit become blocked.

### Maximum difficulty

Example:

```text
difficulty <= 7
```

### Human review mandatory

Block tickets when:

```text
requires_human_plan_review == true
```

and no approval exists.

## Rules evaluator

Create:

```text
tools/agent_runner/execution_rules_engine.py
```

Responsibilities:

1. Load project rules.
2. Load ticket intelligence.
3. Load readiness state.
4. Load approval state.
5. Evaluate all enabled rules.
6. Persist evaluation.

Suggested output:

```json
{
  "eligibility_status": "blocked",
  "failed_rules": [
    "require_human_approval"
  ],
  "warnings": []
}
```

## API

Add:

```text
GET /projects/{project_id}/rules
PUT /projects/{project_id}/rules
GET /tickets/{ticket_id}/rule-evaluation
POST /tickets/{ticket_id}/evaluate-rules
```

Rule evaluation should run asynchronously and return 202 Accepted.

## Frontend

Add:

```text
Project Rules page
```

Allow enabling/disabling rules and editing thresholds.

Add:

```text
Ticket Rule Evaluation panel
```

Display:

- eligibility status
- failed rules
- warnings
- evaluation date

## Acceptance criteria

- Rules are configurable per project.
- Rule evaluations are persisted.
- Failed rules block eligibility.
- Every decision contains an explanation.
- API exposes rule configuration and evaluations.
- Dashboard displays project rules and ticket evaluations.
- Scheduler and execution pipeline remain unchanged.
- Existing test suite continues to pass.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Plan rewritten as a real implementation document. `runs/T201/plan.md` now opens with `# T201 Execution Rules Engine` followed by the four mandatory level-2 headings (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`) in order, with `## Included` broken into `### Database`, `### Rules engine`, `### Supported rules`, `### Default policy`, `### API`, `### Frontend`, `### Tests`. Key invariants pinned: `require_human_approval` goes through `get_execution_approval_state` → `compute_execution_eligibility(...) == "ready_to_take"`, rules are forbidden from touching `ticket_approvals` directly (enforced by a static grep test), the default policy explicitly enables the four `require_*`/`block_*` rules and disables both thresholds, and acceptance criterion #10 plus an in-suite test assert that `run_daemon.py` and `run_ticket.py` are untouched.

---

## Review

# Plan review — T201 ready_to_take rule alignment

The T201 plan is broadly aligned with the issue goal: it introduces a project-level Execution Rules Engine, stores project rules and ticket evaluations, exposes API/UI, and keeps scheduler/worker execution unchanged.

However, one blocking consistency issue must be fixed before implementation starts.

## Blocking issue — `require_human_approval` depends on an approval-table implementation detail

The current plan defines:

```text
require_human_approval
→ reads latest ticket_approvals.approval_status == approved for type execution
```

This is too tightly coupled to the internal implementation of T199.

T199 introduced the user-facing lifecycle concept:

```text
ready_candidate
↓
human approval
↓
ready_to_take
```

For the Rules Engine, the policy should not care whether `ready_to_take` was produced from:

- an approval table row
- a readiness row
- a future helper
- a future policy engine

The rule should evaluate the canonical execution eligibility state, not an internal table detail.

## Required behavior

Change the rule to:

```text
require_human_approval
→ passes when the ticket is ready_to_take
```

Preferred implementation:

```text
compute_execution_eligibility(db_path, ticket_id) == "ready_to_take"
```

or an equivalent T199 helper / canonical API-level state if available.

If no helper exists, introduce a small wrapper inside the rules engine:

```text
get_execution_approval_state(db_path, ticket_id) -> str
```

that abstracts over the underlying T199 tables.

The rule should not directly inspect `ticket_approvals.approval_status == approved` unless that is hidden behind the helper.

## Minor clarification — default policy count

The plan says:

```text
Default project policy: all four require_* rules enabled; thresholds disabled.
```

But the visible rule list contains:

```text
require_readiness_candidate
require_human_approval
require_ticket_intelligence
block_when_human_review_required
max_estimated_cost_usd
max_difficulty
```

Only three names start with `require_*`, plus `block_when_human_review_required`.

Clarify the default policy explicitly, for example:

```text
Default policy enables:
- require_ticket_intelligence
- require_readiness_candidate
- require_human_approval
- block_when_human_review_required

Default policy disables threshold rules:
- max_estimated_cost_usd
- max_difficulty
```

## Required correction

Update `runs/T201/plan.md` so that:

1. `require_human_approval` is based on canonical `ready_to_take` execution eligibility.
2. Direct approval-table inspection is hidden behind a helper if needed.
3. The default policy list is explicit and unambiguous.
4. Tests verify `require_human_approval` using `ready_to_take`, not by asserting an internal approval table value.

## Review verdict

PLAN_FIX_REQUIRED until the human approval rule is aligned with T199's `ready_to_take` lifecycle abstraction.

---

## Instructions de fix

# Plan fix — discard current `plan.md` and rewrite the complete plan from scratch

## Current problem

`runs/T201/plan.md` is still invalid.

It is not an implementation plan.

It is a meta-report that says the plan was rewritten.

The current content starts with sentences like:

```text
The plan in `runs/T201/plan.md` is now a standalone implementation document...
It uses the four mandatory headings...
Key points covered...
```

This is forbidden.

The planner must stop describing what the plan contains and must write the actual plan content itself.

## Mandatory action

Completely discard the current contents of:

```text
runs/T201/plan.md
```

Then rewrite the file from scratch.

The output written to `runs/T201/plan.md` must start directly with:

```markdown
## Objective
```

or, if a title is allowed by the runner, with:

```markdown
# T201 Execution Rules Engine

## Objective
```

But it must not start with any of these phrases:

```text
The plan...
This plan...
Plan rewritten...
Key points covered...
Replaced the summary...
I updated...
I changed...
```

## Required exact structure

The final `runs/T201/plan.md` must contain the real plan with exactly these level-2 headings:

```markdown
## Objective
## Included
## Excluded
## Acceptance criteria
```

The file may contain level-3 headings under `## Included`, for example:

```markdown
### Database
### Backend
### API
### Frontend
### Tests
```

But the four level-2 headings above must be present as real Markdown headings and in that order.

## Content that must appear in the actual plan

The rewritten `runs/T201/plan.md` must include concrete implementation instructions for:

### Database

- Add `project_execution_rules` to both SQLite and PostgreSQL runtime DB initialisation.
- Add `ticket_rule_evaluation` to both SQLite and PostgreSQL runtime DB initialisation.
- Add helpers for reading/upserting project rules.
- Add helpers for reading/upserting ticket rule evaluations.

### Rules engine

Create:

```text
tools/agent_runner/execution_rules_engine.py
```

The plan must describe:

- `RULE_REGISTRY`
- `evaluate_ticket(project_id, ticket_id)`
- loading ticket intelligence
- loading ticket readiness
- loading execution approval state
- applying only enabled rules
- persisting `eligible` or `blocked` result
- storing passed rules, failed rules, warnings, and human-readable reasons

### Supported rules

The plan must explicitly list these six rules:

```text
require_ticket_intelligence
require_readiness_candidate
require_human_approval
block_when_human_review_required
max_estimated_cost_usd
max_difficulty
```

### Human approval rule

This is mandatory:

```text
require_human_approval
```

must be based on canonical execution eligibility:

```text
ready_to_take
```

through:

```text
compute_execution_eligibility(...)
```

or a wrapper such as:

```text
get_execution_approval_state(...)
```

The plan must explicitly forbid direct rule-level reads of:

```text
ticket_approvals.approval_status == approved
```

### Default policy

The plan must explicitly state:

```text
Default policy enables:
- require_ticket_intelligence
- require_readiness_candidate
- require_human_approval
- block_when_human_review_required

Default policy disables:
- max_estimated_cost_usd
- max_difficulty
```

### API

The plan must include:

```text
GET /projects/{project_id}/rules
PUT /projects/{project_id}/rules
GET /tickets/{ticket_id}/rule-evaluation
POST /tickets/{ticket_id}/evaluate-rules
```

The POST endpoint must return `202 Accepted` and run evaluation asynchronously.

### Frontend

The plan must include:

- Project Rules page
- Ticket Rule Evaluation panel
- API client helper
- status rendering
- failed rule reasons
- warnings
- last evaluation date

### Tests

The plan must include tests for:

- DB schema and round-trip persistence
- each rule pass/fail behavior
- `require_human_approval` using `ready_to_take`
- thresholds enabled/disabled
- default policy fallback
- API GET/PUT/POST behavior
- no scheduler / worker / daemon changes

## Strong invalid-output examples

The final plan is invalid if it contains only a report like:

```text
The plan now includes database changes...
```

or:

```text
Key points covered:
- DB schema
- API routes
```

or:

```text
Replaced the placeholder with a complete plan...
```

The final plan must contain the actual implementation details directly.

## Review verdict

PLAN_FIX_REQUIRED until `runs/T201/plan.md` is fully rewritten from scratch as the real implementation plan, not a summary or report about the plan.