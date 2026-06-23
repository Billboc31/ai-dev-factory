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


# T206 — T206 - Fix Ticket Intelligence analysis never completing due to supervisor/API state desynchronization

**Source**: GitHub Issue #267

## Description

# T206 - Fix Ticket Intelligence analysis never completing due to supervisor/API state desynchronization

## Problem

Ticket Intelligence analyses sometimes never complete from the dashboard perspective.

Observed behavior:

```text
User clicks Analyze
↓
status becomes queued
↓
UI displays "Analysis in progress..."
↓
analysis never completes
```

The issue appears intermittently when the Control API delegates analysis execution to the Supervisor because Claude is not available inside the API container.

Potential causes:

- Control API and Supervisor are not reading/writing the same runtime database.
- Analysis completion is persisted in a different runtime root.
- UI polling never observes the final status.
- The supervisor endpoint returns successfully but the final state is never visible from the dashboard API.
- The analysis thread fails silently after delegation.

## Context

Current flow:

```text
Dashboard
↓
POST /tickets/{id}/intelligence/analyze
↓
Control API
↓
if claude unavailable
↓
delegate to Supervisor
↓
Supervisor runs analyzer
↓
result written to DB
↓
Dashboard polls GET /tickets/{id}/intelligence
```

The final GET may not see the same persisted state.

## Goals

Fully diagnose and fix Ticket Intelligence lifecycle synchronization.

Guarantee that:

```text
queued
→ running
→ completed | failed
```

always becomes visible in the dashboard.

## Required investigation

Investigate:

### Runtime paths

Verify:

```text
AI_DEV_FACTORY_RUNTIME_ROOT
runs directory
worktrees directory
database path
```

used by:

```text
Control API
Supervisor
Analyzer
```

Ensure all components use the same project runtime.

### Database consistency

Verify:

```text
runtime_db.upsert_ticket_intelligence()
get_ticket_intelligence()
```

operate on the same DB file across all processes.

Log effective DB paths during analysis.

### Delegation flow

Verify:

```text
POST /projects/{project_id}/tickets/{ticket_id}/intelligence/analyze
```

on Supervisor:

- analysis starts
- analysis finishes
- final state persisted
- errors persisted

### UI polling

Verify dashboard polling behavior.

Ensure polling stops only when:

```text
completed
failed
```

and not because of stale or missing state.

## Required improvements

Add structured logs:

```text
analysis queued
analysis started
analysis completed
analysis failed
analysis delegated
analysis DB path
runtime root path
```

If delegation fails:

```text
analysis_status = failed
```

must always be persisted.

Never leave tickets permanently in:

```text
queued
running
```

without timeout or recovery.

## Recovery requirements

Add stale analysis detection.

Example:

```text
queued > 10 minutes
running > 15 minutes
```

should automatically transition to:

```text
failed
```

with a clear diagnostic message.

## Tests

Add tests covering:

- local analysis execution
- delegated supervisor execution
- shared DB persistence
- analysis timeout
- failed AI subprocess
- stale queued analysis recovery
- stale running analysis recovery
- dashboard polling reaching completed state

## Acceptance criteria

- Ticket Intelligence never remains indefinitely queued or running.
- Dashboard always receives the final completed or failed state.
- API, Supervisor, and analyzer use the same runtime DB for a project.
- Delegated analysis behaves identically to local analysis.
- Failures are persisted and visible in the UI.
- Diagnostic logs clearly show the analysis lifecycle.