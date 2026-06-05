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


# T176 — T176 - Redeploy must rehydrate missing sandbox source clone and support advanced runtime path override

**Source**: GitHub Issue #204

## Description

# T176 - Redeploy must rehydrate missing sandbox source clone and support advanced runtime path override

## Problem

Environment redeploy currently fails when the sandbox source clone is missing or incomplete.

Observed failure:

```text
runtime mismatch: scripts directory not found at
/Users/.../sandboxes/.../source/.ai-dev-factory/scripts
— sandbox source clone missing or not initialized
```

This means redeploy assumes the `source/` clone already exists and is fully initialized.

However:

- stopped environments may lose their source clone
- partial/incomplete bootstrap can leave a broken source state
- runtime cleanup may remove source data
- redeploy should be resilient and self-healing

---

## Root cause

Current redeploy flow:

```text
resolve scripts path
→ expect source/.ai-dev-factory/scripts to exist
→ fail hard if missing
```

Expected behavior:

```text
redeploy
→ verify source clone exists
→ if missing/incomplete:
   - recreate sandbox source clone
   - checkout correct branch/ref
   - restore scripts
→ continue bootstrap
```

---

## Goal

Make redeploy self-healing and resilient.

If the sandbox source clone is missing or invalid:

- automatically recreate it
- restore the correct branch/ref
- continue deployment

Additionally:

- expose advanced runtime path override options in the environment creation UI
- while keeping auto-configuration as the default

---

## Required backend behavior

### Redeploy validation

Before resolving script paths:

validate:

- `sandbox_dir/source` exists
- `.git` exists
- `.ai-dev-factory/scripts` exists
- branch/ref is available

If invalid:

- log explicit diagnostics
- recreate source clone automatically
- checkout requested branch/ref
- continue deployment

---

## Required logging

On redeploy:

```text
source clone missing or invalid
rehydrating sandbox source clone
repo=<repo>
branch=<branch>
source_path=<path>
```

After restore:

```text
sandbox source clone restored successfully
```

---

## UI changes

Keep runtime path auto-configuration by default.

Add an optional advanced section:

```text
[ Advanced runtime options ]
```

Allow overriding:

- sandbox root
- runtime root
- source path

Also allow:

- force source clone refresh
- reset/reclone source

---

## Important constraints

Default/simple flow must remain automatic.

Advanced runtime controls:

- hidden by default
- intended for debugging/recovery
- must validate path ownership and consistency

---

## Acceptance criteria

- Redeploy no longer fails when `source/.ai-dev-factory/scripts` is missing
- Missing source clone is automatically recreated
- Correct branch/ref is restored automatically
- Logs clearly indicate clone rehydration
- Advanced runtime options are available but collapsed by default
- Users can force source refresh/reclone
- Runtime validation still prevents cross-runtime path mismatches