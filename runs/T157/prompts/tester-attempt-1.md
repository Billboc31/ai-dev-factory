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


# T157 — T157 - Ensure deployer fetches and checks out the requested branch before deployment

**Source**: GitHub Issue #164

## Description

## Objective

Ensure the deployer always deploys the exact requested ref/branch, not a stale local checkout or an outdated main branch.

## Context

Recent runtime UI changes were pushed to a ticket branch, but the deployed sandbox did not visually reflect them. A likely cause is that the deployer creates or reuses a worktree without first fetching the remote and checking out the requested branch/ref at the latest remote commit.

This breaks confidence in runtime validation: a sandbox URL may be healthy while serving old code.

## Problem

The deployer must make the deployed code identity explicit and deterministic.

Current risks:

- deploying stale `main`
- deploying a stale local branch
- deploying a branch before fetching recent remote pushes
- not showing clearly which commit/ref was deployed
- validating the wrong code while healthcheck/smoke tests still pass

## Expected behavior

Before deploying a sandbox, the deployer must:

1. Resolve the requested ref/branch explicitly.
2. Fetch the remote branch before checkout.
3. Create/update the sandbox worktree from the fetched remote ref.
4. Record the deployed ref, branch, and commit SHA in sandbox state/metadata.
5. Fail early with a clear error if the requested ref cannot be fetched or resolved.

For a ticket branch such as:

```text
ticket/T156-t156-improve-runtime-tab-with-running-environments
```

The deployer should fetch and deploy the latest remote commit for that exact branch.

## Included

- Update deployer/sandbox bootstrap logic so requested branch/ref is fetched before worktree creation or reuse.
- Prefer deterministic remote refs such as `origin/<branch>` when deploying ticket branches.
- Ensure worktree checkout points to the latest fetched commit for the requested branch.
- Persist deployed identity in sandbox state, including:
  - requested_ref
  - resolved_ref
  - branch name when applicable
  - commit SHA
- Add logs showing:
  - requested ref
  - fetched remote ref
  - resolved commit SHA
  - worktree path
- Add/adjust tests for stale branch prevention.

## Excluded

- No changes to Traefik routing.
- No changes to port allocation.
- No changes to smoke test semantics.
- No automatic merge/rebase behavior.
- No mutation of the main production clone beyond safe `git fetch`.
- No persistent environment management changes.

## Constraints

- Never mutate the main clone working tree.
- Work must happen in sandbox worktrees.
- `git fetch` is allowed on the source clone, but deployment checkout must remain isolated.
- If the branch does not exist remotely, fail loudly instead of silently falling back to `main`.
- Do not infer GitHub issue number from ticket id.

## Acceptance criteria

- Deploying a ticket branch fetches the latest remote commit before sandbox creation.
- The sandbox worktree HEAD equals the fetched remote branch HEAD.
- If a new commit is pushed to a ticket branch, a subsequent deploy uses that new commit.
- If the requested branch/ref does not exist, deployment fails with a clear error and does not deploy `main` silently.
- Sandbox state/metadata exposes the deployed ref and commit SHA.
- Runtime UI can display the deployed commit/ref from sandbox metadata.
- Existing deploys from `main` still work.
- Existing sandbox isolation guarantees remain intact.