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

## Artifact-only output (strict)

Your response will be written verbatim to `runs/<ticket>/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.

This rule applies to both initial plans and rewrites after a review.
Examples of forbidden openings: "The plan has been rewritten…",
"This plan now covers…", "Plan rewritten as a real implementation
document…", "Key points covered…", "The document now contains…",
"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".

Do not use the Write tool on `plan.md` and then print a status summary —
your stdout IS the artifact. If you do write the file, stdout must still
be the full plan (same four headings), not a report about it.

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



# T230 — Batch UI: show per-ticket pipeline status while batch is frozen/waiting

**Source**: GitHub Issue #317

## Description

## Problem
When a backlog batch is `frozen`, the UI mostly shows the batch status alone. That status is not self-explanatory: `frozen` means “collection stopped”, not “dependency analysis running”.

Operators cannot see **which tickets are blocking the next stage** (e.g. Ticket Intelligence still `running` on T003–T006), so a batch looks stuck for no visible reason.

## Expected UX
On the batch detail / batch list view, show a clear per-ticket breakdown of what each member is doing and what the batch is waiting on.

For each ticket in the batch, surface at least:
- ticket id + title/issue number
- Ticket Intelligence status (`not_started` / `queued` / `running` / `completed` / `failed`)
- Readiness status (when applicable)
- runtime state (INIT, PLANNING, …)
- a short “blocking reason” when the batch cannot advance

At batch level, show an explicit waiting summary, e.g.:
- `Waiting on Ticket Intelligence: T003, T004, T005, T006`
- or `Ready for dependency analysis`
- or `Dependency analysis running`
- or `Waiting on readiness: …`

## Why
`frozen` is a gate before `dependency_analysis_running`. Without per-ticket visibility, the IHM feels stuck and operators restart daemons / open issues unnecessarily.

## Acceptance criteria
- [ ] Batch IHM shows per-ticket intelligence / readiness / runtime status for all batch members
- [ ] While status is `frozen`, UI explains that collection is closed and which tickets still block dependency analysis
- [ ] When all intelligence is complete, UI clearly transitions messaging toward dependency analysis (and shows analysis progress/errors if any)
- [ ] Empty/missing pipeline rows are shown as not started, not hidden

## Notes
Related lifecycle: `collecting → frozen → dependency_analysis_running → readiness_running → dispatching → completed`.
Gate today: `batch_intelligence_complete()` requires every member `analysis_status == completed` before analysis starts.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T230/plan.md`.
You MUST rewrite that file with the corrected plan. Leaving it
unchanged is rejected by the factory.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

## Objective

Surface per-ticket Ticket Intelligence, readiness, and runtime state on the batch detail page, and add a compact waiting summary to the batch list, so operators can see exactly what a `frozen` batch is waiting on before dependency analysis starts.

## Included

### Backend

**`services/control_api/models/schemas.py`**
- Add `TicketPipelineRow` model: `ticket_id`, `issue_number: int | None`, `title: str | None`, `intelligence_status: str`, `readiness_status: str | None`, `runtime_state: str | None`, `is_blocking: bool`, `blocking_reason: str | None`
- Add `BatchPipelineStatusResponse` model: `batch_id: str`, `batch_status: str`, `waiting_summary: str`, `tickets: list[TicketPipelineRow]`
- Add `pipeline_summary: str | None = None` optional field to `BatchSummary`

**`services/control_api/routes/batches.py`**
- Add `_compute_pipeline_summary(db_path, batch_status: str, ticket_ids: list[str]) -> str | None` helper — uses a single JOIN query to count incomplete intelligence rows; returns a compact string ("Waiting on Ticket Intelligence (3 pending)", "Ready for dependency analysis", etc.); returns `None` for terminal statuses. Used to populate `BatchSummary.pipeline_summary`.
- Add `_build_pipeline_status(db_path, project_root, batch_id, ticket_ids, worktrees_dir) -> BatchPipelineStatusResponse` helper — fetches `ticket_intelligence`, `ticket_readiness`, and `ticket_runtime` rows per ticket using existing `runtime_db.get_ticket_intelligence`, `runtime_db.get_ticket_readiness`, and `_ticket_runtime_map`; titles via `_read_ticket_title`; computes `waiting_summary` and `is_blocking` per ticket; tickets absent from pipeline tables appear with `intelligence_status="not_started"`.
- Add `GET /{batch_id}/pipeline-status` route on `router` returning `BatchPipelineStatusResponse`.
- Add the project-scoped variant on `project_router` under `/{project_id}/dispatcher/batches/{batch_id}/pipeline-status`.
- Update `_build_summary()` to call `_compute_pipeline_summary()` and populate `pipeline_summary`.

