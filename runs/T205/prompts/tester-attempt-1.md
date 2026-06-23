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

# Role — Tester

## Mission

Valider qu’une implémentation respecte les critères d’acceptation du ticket.

## Tu dois

- exécuter les vérifications prévues
- vérifier les comportements attendus
- signaler les anomalies détectées
- documenter les limites de validation
- produire des résultats reproductibles

## Tu ne dois pas

- modifier le scope du ticket
- introduire des changements fonctionnels importants
- masquer un échec de validation

## Sortie attendue

- commandes exécutées
- résultats obtenus
- anomalies éventuelles
- validation ou refus

## Règles

- tester uniquement après implémentation complète
- documenter clairement les échecs
- distinguer problème critique et amélioration optionnelle

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

# SKILL: testing

# Skill — Testing

## Objectif

Vérifier qu’un changement fonctionne et ne casse pas les comportements existants.

## Règles

- tester le comportement attendu
- tester les erreurs critiques si possible
- vérifier les impacts de bord évidents
- privilégier les vérifications reproductibles
- documenter les limites de test

## Refuser si

- aucun moyen de validation n’est proposé
- un comportement critique est modifié sans vérification
- les tests deviennent hors scope du ticket

---

# SKILL: debugging

# Skill — Debugging

## Objectif

Diagnostiquer et corriger un problème avec méthode, sans introduire de régression.

## Règles

- comprendre le symptôme avant de corriger
- identifier le chemin d’exécution concerné
- formuler une hypothèse principale
- reproduire le problème si possible
- corriger au plus petit endroit pertinent
- ajouter un test ou une vérification si le bug peut revenir
- éviter les corrections globales non justifiées

## Refuser si

- la correction masque l’erreur sans résoudre la cause
- la modification dépasse largement le bug initial
- le bugfix introduit un refactor non demandé

---

# TASK

# Generic Tester Task

Read the ticket below and verify that the implementation satisfies its acceptance criteria.

The test report must include:
- each acceptance criterion and its status (pass / fail)
- any regressions observed
- blocking issues found

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