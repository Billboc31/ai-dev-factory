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



# T197 — Add advisory ticket intelligence analysis before development cycle

**Source**: GitHub Issue #251

## Description

# Add advisory ticket intelligence analysis before development cycle

## Context

AI Dev Factory now has a real database and can persist structured metadata per ticket.

Before a ticket enters the normal development cycle, we want to run an analysis agent that classifies the ticket and stores useful decision data.

This step must not influence scheduling or execution yet. For now, it only enriches each ticket with analysis metadata and displays it on the ticket detail page.

This is intended to prepare future scheduling, model routing, cost control, dependency handling, and parallel execution decisions.

## Goal

Add a new pre-development analysis step that evaluates each ticket and stores advisory intelligence metadata.

The analysis should include:

- estimated difficulty
- risk level
- implementation complexity
- expected AI model needed
- explanation of model choice
- estimated cost range
- recommended queue order
- dependency hints
- whether human plan review is required
- whether human code review is required
- whether the ticket looks safe for autonomous execution

## Important design requirement: hybrid analysis

The analyzer must use AI for reasoning, classification, and recommendation, but it should not rely only on AI.

Some deterministic or semi-deterministic parts should be computed in code, likely Python, because AI is not the best tool for every signal.

Examples of non-AI / Python-computed signals:

- ticket text length
- number of explicit requirements
- number of acceptance criteria
- presence of risky keywords such as `database`, `migration`, `scheduler`, `auth`, `security`, `deployment`, `multi-project`, `worker`, `daemon`
- detected affected domains: backend, frontend, database, infra, orchestration, UI, tests
- dependency references like `depends on`, `after T001`, `requires`, `blocked by`
- number of linked issues or ticket IDs mentioned
- estimated token size
- rough file-impact estimate from keywords or repository search
- whether the ticket changes scheduler/runtime behavior
- whether it likely needs DB migration

The AI should then consume these computed signals plus the ticket content and produce the final advisory classification.

Suggested flow:

```text
Ticket created / refreshed
↓
Python deterministic feature extractor
↓
AI Ticket Intelligence Analyzer
↓
JSON validation / normalization
↓
Persist analysis in DB
↓
Display on ticket page
```

## Non-goals

Do not change the current ticket execution behavior yet.

This ticket must not:

- block ticket execution
- reorder the queue automatically
- enforce dependencies
- change worker scheduling
- prevent agents from starting
- implement parallel execution rules
- automatically choose the model for execution

Those behaviors will be handled in later tickets.

## New concept

Introduce a new agent step:

```text
Ticket Intelligence Analyzer
```

It runs before the normal development cycle:

```text
Ticket created
↓
Ticket Intelligence Analyzer
↓
Planning
↓
Coding
↓
Review
↓
Testing
↓
Deployment
```

For now, the analyzer is informational only.

## Data to store

For each ticket, persist an analysis record in the database.

Suggested fields:

```text
ticket_id
analysis_status
difficulty_score
difficulty_label
risk_score
risk_label
complexity_factors
computed_signals_json
recommended_model
recommended_model_reason
estimated_input_tokens
estimated_output_tokens
estimated_cost_min
estimated_cost_max
cost_currency
cost_estimate_status
queue_rank
queue_reason
dependency_hints
parallel_safe_candidate
requires_human_plan_review
human_plan_review_reason
requires_human_code_review
human_code_review_reason
autonomous_execution_recommendation
analysis_summary
created_at
updated_at
```

## Difficulty scoring

The analyzer should compute a difficulty score from 1 to 10.

Example labels:

```text
1-2  trivial
3-4  simple
5-6  medium
7-8  complex
9-10 critical
```

The score should consider both deterministic signals and AI reasoning:

- number of files likely impacted
- database changes
- architecture changes
- frontend/backend scope
- tests required
- deployment impact
- security impact
- scheduler/runtime impact
- dependency on previous tickets
- ambiguity of requirements
- risk of breaking existing behavior

## Risk scoring

The analyzer should compute a risk score from 1 to 10.

Risk factors include:

- changes to scheduler / worker orchestration
- changes to project isolation
- changes to database schema
- changes to deployment/runtime
- security/auth concerns
- changes that affect multiple projects
- stale-branch or dependency-sensitive work
- unclear acceptance criteria

