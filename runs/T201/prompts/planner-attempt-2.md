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

## Objective

Introduce a project-level Execution Rules Engine that evaluates whether a ticket is eligible to proceed through the autonomous factory, based on configurable per-project policies. The engine is advisory: it persists explained decisions (ELIGIBLE / BLOCKED) but does not schedule, dispatch, or execute work.

## Included

**Database schema** (declared inline in `tools/agent_runner/runtime_db.py` and `tools/agent_runner/runtime_db_pg.py`, mirroring T197–T199 conventions):
- `project_execution_rules` — columns: `project_id`, `rule_key`, `enabled`, `configuration_json`, `created_at`, `updated_at` (PK `(project_id, rule_key)`).
- `ticket_rule_evaluation` — columns: `project_id`, `ticket_id`, `eligibility_status` (`eligible|blocked|failed`), `failed_rules_json`, `passed_rules_json`, `warnings_json`, `evaluated_at`, `created_at`, `updated_at` (PK `(project_id, ticket_id)`).
- Accessor helpers in `runtime_db.py`: `get_project_rules`, `upsert_project_rule`, `get_ticket_rule_evaluation`, `upsert_ticket_rule_evaluation` — and their PostgreSQL counterparts.

**Rules engine module** — new file `tools/agent_runner/execution_rules_engine.py`:
- `RULE_REGISTRY` mapping `rule_key` → evaluator callable. Initial rules:
  - `require_readiness_candidate` (reads `ticket_readiness.readiness_status == ready_candidate`)
  - `require_human_approval` (reads latest `ticket_approvals.approval_status == approved` for type `execution`, surfaced via T199 lifecycle as `ready_to_take`)
  - `require_ticket_intelligence` (reads `ticket_intelligence.analysis_status == completed`)
  - `max_estimated_cost_usd` (compares `ticket_intelligence.estimated_cost_max` to threshold)
  - `max_difficulty` (compares `ticket_intelligence.difficulty_score` to threshold)
  - `block_when_human_review_required` (blocks when `ticket_intelligence.requires_human_plan_review` is true and no execution approval exists)
- `evaluate_ticket(project_id, ticket_id)` — loads project rules, loads intelligence/readiness/approval state via existing `runtime_db` helpers, runs only enabled rules, returns a dict `{eligibility_status, failed_rules, passed_rules, warnings}` with per-rule human-readable reasons, and persists via `upsert_ticket_rule_evaluation`.
- Default project policy (returned when `project_execution_rules` is empty for a project): all four `require_*` rules enabled; thresholds disabled.

**API routes** — new file `services/control_api/routes/execution_rules.py`, registered in the FastAPI app:
- `GET /projects/{project_id}/rules` — returns the list of configured (or default) rules.
- `PUT /projects/{project_id}/rules` — accepts a list of `{rule_key, enabled, configuration}` entries, upserts each row.
- `GET /tickets/{ticket_id}/rule-evaluation` — returns the persisted evaluation (or `404` if none).
- `POST /tickets/{ticket_id}/evaluate-rules` — returns `202 Accepted`, spawns a `threading.Thread` running `execution_rules_engine.evaluate_ticket`, mirroring the dispatch pattern used in `services/control_api/routes/readiness.py`.
- Pydantic models added to `services/control_api/models/schemas.py` (`ProjectRule`, `ProjectRulesPayload`, `RuleEvaluationResponse`, `RuleEvaluationQueued`).

**Frontend** (React + Vite under `apps/dashboard/`):
- New page `src/pages/ProjectRulesPage.jsx` listing rules with enable/disable toggles and threshold inputs; uses a new API helper `src/api/projectRules.js`.
- New component `src/components/TicketRuleEvaluationPanel.jsx` integrated into `TicketDetailPage.jsx`, displaying `eligibility_status`, failed rules with reasons, warnings, and `evaluated_at`. Reuses `hooks/usePolling.js` while the evaluation is queued.

**Tests** (under `tests/`, mirroring T197–T199 layout):
- `test_execution_rules_db.py` — schema, upsert, fetch, JSON round-trip.
- `test_execution_rules_engine.py` — each rule evaluated in isolation, default-policy fallback, eligibility aggregation, persisted evaluation shape, missing intelligence/readiness handled gracefully.
- `test_execution_rules_api.py` — GET/PUT rules, GET evaluation, POST returns `202` and persists asynchronously.

## Excluded

- Any change to the scheduler, worker dispatch, queue ordering, or `run_ticket.py` lifecycle — the engine remains advisory.
- Automatic re-evaluation triggers (cron, on-state-change hooks). Evaluation is only invoked explicitly via the POST endpoint in this ticket.
- New rule types beyond the six listed above (custom DSL, regex on labels, time windows, etc.) — extension is left to follow-up tickets via `RULE_REGISTRY`.
- Versioning or audit history of rule edits (the table records the current configuration only; the `ticket_rule_evaluation` table is point-in-time, not append-only).
- Multi-project UI navigation overhaul; the Project Rules page is reachable from the existing project context, no global redesign.
- Authentication or RBAC on the new endpoints (consistent with current API surface).

## Acceptance criteria

- `project_execution_rules` and `ticket_rule_evaluation` tables are created on first run in both SQLite and PostgreSQL backends; existing data is preserved.
- `GET /projects/{project_id}/rules` returns the default policy when no rows exist, and the persisted rows otherwise; `PUT` round-trips a configuration without data loss.
- `POST /tickets/{ticket_id}/evaluate-rules` returns `202 Accepted`; a subsequent `GET /tickets/{ticket_id}/rule-evaluation` returns the persisted decision with `failed_rules`, `passed_rules`, and `warnings` populated.
- Every entry in `failed_rules_json` includes a non-empty human-readable `reason`; `eligibility_status` is `blocked` whenever `failed_rules` is non-empty and `eligible` otherwise.
- Disabling a rule via `PUT` causes the next evaluation to skip it (rule absent from both `passed_rules` and `failed_rules`).
- The Project Rules page renders the configured rules, allows toggling and editing thresholds, and persists changes via the API.
- The Ticket Rule Evaluation panel displays the current decision and refreshes after a triggered evaluation.
- `pytest tests/test_execution_rules_db.py tests/test_execution_rules_engine.py tests/test_execution_rules_api.py` passes; the full existing test suite continues to pass.
- No file under `tools/agent_runner/run_ticket.py` or the scheduler is modified.

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