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
document…", "Key points covered…", "The document now contains…".

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



# T205 — T205 - Compact Ticket Intelligence UI with expandable detailed analysis

**Source**: GitHub Issue #266

## Description

# T205 - Compact Ticket Intelligence UI with expandable detailed analysis

## Context

Ticket Intelligence is valuable, but the current display is too long for day-to-day use.

When an operator is triaging tickets quickly, they should not have to read a large analysis block just to understand whether a ticket is risky, expensive, blocked, or suitable for autonomous execution.

The UI should separate:

```text
quick operational summary
```

from:

```text
detailed audit / reasoning
```

This ticket improves usability only. It must not change the analyzer logic, scheduler behavior, rules engine, readiness evaluator, approvals, or dispatcher behavior.

## Goal

Make the Ticket Intelligence panel compact and scannable by default, while keeping the full analysis available behind an expandable section.

The panel should help answer quickly:

```text
How hard is this ticket?
How risky is it?
How expensive might it be?
Which model is recommended?
Is human review required?
Is it blocked by dependencies?
Can it run in parallel?
```

## Non-goals

Do not:

- change Ticket Intelligence analysis generation
- change persisted intelligence fields
- change scheduler behavior
- change readiness evaluation
- change rules evaluation
- change approval workflow
- change dispatcher / worker behavior
- remove existing detailed data from the UI

## Frontend requirements

Update:

```text
apps/dashboard/src/components/TicketIntelligencePanel.jsx
```

or the current equivalent component.

### Compact summary section

By default, show a compact summary card with key fields:

```text
Difficulty
Risk
Estimated cost
Recommended model
Human plan review
Human code review
Dependencies
Parallel safe candidate
Autonomous recommendation
Last analysis date
```

Recommended layout:

```text
Ticket Intelligence
[Advisory only]

Difficulty     7/10 Medium
Risk           6/10 Moderate
Cost           $0.05 - $0.35
Model          advanced-reasoning-model
Plan review    Required
Dependencies   T001, T004
Parallel safe  No
```

Use badges and short labels instead of long paragraphs.

### One-line summary

Show `analysis_summary` as a short paragraph under the key fields.

If the summary is long, clamp it visually or limit display height.

### Expandable detailed analysis

Move verbose fields into a collapsed section:

```text
Show detailed analysis
```

When expanded, display:

- complexity factors
- model recommendation reason
- cost estimate details
- queue rank reason
- dependency hints
- human review reasons
- computed deterministic signals
- raw or verbose AI output if available

The detailed section should be collapsed by default.

### Optional raw JSON/debug section

If the component currently displays raw JSON or large diagnostic content, move it behind:

```text
Show raw intelligence data
```

This should be collapsed by default and styled as debug information.

### Empty/running/failed states

Keep or improve existing handling for:

```text
not_started
queued
running
completed
failed
```

The completed state must use the compact summary by default.

### Re-analyze action

Keep the existing analyze / re-analyze button behavior.

Do not change backend semantics.

## UX requirements

- The default panel should fit comfortably on a laptop screen without forcing a long scroll.
- Important warnings should remain visible without expanding details.
- High risk / human review required / failed analysis should be visually obvious.
- Detailed reasoning should remain accessible for audit and debugging.

## Backend requirements

No backend changes are required unless the current API does not expose a concise enough summary field.

If a backend change is absolutely necessary, it must be additive only and must not change analyzer output semantics.

## Tests

Add or update frontend tests for the Ticket Intelligence panel.

Suggested tests:

- completed analysis renders compact summary fields
- detailed analysis is collapsed by default
- clicking `Show detailed analysis` reveals verbose fields
- raw/debug data is collapsed by default if present
- failed/running/not_started states still render correctly
- re-analyze button remains available where expected

## Acceptance criteria

- Ticket Intelligence panel is compact by default.
- Key operational fields are visible without expanding anything.
- Long reasoning / verbose data is hidden behind an expandable section.
- Raw/debug information is hidden behind a separate collapsed section if present.
- Existing analyze / re-analyze behavior still works.
- No scheduler, dispatcher, readiness, rules, approval, or worker behavior is changed.
- Existing tests continue to pass.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T205/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

# T205 Plan Placeholder

## Context

This placeholder file was created to unblock the planner workflow after a PLAN_FIX_REQUIRED transition.

The previous plan was considered stale because `main` changed after the original planning step.

## Required action

The planner MUST regenerate this file completely from the current `main` branch.

The regenerated plan must:

- re-read the current dashboard architecture
- inspect the current Ticket Intelligence panel implementation
- preserve existing ticket detail panels
- implement a compact-first Ticket Intelligence UI
- hide long reasoning sections behind expandable panels
- avoid modifying scheduler, worker, readiness, approval, rules, diagnostics, or operations logic

## Status

THIS FILE IS A TEMPORARY PLACEHOLDER ONLY.