## Model recommendation

The analyzer should recommend the most appropriate AI model for the ticket.

Example output:

```text
recommended_model: advanced-reasoning-model
recommended_model_reason: Requires architecture reasoning, dependency analysis, and careful backend implementation planning.
```

The model choice should consider:

- ticket complexity
- amount of reasoning needed
- need for code generation
- need for review accuracy
- expected token usage
- acceptable cost
- risk level
- whether a local model may be sufficient

The implementation should keep the model catalog configurable.

Example model catalog:

```text
local-qwen
cheap-fast-model
balanced-code-model
advanced-reasoning-model
```

No hardcoded provider-specific logic should be required at this stage.

## Cost estimation

The analyzer should estimate cost using:

```text
estimated input tokens
estimated output tokens
selected model pricing
```

If pricing is unknown, store:

```text
cost_estimate_status: unknown
```

The cost estimate can be approximate.

Example:

```text
estimated_cost_min: 0.05
estimated_cost_max: 0.35
cost_currency: USD
```

## Queue rank recommendation

The analyzer should propose a queue rank for the ticket.

This is only advisory for now.

It should consider:

- explicit dependencies
- detected dependency hints
- ticket difficulty
- foundational tickets first
- architecture/setup tickets before feature tickets
- blocking tickets before dependent tickets
- low-risk independent tickets may be good early candidates

Example:

```text
queue_rank: 20
queue_reason: Backend foundation should run before CRUD API and frontend integration tickets.
```

## Human review recommendation

The analyzer should decide whether the ticket likely needs human plan review.

Examples requiring human plan review:

- architecture decision
- dependency or scheduler changes
- database schema change
- security/auth change
- deployment change
- multi-project orchestration
- high cost/risk ticket
- ambiguous requirements

Example:

```text
requires_human_plan_review: true
human_plan_review_reason: The ticket changes scheduler behavior and may affect all project runs.
```

## UI requirements

On the ticket detail page, display a new section:

```text
Ticket Intelligence
```

It should show:

- difficulty label and score
- risk label and score
- recommended model
- estimated cost range
- queue rank recommendation
- human plan review recommendation
- human code review recommendation
- autonomous execution recommendation
- analysis summary
- last analysis date

The UI should clearly indicate that this analysis is advisory only.

Example badge:

```text
Advisory only — not used by scheduler yet
```

## API requirements

Expose the analysis through the existing ticket API.

Suggested endpoints:

```text
GET /api/tickets/:ticketId/intelligence
POST /api/tickets/:ticketId/intelligence/analyze
```

The POST endpoint should run or re-run the analyzer for a ticket.

## Database requirements

Add a table for ticket intelligence analysis.

Suggested table:

```text
ticket_intelligence
```

It should be linked to the existing ticket record.

Only one current analysis per ticket is required for now.

Historical analysis versions are optional and can be added later.

## Agent prompt

Create a prompt for the Ticket Intelligence Analyzer.

The prompt should instruct the agent to return structured JSON with fields like:

```json
{
  "difficulty_score": 6,
  "difficulty_label": "medium",
  "risk_score": 5,
  "risk_label": "moderate",
  "complexity_factors": ["backend", "database", "UI"],
  "recommended_model": "advanced-reasoning-model",
  "recommended_model_reason": "Requires architecture reasoning, dependency analysis, and careful backend implementation planning.",
  "estimated_input_tokens": 12000,
  "estimated_output_tokens": 6000,
  "estimated_cost_min": 0.05,
  "estimated_cost_max": 0.35,
  "cost_currency": "USD",
  "cost_estimate_status": "estimated",
  "queue_rank": 20,
  "queue_reason": "Backend foundation should run before CRUD API and frontend integration tickets.",
  "dependency_hints": ["T001"],
  "requires_human_plan_review": true,
  "human_plan_review_reason": "The ticket changes scheduler behavior and may affect all project runs.",
  "requires_human_code_review": false,
  "parallel_safe_candidate": false,
  "autonomous_execution_recommendation": "plan_review_required",
  "analysis_summary": "This ticket is medium difficulty and moderate risk because it touches backend persistence and UI display but does not yet affect scheduling."
}
```

## Acceptance criteria

