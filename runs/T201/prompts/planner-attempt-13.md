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

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T201/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

## Objective

Introduce a project-level Execution Rules Engine that evaluates configurable policies against a ticket and emits an `eligible` or `blocked` decision with explicit reasons. The engine is advisory: it persists evaluations and exposes them via the existing Control API and dashboard, but it does not start execution, dispatch workers, reserve workers, reorder queues, or change scheduler/daemon behavior.

## Included

### Database

- Extend `tools/agent_runner/runtime_db.py` and `tools/agent_runner/runtime_db_pg.py` to create the table `project_execution_rules` in both the SQLite and PostgreSQL initialisation paths, with columns:
  - `project_id TEXT NOT NULL`
  - `rule_key TEXT NOT NULL`
  - `enabled INTEGER NOT NULL` (boolean in PG)
  - `configuration_json TEXT NOT NULL DEFAULT '{}'` (JSONB in PG)
  - `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - PRIMARY KEY `(project_id, rule_key)`
- Extend the same modules to create `ticket_rule_evaluation` with columns:
  - `ticket_id TEXT NOT NULL`
  - `project_id TEXT NOT NULL`
  - `eligibility_status TEXT NOT NULL` (`eligible` or `blocked`)
  - `failed_rules_json TEXT NOT NULL DEFAULT '[]'`
  - `passed_rules_json TEXT NOT NULL DEFAULT '[]'`
  - `warnings_json TEXT NOT NULL DEFAULT '[]'`
  - `evaluated_at TEXT NOT NULL`
  - `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - PRIMARY KEY `(ticket_id)`
- Add to `tools/agent_runner/runtime_db.py` (and PG equivalents in `runtime_db_pg.py`):
  - `list_project_rules(db_path, project_id) -> list[dict]`
  - `upsert_project_rule(db_path, project_id, rule_key, enabled, configuration)` — upserts one row.
  - `replace_project_rules(db_path, project_id, rules: list[dict])` — atomically replaces the project's rule set; used by `PUT /projects/{project_id}/rules`.
  - `get_ticket_rule_evaluation(db_path, ticket_id) -> dict | None`
  - `upsert_ticket_rule_evaluation(db_path, ticket_id, project_id, eligibility_status, passed_rules, failed_rules, warnings, evaluated_at)` — overwrites the row keyed by `ticket_id`.
- All helpers accept both SQLite and PostgreSQL `db_path`/DSN via the existing connection abstraction; JSON columns are read back as Python lists/dicts.

### Rules engine

Create `tools/agent_runner/execution_rules_engine.py` containing:

- A module-level `RULE_REGISTRY: dict[str, RuleSpec]` mapping every supported rule key to a `RuleSpec` dataclass holding:
  - `key: str`
  - `description: str`
  - `default_enabled: bool`
  - `default_configuration: dict`
  - `evaluator: Callable[[RuleContext], RuleResult]`