It must be fully replaced by a newly generated plan before implementation starts.

---

## Review

# Plan review — main changed, replan required

The current T205 plan must not be implemented as-is because `main` has changed since the plan was generated.

T205 touches the Ticket Intelligence UI. This area is actively connected to recent work around:

- Ticket Intelligence
- Ticket Readiness
- Human Approval
- Execution Rules
- Ticket Diagnostics
- Ticket Operations
- project-scoped dashboard routes

Because the dashboard and ticket detail page have evolved, the existing plan may be stale and may target outdated component structure, props, API helpers, or layout assumptions.

## Required action

Recalculate the plan from the current `main` before the coder starts.

The planner must re-read the current files from `main`, especially:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
apps/dashboard/src/components/TicketIntelligencePanel.jsx
apps/dashboard/src/components/TicketReadinessPanel.jsx
apps/dashboard/src/components/HumanApprovalPanel.jsx
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/components/TicketDiagnosticsPanel.jsx
apps/dashboard/src/api/tickets.js
services/control_api/routes/intelligence.py
services/control_api/models/schemas.py
```

If any of these files have moved or changed, the plan must adapt to the current repository structure.

## Product requirement reminder

The goal of T205 is not to remove detail from Ticket Intelligence.

The goal is to make the default UI compact and usable:

```text
show high-value summary first
hide long reasoning by default
allow expansion when needed
```

The compact view should prioritize:

- difficulty score / label
- risk score / label
- recommended model
- estimated cost
- human review requirement
- dependencies / blocking hints
- short summary
- analysis status / last analyzed date

Detailed analysis should be behind an expandable section.

Raw/debug data should be either hidden by default or placed in a secondary advanced section.

## Review verdict

PLAN_FIX_REQUIRED because the plan was generated against stale `main` and must be recalculated before implementation.

---

## Instructions de fix

# Plan fix — recalculate T205 from current main

## Required plan update

Before coding T205, regenerate `runs/T205/plan.md` from the current `main` branch.

The previous plan is considered stale because `main` changed after it was generated.

Do not patch the old plan incrementally unless the planner first reloads the current repository state and confirms every referenced file and component still exists.

## Files that must be re-read from current main

The corrected plan must inspect the current implementation of:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
apps/dashboard/src/components/TicketIntelligencePanel.jsx
apps/dashboard/src/components/TicketReadinessPanel.jsx
apps/dashboard/src/components/HumanApprovalPanel.jsx
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/components/TicketDiagnosticsPanel.jsx
apps/dashboard/src/api/tickets.js
services/control_api/routes/intelligence.py
services/control_api/models/schemas.py
```

If new panels or components have been added since the original plan, the corrected plan must preserve their order and avoid breaking the ticket detail layout.

## Correct target

T205 should only improve the Ticket Intelligence UI.

It must not modify:

- Ticket Intelligence analyzer logic
- Ticket Readiness logic
- Human Approval logic
- Execution Rules logic
- Ticket Diagnostics logic
- Ticket Operations logic
- scheduler / dispatcher / worker behavior
- database schema unless strictly necessary for display compatibility

## UI behavior expected

The corrected plan should implement a compact-first Ticket Intelligence panel.

Default collapsed/summary view should show:

```text
analysis status
last analyzed date
difficulty score + label
risk score + label
recommended model
estimated cost range
human plan review required yes/no
human code review required yes/no
dependency hints
short analysis summary
```

Long sections should be hidden by default behind expanders such as:

```text
Show details
Show reasoning
Show raw/debug data
```

The UI should remain useful when fields are missing or unknown.

## UX requirements

The default page must be scannable.

Avoid rendering long JSON blobs or long reasoning text by default.

Use concise badges/cards for the summary.

Use expandable sections for:

- complexity factors
- dependency hints
- model reasoning
- cost breakdown
- raw computed signals
- raw AI response / debug data, if currently exposed

## Tests to update/add

The corrected plan should include tests for:

- compact summary renders important fields
- detailed reasoning is hidden by default
- clicking expand shows detailed analysis
- unknown/missing fields do not crash the panel
- existing re-analyze behavior still works
- ticket detail page still renders all existing panels

## Acceptance criteria additions

Add these acceptance criteria to the recalculated plan:

- The plan explicitly states it was recalculated from current `main`.
- The implementation targets the current `apps/dashboard/src/components/TicketIntelligencePanel.jsx` location.
- The Ticket Intelligence panel is compact by default.
- Long detail/reasoning/raw sections are collapsed by default.
- Users can expand details when needed.
- Existing Ticket Detail panels remain mounted and functional.
- No scheduler, dispatcher, worker, readiness, rules, diagnostics, approval, or operations behavior is changed.

## Review verdict after fix

After the plan is regenerated against current `main`, it can be reviewed again for `PLAN_APPROVED`.