**`waiting_summary` string rules (implemented in `_build_pipeline_status`):**
- `collecting` → `"Collecting — {N} member(s) so far"`
- `frozen` + incomplete intelligence → `"Waiting on Ticket Intelligence: {T001}, {T002}, …"`
- `frozen` + all intelligence complete → `"Ready for dependency analysis"`
- `dependency_analysis_running` → `"Dependency analysis running"`
- `dependency_analysis_failed` → `"Dependency analysis failed — retry pending"`
- `readiness_running` → `"Readiness evaluation running"`
- `dispatching` → `"Dispatching tickets"`
- `completed` → `"Batch completed"`

### Frontend

**`apps/dashboard/src/api/batches.js`**
- Add `getBatchPipelineStatus(projectId, batchId)` → `GET /dispatcher/batches/{batchId}/pipeline-status` (with project-scoped path when `projectId` is set, matching the pattern used by `getBatch`).

**`apps/dashboard/src/components/BatchPipelineStatusPanel.jsx`** (new file)
- Prop: `data` (a `BatchPipelineStatusResponse` object), `batchStatus` string.
- Renders a colored banner for `waiting_summary`: yellow when frozen with blocking tickets, green when ready/complete, gray otherwise.
- Renders a table with columns: Ticket ID | Title | Intelligence | Readiness | Runtime State | Blocking reason.
- Status badges use consistent color coding: `not_started` gray, `queued` blue, `running` indigo (animated), `completed` green, `failed` red.
- Missing `readiness_status` (null) displayed as `—` not hidden.
- Missing `runtime_state` (null) displayed as `—` not hidden.

**`apps/dashboard/src/pages/BatchDetailPage.jsx`**
- Import `BatchPipelineStatusPanel` and `getBatchPipelineStatus`.
- Add a `usePolling` call for `getBatchPipelineStatus(projectId, batchId)` alongside the existing polling calls.
- Render `<BatchPipelineStatusPanel>` near the top of the detail layout — before the dependency graph and phases panels — so it is immediately visible; visible for all batch statuses.

**`apps/dashboard/src/pages/BatchesPage.jsx`**
- In each batch card (for the current/next batch display and the list), render `batch.pipeline_summary` as a small italic line below the status badge when the value is non-null.

## Excluded

- Changes to the batch lifecycle state machine or dispatcher logic.
- Triggering or re-queuing intelligence analysis from the UI.
- Modifying existing panels: `BatchAnalysisSummaryPanel`, `BatchDependencyGraph`, `BatchPhasesPanel`, `DispatcherInsightsPanel`.
- Per-ticket intelligence detail panels beyond what `BatchPipelineStatusPanel` provides.
- Sorting, filtering, or pagination of the pipeline status table.
- Real-time WebSocket/SSE updates (existing `usePolling` interval is sufficient).
- Changes to ticket-level intelligence or readiness routes.

## Acceptance criteria

- `GET /dispatcher/batches/{batch_id}/pipeline-status` returns `waiting_summary` string, `batch_status`, and a `tickets` array with `intelligence_status`, `readiness_status`, `runtime_state` for every batch member.
- Tickets absent from `ticket_intelligence` or `ticket_readiness` tables are included in the response with `intelligence_status="not_started"` (not omitted).
- `BatchSummary.pipeline_summary` is non-null for `collecting` and `frozen` statuses and is reflected in `GET /dispatcher/batches` list response.
- Batch detail page renders `BatchPipelineStatusPanel` for all batch statuses; when `frozen` with incomplete intelligence, the banner names the blocking ticket IDs.
- When all tickets have `intelligence_status == "completed"` and batch status is `frozen`, `waiting_summary` is `"Ready for dependency analysis"`.
- Batch list cards show `pipeline_summary` text for `frozen` and `collecting` batches.
- No regressions in existing batch detail panels (graph, phases, insights, analysis summary).

---

## Review

# T230 Plan Review 01

## Verdict

`PLAN_FIX_REQUIRED`

## Summary

The plan is directionally correct and covers the main visibility gap for frozen batches: per-ticket Ticket Intelligence/readiness/runtime state, a batch-level waiting summary, and a dedicated dashboard panel.

However, one important part of the ticket is not fully specified yet: **readiness blocking visibility**.

The ticket explicitly requires the batch UI to explain what the batch is waiting on, including readiness when applicable, and to show a short blocking reason per ticket. The current plan introduces `readiness_status`, `is_blocking`, and `blocking_reason`, but does not define the rules that make readiness-blocked tickets identifiable or reflected in the batch waiting summary.