- A `RuleContext` dataclass exposing the inputs each evaluator may read:
  - `project_id`
  - `ticket_id`
  - `configuration` (the rule's own JSON configuration)
  - `intelligence` (the Ticket Intelligence record, or `None`)
  - `readiness` (the Readiness record, or `None`)
  - `approval_state` (the canonical execution eligibility string returned by `compute_execution_eligibility`)
- A `RuleResult` dataclass: `passed: bool`, `reason: str`, optional `warnings: list[str]`.
- `get_execution_approval_state(db_path, ticket_id) -> str` — wrapper that calls `compute_execution_eligibility(db_path, ticket_id)` imported from `tools/agent_runner/ticket_approval_service.py` and returns the canonical string (`ready_candidate`, `ready_to_take`, `blocked`, `not_started`, etc.). This wrapper is the **only** place in the engine that resolves the approval state. Rule evaluators receive the resulting string through `RuleContext.approval_state`. The file must not import or reference `ticket_approvals` or `approval_status` directly.
- `evaluate_ticket(db_path, project_id, ticket_id) -> dict` that:
  1. Loads project rules via `list_project_rules`. If a registered rule has no row for the project, fall back to its registry defaults (default policy below).
  2. Loads Ticket Intelligence for `ticket_id` from the existing analysis tables.
  3. Loads Readiness state for `ticket_id` from the T199 readiness helpers.
  4. Calls `get_execution_approval_state` once and stores the result in `RuleContext`.
  5. Iterates over the registry; for each enabled rule, runs its evaluator with the populated `RuleContext`.
  6. Aggregates the results into:
     - `passed_rules: list[{"rule_key", "reason"}]`
     - `failed_rules: list[{"rule_key", "reason"}]`
     - `warnings: list[{"rule_key", "message"}]`
  7. Sets `eligibility_status = "blocked"` if any rule failed, otherwise `"eligible"`.
  8. Persists the decision via `upsert_ticket_rule_evaluation` with `evaluated_at = utcnow().isoformat()`.
  9. Returns the dict `{"eligibility_status", "passed_rules", "failed_rules", "warnings", "evaluated_at"}`.

### Supported rules

The engine ships with exactly these six rules registered in `RULE_REGISTRY`:

- `require_ticket_intelligence` — passes when the Ticket Intelligence record exists and `analysis_status == "completed"`. Default `enabled = true`.
- `require_readiness_candidate` — passes when readiness is loaded and `readiness_status == "ready_candidate"` (or any later canonical lifecycle state). Default `enabled = true`.
- `require_human_approval` — passes when `RuleContext.approval_state == "ready_to_take"`. The evaluator MUST read only from `RuleContext.approval_state`; it MUST NOT query the `ticket_approvals` table directly. Default `enabled = true`.
- `block_when_human_review_required` — fails when the Ticket Intelligence flag `requires_human_plan_review` is `true` AND `RuleContext.approval_state != "ready_to_take"`. Default `enabled = true`.
- `max_estimated_cost_usd` — configuration `{"max_cost_usd": float}`. Fails when the ticket's estimated AI cost from intelligence exceeds `max_cost_usd`. Default `enabled = false`, default configuration `{"max_cost_usd": 0.50}`.
- `max_difficulty` — configuration `{"max_difficulty": int}`. Fails when the ticket's difficulty score from intelligence exceeds `max_difficulty`. Default `enabled = false`, default configuration `{"max_difficulty": 7}`.

### Default policy

When `evaluate_ticket` finds no row in `project_execution_rules` for a given `(project_id, rule_key)`, it uses the registry default. The effective default policy is:

```
Default policy enables:
- require_ticket_intelligence
- require_readiness_candidate
- require_human_approval
- block_when_human_review_required

Default policy disables:
- max_estimated_cost_usd
- max_difficulty
```

`PUT /projects/{project_id}/rules` with no body OR with the special action `reset_defaults` resets the project to this exact policy by calling `replace_project_rules` with the registry defaults serialised out.

### Control API

Wire the following endpoints into the existing Control API. Place handlers in `services/control_api/routes/rules.py`, register the router in `services/control_api/main.py` next to the existing `intelligence`, `readiness`, and `approvals` routers, and add request/response schemas to `services/control_api/models/schemas.py`. Follow the conventions established by `services/control_api/routes/intelligence.py`, `routes/readiness.py`, and `routes/approvals.py`.

- `GET /projects/{project_id}/rules` — returns `{"rules": [{"rule_key", "enabled", "configuration", "description", "default_enabled", "default_configuration"}]}`. Rules without a stored row are returned with their registry defaults so the UI always sees the full set.
- `PUT /projects/{project_id}/rules` — body `{"rules": [{"rule_key", "enabled", "configuration"}]}`. Validates that every `rule_key` exists in `RULE_REGISTRY` and that `configuration` matches the rule's schema (e.g. `max_cost_usd` must be a non-negative number). Calls `replace_project_rules`. Returns the updated set in the same shape as the GET.
- `GET /tickets/{ticket_id}/rule-evaluation` — returns the persisted evaluation row (parsed JSON arrays). Returns `404` if none exists.
- `POST /tickets/{ticket_id}/evaluate-rules` — schedules `evaluate_ticket` on a FastAPI `BackgroundTasks` queue and immediately responds with HTTP `202 Accepted` and body `{"status": "scheduled", "ticket_id": ...}`. The background task writes the result via `upsert_ticket_rule_evaluation`; clients poll the GET endpoint to read it.

No changes are made to existing scheduler/queue endpoints.

### Frontend (dashboard)

All UI work targets the existing dashboard under `apps/dashboard/src/` (React + React Router). No file is created under `web/` and no Next.js conventions are used.

- Extend the existing API client at `apps/dashboard/src/api/tickets.js` (or add a sibling file `apps/dashboard/src/api/rules.js` if isolation is preferred) with:
  - `getProjectRules(projectId)`
  - `putProjectRules(projectId, rules)`
  - `getTicketRuleEvaluation(ticketId)`
  - `postEvaluateTicketRules(ticketId)`
- Add a **Project Rules panel** at `apps/dashboard/src/components/ProjectRulesPanel.jsx`:
  - Lists every rule from the registry with its description.
  - Each row has an enable/disable toggle.
  - Threshold rules (`max_estimated_cost_usd`, `max_difficulty`) expose an inline editable numeric field.
  - "Reset to defaults" button calls `PUT` with the default payload.
  - "Save" button calls `PUT` with the current state.
- Add a **Project Rules page** at `apps/dashboard/src/pages/ProjectRulesPage.jsx` that hosts `ProjectRulesPanel` and is wired into the existing React Router route table next to the other project pages.
- Add a **Ticket Rule Evaluation panel** at `apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx`, following the visual conventions of `TicketIntelligencePanel.jsx`, `TicketReadinessPanel.jsx`, and `HumanApprovalPanel.jsx`:
  - Displays `eligibility_status` with a coloured badge (`eligible` = green, `blocked` = red).
  - Lists failed rules with their human-readable reasons.
  - Lists warnings.
  - Shows `evaluated_at` formatted as local datetime.
  - "Re-evaluate" button calls the POST endpoint, then polls the GET endpoint until `evaluated_at` changes.
- Embed `TicketRuleEvaluationPanel` into `apps/dashboard/src/pages/TicketDetailPage.jsx` next to the existing intelligence, readiness, and approval panels.

### Tests

Add the following Python test files under `tests/`:

- `tests/test_execution_rules_db.py` — round-trip persistence on both SQLite and PostgreSQL fixtures: schema creation, upsert/list of project rules, upsert/get of ticket evaluations, JSON columns deserialise to lists.
- `tests/test_execution_rules_engine.py` — for each of the six rules: one case where the rule passes and one where it fails, asserting the reason string. The `require_human_approval` cases must drive the result by setting `RuleContext.approval_state` to `"ready_to_take"` (pass) vs `"ready_candidate"` (fail). The `max_estimated_cost_usd` and `max_difficulty` cases cover both enabled and disabled configurations.
- `tests/test_execution_rules_default_policy.py` — when no rows exist in `project_execution_rules`, `evaluate_ticket` applies the four `require_*` / `block_when_*` rules with `enabled=true` and the two threshold rules with `enabled=false`.
- `tests/test_execution_rules_approval_isolation.py` — static grep test asserting that `tools/agent_runner/execution_rules_engine.py` does NOT contain the substrings `ticket_approvals` or `approval_status` outside of comments. The only allowed approval lookup path is `compute_execution_eligibility` via `get_execution_approval_state`.
- `tests/test_execution_rules_api.py` — FastAPI `TestClient` against `services/control_api/main.py` exercising `GET`/`PUT /projects/{project_id}/rules`, `GET /tickets/{ticket_id}/rule-evaluation`, and `POST /tickets/{ticket_id}/evaluate-rules` (asserting HTTP `202` and eventual persistence after the background task runs).
- `tests/test_execution_rules_pipeline_untouched.py` — asserts via static greps that `tools/agent_runner/run_daemon.py`, `tools/agent_runner/run_ticket.py`, and the scheduler module do not import `execution_rules_engine` and contain no call sites for `evaluate_ticket`.

Add the following frontend tests under `apps/dashboard/tests/` (matching the existing dashboard test setup):

- `apps/dashboard/tests/TicketRuleEvaluationPanel.test.jsx` — renders the panel with eligible/blocked fixtures, asserts the badge colour, failed-rule list, warnings list, and that clicking "Re-evaluate" calls the POST endpoint and re-fetches the GET endpoint.
- `apps/dashboard/tests/ProjectRulesPanel.test.jsx` — renders the panel with a mixed-rules fixture, asserts toggles and numeric inputs render, and that "Save" / "Reset to defaults" call the PUT endpoint with the expected payload.

## Excluded

- Any automatic gating of execution: the scheduler, worker dispatch, queue ordering, and `tools/agent_runner/run_daemon.py` / `tools/agent_runner/run_ticket.py` remain untouched and continue to schedule tickets exactly as before.
- Worker reservation, retry logic, or any change to the existing execution pipeline.
- New rules beyond the six listed above.
- Migration of historical tickets to populate `ticket_rule_evaluation` retroactively.
- Per-user or per-role rule overrides; rules are scoped to `project_id` only.
- Frontend visualisation of rule evaluation history (only the latest evaluation per ticket is stored and displayed).
- Notifications, webhooks, or alerts triggered by `blocked` evaluations.
- Refactors of the T198 Ticket Intelligence schema or the T199 approval lifecycle beyond reading their existing canonical state.
- Any work under `tools/api/` or `web/` — these paths are not used in T201.

## Acceptance criteria

1. Tables `project_execution_rules` and `ticket_rule_evaluation` are created in both SQLite (`tools/agent_runner/runtime_db.py`) and PostgreSQL (`tools/agent_runner/runtime_db_pg.py`) by the runtime DB initialiser, with the columns specified above.
2. Project rules are configurable through `GET` / `PUT /projects/{project_id}/rules` served by `services/control_api/routes/rules.py`, and the stored set is returned merged with registry defaults.
3. `POST /tickets/{ticket_id}/evaluate-rules` returns HTTP `202 Accepted`, runs `evaluate_ticket` asynchronously via FastAPI `BackgroundTasks`, and the resulting row is retrievable via `GET /tickets/{ticket_id}/rule-evaluation`.
4. `evaluate_ticket` returns `eligibility_status = "blocked"` whenever at least one enabled rule fails, and `"eligible"` only when all enabled rules pass.
5. Every failed rule in the persisted evaluation includes a human-readable reason; warnings are persisted in the `warnings_json` column.
6. The `require_human_approval` rule passes if and only if `compute_execution_eligibility(db_path, ticket_id) == "ready_to_take"`, and is wired through `get_execution_approval_state`, which is the sole bridge between the engine and `tools/agent_runner/ticket_approval_service.py`. The static test `tests/test_execution_rules_approval_isolation.py` confirms `execution_rules_engine.py` never references `ticket_approvals` or `approval_status` directly.
7. With no rows in `project_execution_rules`, the default policy enables `require_ticket_intelligence`, `require_readiness_candidate`, `require_human_approval`, `block_when_human_review_required`, and disables `max_estimated_cost_usd` and `max_difficulty`.
8. The threshold rules `max_estimated_cost_usd` and `max_difficulty` block tickets that exceed their configured limits, and are inert when disabled.
9. The Project Rules panel and page (`apps/dashboard/src/components/ProjectRulesPanel.jsx`, `apps/dashboard/src/pages/ProjectRulesPage.jsx`) allow toggling each rule and editing thresholds; the Ticket Rule Evaluation panel (`apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx`) embedded in `apps/dashboard/src/pages/TicketDetailPage.jsx` displays eligibility status, failed rules with reasons, warnings, and evaluation date, and exposes a "Re-evaluate" action.
10. `tools/agent_runner/run_daemon.py`, `tools/agent_runner/run_ticket.py`, and the scheduler module contain no import of `execution_rules_engine` and no behavioural change; this is enforced by `tests/test_execution_rules_pipeline_untouched.py`.
11. No file is created under `tools/api/` and no file is created under `web/` for T201. The new API routes live under `services/control_api/routes/rules.py`, are registered in `services/control_api/main.py`, and their schemas live in `services/control_api/models/schemas.py`. All dashboard work lives under `apps/dashboard/src/`.
12. The full existing test suite continues to pass alongside the new Python tests under `tests/` and the new dashboard tests under `apps/dashboard/tests/`.

---

## Review

# Plan review — T201 must target the current repo architecture

The T201 plan is conceptually aligned with the issue: it introduces an advisory Execution Rules Engine, persists rule configuration and evaluations, exposes API/UI, and explicitly avoids changing scheduler, worker dispatch, daemon state, or execution queue behavior.

However, the plan targets stale / incorrect repository paths for the API and frontend.

## Blocking issue 1 — API path is wrong

The plan says:

```text
Wire endpoints into tools/api/
place handlers in tools/api/rules.py
register in tools/api/main.py
```

But the current repository uses the Control API under:

```text
services/control_api/
```

Existing related routes are already registered from:

```text
services/control_api/routes/intelligence.py
services/control_api/routes/readiness.py
services/control_api/routes/approvals.py
```

The new rules route must follow the same structure:

```text
services/control_api/routes/rules.py
services/control_api/main.py
```

## Blocking issue 2 — frontend path is wrong

The plan says:

```text
web/
web/lib/api/rules.ts
web/app/projects/[project_id]/rules/page.tsx
web/components/TicketRuleEvaluation.tsx
```

But the current dashboard is under:

```text
apps/dashboard/
```

The ticket detail page and existing panels live under:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
apps/dashboard/src/components/TicketIntelligencePanel.jsx
apps/dashboard/src/components/TicketReadinessPanel.jsx
apps/dashboard/src/components/HumanApprovalPanel.jsx
apps/dashboard/src/api/tickets.js
```

The new UI must target this structure, not `web/`.

## Blocking issue 3 — approval state helper should use existing T199 service

The plan correctly says the rules engine should not query the approval table directly.

However, the plan should explicitly use the existing T199 service:

```text
tools/agent_runner/ticket_approval_service.py::compute_execution_eligibility(db_path, ticket_id)
```

This helper already provides the canonical execution eligibility state such as:

```text
ready_candidate
ready_to_take
blocked
not_started
```

The rules engine should import this helper and expose it only through:

```text
get_execution_approval_state(db_path, ticket_id)
```

## Required correction

Update `runs/T201/plan.md` so that:

1. API work is implemented in `services/control_api/routes/rules.py`.
2. Router registration is done in `services/control_api/main.py`.
3. API schemas are added to `services/control_api/models/schemas.py`.
4. Frontend API helpers are added to `apps/dashboard/src/api/tickets.js` or a sibling file already used by the dashboard.
5. Ticket rule evaluation UI is added under `apps/dashboard/src/components/`.
6. The ticket detail page integration targets `apps/dashboard/src/pages/TicketDetailPage.jsx`.
7. If a Project Rules page is included, it must use the current React Router / dashboard structure, not Next.js `web/app` conventions.
8. The rules engine uses `ticket_approval_service.compute_execution_eligibility(...)` and never reads approval tables directly.

## Review verdict

PLAN_FIX_REQUIRED until the plan targets the current `services/control_api` + `apps/dashboard` architecture and the existing T199 approval service helper.

---

## Instructions de fix

# Plan fix — target current Control API and dashboard paths

## Required plan update

Update `runs/T201/plan.md` before starting implementation.

The current plan is conceptually correct, but it references stale paths from an older architecture:

```text
tools/api/
web/
```

These paths must not be used for T201.

## Correct backend/API paths

Replace:

```text
tools/api/rules.py
tools/api/main.py
```

with:

```text
services/control_api/routes/rules.py
services/control_api/main.py
services/control_api/models/schemas.py
```

The new routes must follow the same style as the existing routes:

```text
services/control_api/routes/intelligence.py
services/control_api/routes/readiness.py
services/control_api/routes/approvals.py
```

Register the new router in `services/control_api/main.py` next to the existing `intelligence`, `readiness`, and `approvals` routers.

## Correct frontend paths

Replace all `web/` / Next.js references with the current dashboard structure:

```text
apps/dashboard/src/
```

Use paths like:

```text
apps/dashboard/src/api/tickets.js
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/pages/TicketDetailPage.jsx
```

If a project-level rules page is implemented in this ticket, it must use the current React Router / dashboard conventions already present in `apps/dashboard`, not `web/app/...` or Next.js conventions.

Possible page/component names:

```text
apps/dashboard/src/pages/ProjectRulesPage.jsx
apps/dashboard/src/components/ProjectRulesPanel.jsx
```

The exact names may vary, but the implementation must remain inside `apps/dashboard/src`.

## Existing approval service to use

The rules engine must not query `ticket_approvals` directly.

It must use the existing helper introduced by the Human Approval Workflow:

```python
from ticket_approval_service import compute_execution_eligibility
```

Then wrap it in:

```python
def get_execution_approval_state(db_path, ticket_id) -> str:
    return compute_execution_eligibility(db_path, ticket_id)
```

Rules receive this value through `RuleContext.approval_state`.

The following must remain true:

```text
execution_rules_engine.py must not query approval tables directly
execution_rules_engine.py must not inspect ticket_approvals directly
execution_rules_engine.py must not duplicate approval lifecycle logic
```

## Updated implementation targets

Backend:

```text
tools/agent_runner/execution_rules_engine.py
tools/agent_runner/runtime_db.py
tools/agent_runner/runtime_db_pg.py
services/control_api/routes/rules.py
services/control_api/models/schemas.py
services/control_api/main.py
```

Frontend:

```text
apps/dashboard/src/api/tickets.js
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/components/ProjectRulesPanel.jsx
apps/dashboard/src/pages/TicketDetailPage.jsx
```

Optional if routing is straightforward in the current dashboard:

```text
apps/dashboard/src/pages/ProjectRulesPage.jsx
```

Tests:

```text
tests/test_execution_rules_db.py
tests/test_execution_rules_engine.py
tests/test_execution_rules_default_policy.py
tests/test_execution_rules_approval_isolation.py
tests/test_execution_rules_api.py
tests/test_execution_rules_pipeline_untouched.py
apps/dashboard/tests/TicketRuleEvaluationPanel.test.jsx
apps/dashboard/tests/ProjectRulesPanel.test.jsx
```

## Acceptance criteria additions

Add these acceptance criteria to the corrected plan:

- No files are created under `tools/api/` for T201.
- No files are created under `web/` for T201.
- API routes live under `services/control_api/routes/rules.py` and are registered in `services/control_api/main.py`.
- API schemas live in `services/control_api/models/schemas.py`.
- Dashboard work lives under `apps/dashboard/src`.
- Rules engine approval state uses `ticket_approval_service.compute_execution_eligibility(...)` through a wrapper and does not read approval tables directly.
- Scheduler, daemon, run-ticket, worker dispatch, and queue code remain untouched.

## Non-goals reminder

Do not implement:

- automatic dispatch
- worker reservation
- scheduler gating
- queue ordering
- daemon behavior changes
- historical rule evaluation history

The Execution Rules Engine remains advisory only in T201.