- A ticket can be analyzed before entering the dev cycle.
- Analysis results are stored in the database.
- Re-running the analysis updates the stored result.
- The ticket detail page displays the analysis.
- The analysis includes difficulty, risk, model recommendation, cost estimate, queue rank, dependency hints, and human review recommendation.
- The analyzer uses a hybrid approach: deterministic feature extraction in code plus AI-based classification/recommendation.
- Computed deterministic signals are persisted or visible enough for debugging.
- The current scheduler behavior is unchanged.
- No ticket is blocked, reordered, or auto-routed based on this analysis yet.
- The UI clearly states that the analysis is advisory only.
- Tests cover database persistence, API response, analyzer normalization, and UI rendering.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Now I have enough context to produce the plan.

## Objective

Add a hybrid (deterministic + AI) Ticket Intelligence Analyzer that runs before the development cycle, persists structured advisory metadata per ticket in the database, exposes it through two new API endpoints, and displays it on the ticket detail page — without affecting any scheduling or execution behavior.

## Included

### Database

- **`tools/agent_runner/runtime_db.py`**: add `CREATE TABLE IF NOT EXISTS ticket_intelligence` with all fields from the ticket spec (`ticket_id`, `analysis_status`, `difficulty_score`, `difficulty_label`, `risk_score`, `risk_label`, `complexity_factors`, `computed_signals_json`, `recommended_model`, `recommended_model_reason`, `estimated_input_tokens`, `estimated_output_tokens`, `estimated_cost_min`, `estimated_cost_max`, `cost_currency`, `cost_estimate_status`, `queue_rank`, `queue_reason`, `dependency_hints`, `parallel_safe_candidate`, `requires_human_plan_review`, `human_plan_review_reason`, `requires_human_code_review`, `human_code_review_reason`, `autonomous_execution_recommendation`, `analysis_summary`, `created_at`, `updated_at`). One row per ticket (upsert on `ticket_id`).

### Deterministic Feature Extractor

- **`tools/agent_runner/ticket_intelligence_extractor.py`** (new file): pure-Python module, no AI dependency. Computes and returns a `ComputedSignals` dict from raw ticket text:
  - text length, requirement count, acceptance criteria count
  - presence of risky keywords (`database`, `migration`, `scheduler`, `auth`, `security`, `deployment`, `multi-project`, `worker`, `daemon`)
  - affected domains (`backend`, `frontend`, `database`, `infra`, `orchestration`, `UI`, `tests`) inferred from keyword scan
  - dependency references (`depends on`, `after T\d+`, `requires`, `blocked by`) + count of referenced ticket IDs
  - estimated token size (character count ÷ 4)
  - rough file-impact estimate (count of risky-domain keyword hits)
  - boolean flags: `changes_scheduler`, `likely_needs_db_migration`

### AI Ticket Intelligence Analyzer

- **`tools/agent_runner/ticket_intelligence_analyzer.py`** (new file): orchestrates the hybrid flow:
  1. Calls the extractor to get `computed_signals`
  2. Loads prompt template, injects ticket content + computed signals
  3. Calls the configured AI model (via existing Claude API integration pattern in the project)
  4. Parses and validates the JSON response against expected field names and types
  5. Normalizes/clamps numeric scores (1–10), fills `cost_estimate_status: "unknown"` when pricing unavailable
  6. Persists result to `ticket_intelligence` via `runtime_db.py`

### Agent Prompt

- **`ai/roles/ticket-intelligence-analyzer.md`** (new file): role definition for the analyzer agent
- **`prompts/ticket-intelligence-analyzer-prompt.md`** (new file): canonical prompt template instructing the model to return the exact JSON schema from the ticket spec; includes placeholder sections for `{{ticket_content}}` and `{{computed_signals}}`

### Model Catalog

- **`tools/agent_runner/model_catalog.py`** (new file): a small configurable dict mapping logical names (`local-qwen`, `cheap-fast-model`, `balanced-code-model`, `advanced-reasoning-model`) to cost-per-token values and provider hints. Read-only at this stage; no routing side-effects.

### API Layer

- **`services/control_api/routes/intelligence.py`** (new file):
  - `GET /api/tickets/{ticket_id}/intelligence` — fetches current analysis row from DB, returns 404 if none exists
  - `POST /api/tickets/{ticket_id}/intelligence/analyze` — triggers the analyzer synchronously, persists result, returns it
