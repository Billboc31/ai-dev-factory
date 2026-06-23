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


# T208 — Fix Ticket Intelligence analysis stuck in running state

**Source**: GitHub Issue #272

## Description

# Fix Ticket Intelligence analysis stuck in running state

## Context

The Ticket Intelligence feature currently fails to complete analyses reliably.

Observed behavior:

```text
User clicks 'Analyze'
↓
analysis status = running
↓
analysis never completes
↓
after 900 seconds
↓
reaper marks analysis as failed
```

UI error:

```text
Analysis failed

Analysis stuck in 'running' for 900s — auto-recovered by reaper.
```

This makes Ticket Intelligence effectively unusable.

## Problem

The analysis lifecycle enters:

```text
running
```

but never reaches:

```text
completed
```

or

```text
failed
```

The reaper eventually detects the stale analysis and forces failure.

Possible causes include:

- background worker never starts
- exception swallowed inside background task
- AI call hangs indefinitely
- subprocess never exits
- missing timeout on LLM execution
- analysis result never persisted
- status transition never executed
- deadlock while updating runtime database

## Goal

Guarantee that every Ticket Intelligence analysis eventually reaches:

```text
completed
```

or

```text
failed
```

with a meaningful error message.

No analysis should remain indefinitely in:

```text
running
```

## Scope

Investigate the complete Ticket Intelligence execution pipeline:

```text
UI trigger
↓
Control API endpoint
↓
background execution
↓
AI invocation
↓
database persistence
↓
status transitions
↓
reaper interaction
```

## Required changes

### Background execution reliability

Verify that analysis jobs always start and always terminate.

Unexpected exceptions must never be silently swallowed.

All exceptions must:

```text
log error
persist failure reason
set status = failed
```

### AI timeout handling

Ensure all AI/model invocations have explicit timeouts.

### Runtime persistence

Successful analyses always persist:

```text
status = completed
completed_at
analysis payload
```

Failures must persist:

```text
status = failed
error_message
failed_at
```

### Observability

Add detailed runtime logging:

```text
analysis started
analysis step started
AI request started
AI request completed
analysis persisted
analysis failed
```

### Reaper improvements

The reaper should preserve original failure causes when known instead of always replacing them with the generic timeout message.

## Tests

Add tests covering:

- successful execution
- AI timeout
- unexpected exception path
- reaper recovery
- no silent failures

## Acceptance criteria

- No Ticket Intelligence analysis remains indefinitely in `running`.
- Every analysis eventually becomes `completed` or `failed`.
- AI calls use explicit timeouts.
- Exceptions are logged and persisted.
- Failure reasons are visible in UI.
- Reaper preserves original failure causes when available.
- Runtime logs clearly show analysis lifecycle steps.
- Existing Ticket Intelligence functionality continues to work.
- All new and existing tests pass.