## Blocking issues

### 1. Readiness blockers are not fully represented in `waiting_summary`

The plan defines:

- `readiness_running` → `"Readiness evaluation running"`

but does not define how to surface the actual tickets that are still blocking readiness progression when that information is available.

This leaves a gap versus the expected UX from the issue, which explicitly calls for messages such as:

- `Waiting on readiness: T003, T006`

The plan must explain how readiness-blocking tickets are detected and when the batch-level summary names them.

### 2. `is_blocking` / `blocking_reason` rules are underspecified

The response model contains:

- `is_blocking`
- `blocking_reason`

but the plan does not define deterministic rules for populating them across relevant pipeline stages.

At minimum, the plan should specify blocking semantics for:

- missing / incomplete Ticket Intelligence while the batch is frozen;
- failed Ticket Intelligence where it prevents progression;
- readiness states that prevent dispatch/progression;
- non-blocking runtime states, so runtime display does not accidentally become a second source of workflow truth.

The UI should not have to infer blocking logic from raw statuses.

### 3. Tests do not explicitly cover the new blocking logic

Because the core value of this ticket is making workflow waiting reasons trustworthy, the plan should explicitly include backend tests for the summary/blocking computation and frontend tests for the visible readiness-blocked state.

Important cases include:

- frozen + one or more incomplete intelligence rows;
- frozen + all intelligence complete;
- readiness stage with one or more blocking tickets;
- missing pipeline rows shown as `not_started` rather than omitted;
- failed intelligence/readiness state producing a visible blocking reason;
- completed/non-blocking states not being incorrectly marked as blockers.

## Risks if implemented as currently planned

- The batch may still look ambiguous once it reaches readiness, reproducing the same operational problem this ticket is intended to solve.
- Different frontend/backend code paths may derive blocking state differently because the rules are not defined centrally.
- `is_blocking` and `blocking_reason` could become inconsistent or effectively cosmetic fields.
- Regressions in waiting-state calculation may go unnoticed without explicit tests.

## Non-blocking observations

The plan's use of existing runtime DB helpers and polling architecture is reasonable. A possible N+1 pattern from per-ticket lookups is worth keeping in mind, but it is not a blocker for this ticket unless batch sizes make it materially expensive.

---

## Instructions de fix

# T230 Plan Fix 01

Revise `runs/T230/plan.md` to close the readiness-visibility gap identified in `runs/T230/reviews/plan-review-01.md`.

## Required corrections

### 1. Define readiness blocking semantics

The plan must explicitly define how the backend determines which tickets are blocking the batch during readiness-related stages.

Do not make the frontend infer blocking from raw statuses.

Specify the source of truth and deterministic rules used to populate, per ticket:

- `is_blocking`
- `blocking_reason`

Cover at least:

- missing / incomplete Ticket Intelligence while the batch is frozen;
- failed Ticket Intelligence when it prevents progression;
- readiness states that prevent the batch from progressing to dispatch;
- states that are informational only and must not be treated as blockers.

### 2. Extend batch-level waiting summary rules for readiness

The plan must cover the issue requirement that operators can see which tickets are blocking readiness when applicable.

Add a readiness-specific waiting-summary rule such as:

`Waiting on readiness: T003, T006`

when individual blocking tickets can be identified.

If the lifecycle has a state where readiness is merely executing and no individual blocker can yet be determined, `Readiness evaluation running` is acceptable for that specific situation, but the plan must clearly distinguish the two cases.

The summary must remain derived from backend workflow state rather than duplicated frontend logic.

### 3. Add explicit tests for blocking/waiting computation

Update the plan to include backend tests for the pipeline-status computation and frontend tests for rendering the resulting states.

At minimum cover:

- frozen + incomplete intelligence → blocking ticket IDs are named;
- frozen + all intelligence completed → `Ready for dependency analysis`;
- readiness stage with identifiable blocking tickets → readiness summary names those tickets;
- missing intelligence/readiness rows remain visible with `not_started` / `—` as appropriate;
- failed intelligence or readiness state produces an explicit visible blocking reason where it blocks progression;
- completed/non-blocking tickets are not incorrectly flagged as blockers.

## Constraints

- Keep the existing architecture proposed by the plan unless a concrete repository constraint requires adjustment.
- Do not change the batch lifecycle state machine or dispatcher behaviour as part of this fix.
- Do not add frontend-side workflow inference that duplicates backend business logic.
- Do not expand scope into retries/requeue actions, WebSocket/SSE updates, or ticket detail views.

After applying these corrections, update `runs/T230/plan.md` itself so the revised plan is the new source of truth for the next review.