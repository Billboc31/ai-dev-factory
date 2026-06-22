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

Plan updated. All four review points addressed in `runs/T201/plan.md`:

1. **`require_human_approval` uses canonical `ready_to_take`** — now goes through `ticket_approval_service.compute_execution_eligibility(db_path, ticket_id)` (verified to exist at `tools/agent_runner/ticket_approval_service.py:148`), with the optional `get_execution_approval_state` wrapper as documented fallback.
2. **Result mapping made explicit** — `ready_to_take` passes; `ready_candidate`, `blocked`, `not_started`/unknown each fail with a specific human-readable reason.
3. **`block_when_human_review_required` realigned** — now also reads via `compute_execution_eligibility`, no direct approval-table inspection.
4. **Default policy listed explicitly** — four enabled rules and two disabled threshold rules, named one by one (no more ambiguous "four `require_*`" wording).
5. **Test description updated** — `require_human_approval` is tested through the canonical eligibility contract; approval-table internals must not be the rule contract.
6. **Acceptance criteria extended** — three new criteria covering canonical state usage, deterministic default policy, and human-readable failure reasons; advisory-only constraint reiterated.

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

# Plan fix — align `require_human_approval` with canonical `ready_to_take`

## Required plan update

Update `runs/T201/plan.md` before implementation starts.

The plan is directionally correct, but `require_human_approval` must be aligned with the lifecycle introduced by T199.

## 1. Use canonical execution eligibility state

Replace this rule definition:

```text
require_human_approval
→ reads latest ticket_approvals.approval_status == approved for type execution
```

with:

```text
require_human_approval
→ passes when execution eligibility is ready_to_take
```

Preferred implementation:

```python
compute_execution_eligibility(db_path, ticket_id) == "ready_to_take"
```

If `compute_execution_eligibility` is not available or not appropriate, introduce a small abstraction in the rules engine:

```python
def get_execution_approval_state(db_path: str, ticket_id: str) -> str:
    """Return canonical execution approval state such as ready_candidate, ready_to_take, blocked, unknown."""
```

The Rules Engine must not depend directly on the physical approval-table representation.

Direct reads from T199 tables may exist only behind this helper.

## 2. Rule behavior

The `require_human_approval` rule should behave as follows:

```text
ready_to_take
→ passed

ready_candidate
→ failed: Human approval required before execution

blocked
→ failed: Ticket is blocked

not_started / unknown / missing state
→ failed or warning depending on existing readiness/intelligence rule result, but must not pass
```

The exact reason text can vary, but it must be human-readable.

## 3. Default policy clarification

Replace ambiguous wording like:

```text
all four require_* rules enabled; thresholds disabled
```

with an explicit list:

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

This avoids confusion because `block_when_human_review_required` is not named as a `require_*` rule.

## 4. Test updates

Add or adjust tests so that:

- `require_human_approval` passes when the canonical execution state is `ready_to_take`.
- `require_human_approval` fails when the canonical execution state is `ready_candidate`.
- Tests do not assert `ticket_approvals.approval_status == approved` as the rule contract.
- The helper or abstraction is tested separately if introduced.

## 5. Non-goals reminder

This fix must not change:

- scheduler behavior
- worker dispatch
- queue ordering
- daemon state machine
- run execution lifecycle

The Rules Engine remains advisory only in this ticket.

## Updated acceptance criteria

Add acceptance criteria:

- `require_human_approval` evaluates canonical `ready_to_take` execution eligibility, not approval-table internals.
- Default project policy is explicitly listed and deterministic.
- Rule evaluation output explains failures with human-readable reasons.