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


# T171 — T171 - Environment deploy should use a fresh runtime checkout of the selected branch

**Source**: GitHub Issue #194

## Description

# T171 - Environment deploy should use a fresh runtime checkout of the selected branch

## Problem

Environment deploy currently appears to reuse an existing local project/worktree instead of building from a fresh checkout of the selected repository branch.

Observed effects:

- a branch is selected in the environment UI;
- deploy logs show scripts executing;
- but the deployed code does not match the selected branch;
- fixes present on ticket branches are missing at runtime;
- stale local worktrees influence deployments unexpectedly.

This makes deployments unreliable because the selected branch is not guaranteed to be the code actually deployed.

---

## Goal

Environment deploy must always use a fresh runtime checkout of the selected repository and branch.

Deployments should no longer depend on arbitrary existing local project folders.

---

## Required behavior

For a selected:

- project
- repository
- branch
- environment

The deploy flow must:

1. create a clean runtime source directory;
2. clone the repository into that runtime directory;
3. checkout the selected branch;
4. verify branch and commit before build/start;
5. run bootstrap/build/start/healthcheck from that runtime checkout.

---

## Suggested runtime structure

Example:

```text
environment/<env-id>/
  source/
  runtime/
```

Where:

- `source/` contains the runtime git checkout;
- `runtime/` contains logs/state/validation artifacts.

Equivalent layouts are acceptable if deployments are isolated and deterministic.

---

## Validation

Before build/start, log:

```bash
pwd
git branch --show-current
git rev-parse --short HEAD
```

If the checked out branch does not match the selected branch, deployment must fail.

---

## Important constraints

Do NOT:

- silently fallback to another branch;
- deploy from main when another branch was selected;
- reuse stale local clones unless explicitly requested;
- infer deployment source from the current shell directory.

---

## Acceptance criteria

- Deploying an environment from T170 actually deploys T170 code
- Runtime scripts executed during deploy come from the selected branch
- Branch verification appears in deployment logs
- Existing unrelated local worktrees no longer affect deployments
- Failed clone/checkout aborts deployment clearly
- Multiple environments can deploy different branches concurrently