- **`services/control_api/main.py`**: register the new router with prefix `/api/tickets`
- **`services/control_api/models/schemas.py`**: add `TicketIntelligence` Pydantic model matching all DB fields

### Frontend

- **`apps/dashboard/src/components/TicketIntelligencePanel.jsx`** (new file): displays all advisory fields in a card/section; includes "Advisory only — not used by scheduler yet" badge; shows a "Re-analyze" button that calls `POST /api/tickets/:id/intelligence/analyze`; handles loading and error states
- **`apps/dashboard/src/pages/TicketDetailPage.jsx`**: import and render `<TicketIntelligencePanel ticketId={...} />` below the existing timeline section

### Tests

- **`tests/test_ticket_intelligence_extractor.py`** (new): unit tests for all deterministic signals on synthetic ticket strings; covers keyword detection, dependency hint parsing, token estimation
- **`tests/test_ticket_intelligence_api.py`** (new): integration tests for both API endpoints — 404 when no analysis exists, happy-path GET after POST, re-run updates `updated_at`
- **`tests/test_ticket_intelligence_db.py`** (new): tests DB upsert behavior — second insert updates rather than duplicates
- **`apps/dashboard/tests/TicketIntelligencePanel.test.jsx`** (new): Vitest tests for panel rendering with mock data, advisory badge presence, re-analyze button behavior

## Excluded

- Changing ticket scheduling, queue ordering, or worker dispatch based on the analysis
- Blocking or auto-routing tickets based on `autonomous_execution_recommendation`
- Implementing parallel execution rules
- Automatically selecting the AI execution model from the analysis output
- Storing historical analysis versions (only the latest record per ticket is kept)
- Provider-specific API integration logic in the model catalog (only logical names and cost hints)
- Admin UI for editing or overriding analysis results

## Acceptance criteria

- `GET /api/tickets/{ticket_id}/intelligence` returns 404 for a ticket with no analysis, and returns all expected fields after an analysis has been run
- `POST /api/tickets/{ticket_id}/intelligence/analyze` runs the hybrid analyzer and persists the result; a second call updates `updated_at` without creating a duplicate row
- `computed_signals_json` in the DB contains the output of the deterministic extractor (independently verifiable)
- `difficulty_score` and `risk_score` are integers in [1, 10]; `cost_estimate_status` is `"unknown"` when the model is not in the catalog
- The ticket detail page displays the "Ticket Intelligence" section with all advisory fields and the "Advisory only — not used by scheduler yet" badge
- The "Re-analyze" button triggers `POST` and refreshes the panel without a full page reload
- Existing ticket states, the scheduler loop, and the worker dispatch logic are unmodified (confirmed by existing test suite passing)
- `pytest tests/test_ticket_intelligence_*.py` and `vitest apps/dashboard/tests/TicketIntelligencePanel.test.jsx` all pass

---

## Review

# Plan review — T197 async execution and model abstraction

The T197 plan is generally aligned with the issue goal: it adds an advisory Ticket Intelligence Analyzer, stores structured metadata in the database, exposes API endpoints, and displays the result on the ticket detail page without changing scheduler behavior.

However, two points must be fixed before implementation starts.

## Blocking issue 1 — POST analyze should not block indefinitely

The current plan says:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze — triggers the analyzer synchronously, persists result, returns it
```

This is risky because the analyzer calls an AI model. Depending on model latency, network behavior, prompt size, or retries, the HTTP request could block the UI for too long or hit a timeout.

The implementation should avoid designing this endpoint as a long-running blocking call.

Acceptable approaches:

- enqueue an intelligence analysis job and return quickly with `202 Accepted`
- or perform a bounded synchronous execution with strict timeout and clear status fields

Preferred approach for this ticket:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze
→ creates/updates ticket_intelligence row with analysis_status = queued or running
→ starts the analyzer through the existing worker/job mechanism if available
→ returns current analysis state quickly
```

If no job mechanism exists yet, a bounded synchronous MVP is acceptable only if:

- timeout is explicit
- failure is stored as `analysis_status = failed`
- UI handles running/failed states
- endpoint does not hang indefinitely

## Blocking issue 2 — do not hardcode Claude-specific integration

The current plan says:

```text
Calls the configured AI model (via existing Claude API integration pattern in the project)
```

This is too provider-specific. The whole point of Ticket Intelligence is to recommend and later route by model, so the analyzer must use the existing project abstraction for agent/model execution, not hardcode Claude.

The plan must be corrected to say:

```text
Calls the configured AI model through the existing AI Dev Factory agent/model execution abstraction.
```

The model catalog should contain logical model identifiers and pricing hints, but must not force one provider.

## Required correction

Rewrite or amend `runs/T197/plan.md` so that:

1. The analyzer uses the existing agent/model execution abstraction, not direct Claude-specific code.
2. The analyze endpoint is non-blocking or bounded with explicit timeout/failure handling.
3. `analysis_status` supports at least:

```text
not_started
queued
running
completed
failed
```

4. The UI can render loading/running/failed states.
5. Scheduler and worker dispatch behavior remain unchanged.

## Review verdict

PLAN_FIX_REQUIRED until the plan clarifies async/bounded analysis execution and removes provider-specific Claude assumptions.

---

## Instructions de fix

# Plan fix — make T197 analysis bounded/non-blocking and provider-agnostic

## Required plan update

Update `runs/T197/plan.md` before starting the coder.

The plan is functionally good, but it must be corrected in two areas:

1. AI execution must be provider-agnostic.
2. The analysis endpoint must not be an unbounded synchronous AI call.

## 1. Use AI Dev Factory model/agent abstraction

Replace any Claude-specific wording such as:

```text
via existing Claude API integration pattern
```

with:

```text
via the existing AI Dev Factory agent/model execution abstraction
```

The analyzer must not directly depend on a specific provider.

It should work with logical model names from the model catalog, for example:

```text
local-qwen
cheap-fast-model
balanced-code-model
advanced-reasoning-model
```

Provider-specific configuration can exist behind the abstraction, but the Ticket Intelligence Analyzer should not hardcode Claude, OpenAI, local models, or any other provider.

## 2. Avoid unbounded synchronous POST analyze

The current plan proposes:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze
```

as a synchronous endpoint that runs the analyzer and returns the result.

This must be changed.

Preferred behavior:

```text
POST /api/tickets/{ticket_id}/intelligence/analyze
→ validates the ticket exists
→ creates or updates ticket_intelligence with analysis_status = queued or running
→ triggers analysis via the existing job/worker mechanism if available
→ returns quickly with the current analysis state
```

Recommended HTTP response:

```text
202 Accepted
```

with body like:

```json
{
  "ticket_id": "T197",
  "analysis_status": "queued"
}
```

If AI Dev Factory does not yet have a generic background job mechanism suitable for this, a bounded synchronous MVP is acceptable for this ticket only if all of the following are true:

- the AI call has an explicit timeout
- failures are persisted with `analysis_status = failed`
- timeout errors are visible in the API response and UI
- the frontend never waits indefinitely
- tests cover timeout/failure handling

## 3. Analysis status lifecycle

The database and API must support at least these statuses:

```text
not_started
queued
running
completed
failed
```

Suggested behavior:

- no row yet: API may return 404 or `not_started`, but the behavior must be consistent
- POST analyze: `queued` or `running`
- successful analyzer result: `completed`
- validation / timeout / model failure: `failed`

## 4. UI behavior

`TicketIntelligencePanel` must handle:

- no analysis yet
- queued/running analysis
- completed analysis
- failed analysis

The button label may change depending on state:

```text
Analyze
Re-analyze
Analysis running
Retry analysis
```

The advisory badge must remain visible:

```text
Advisory only — not used by scheduler yet
```

## 5. Scheduler remains untouched

This fix must not introduce scheduler behavior changes.

The analysis remains advisory only.

Do not:

- reorder queue automatically
- block tickets
- route execution to selected model
- change worker dispatch
- enforce dependency rules

## Updated acceptance criteria

The corrected plan is acceptable only if:

- AI execution uses the existing model/agent abstraction, not Claude-specific direct integration
- `POST /api/tickets/{ticket_id}/intelligence/analyze` is non-blocking or explicitly bounded with timeout handling
- `analysis_status` supports queued/running/completed/failed states
- failures and timeouts are persisted and displayed
- UI handles running and failed states cleanly
- scheduler and worker dispatch are unchanged