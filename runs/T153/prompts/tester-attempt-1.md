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


# T153 — T153 — Generic smoke tests and bounded auto-fix deployment loop

**Source**: GitHub Issue #158

## Description

Goal: make the Deployer able to converge toward a functional ephemeral environment by running healthchecks, smoke tests, and a bounded AI auto-fix loop.

Context:
The intended Deployer flow is not just `docker compose up`.

Expected Deployer role:
- audit the project
- generate/update deployment scripts
- deploy an ephemeral sandbox environment
- run healthchecks
- run real smoke tests
- if validation fails, ask the configured AI runtime to propose/apply safe fixes
- redeploy and retest
- repeat until success or retry limit
- cleanup/undeploy automatically after success

Current limitation:
- we mostly have healthchecks today
- healthchecks only prove that services respond
- they do not prove that the application actually works
- auto-fixing only against healthchecks risks optimizing for "starts" rather than "works"

Scope:

1. Generic smoke test layer
- define a generic smoke test lifecycle after healthcheck
- support generated project-specific smoke tests
- prefer `.ai-dev-factory/scripts/smoke.sh` or equivalent lifecycle declaration
- smoke tests must use sandbox/proxy URLs when available
- fallback to allocated direct ports only when proxy URLs are absent
- smoke test output must be captured in logs and state

2. Deployer validation pipeline
- deploy ephemeral sandbox
- run healthcheck
- run smoke tests
- collect result state:
  - health status
  - smoke test status
  - failing step
  - logs
  - generated artifacts

3. Bounded AI auto-fix loop
- on failure, collect context and call the configured AI runtime
- no hardcoded provider or Claude-specific SDK
- use existing exec_cmd / AI runtime abstraction
- restrict modifications to allowed deployment artifacts first:
  - `.ai-dev-factory/scripts/*`
  - deploy profile files
  - compose/env/deployment config files explicitly allowed by policy
- apply patch in sandbox/worktree only
- redeploy and retest
- repeat up to configurable max retries
- stop if the same failure repeats without progress
- persist iteration history

4. Safety and observability
- max retry limit required
- each iteration records:
  - failure reason
  - changed files
  - patch summary
  - health result
  - smoke result
  - logs
- never merge automatically
- never modify unrelated application source files in this first version
- final diff must be visible and reviewable

5. Cleanup
- on success, undeploy/cleanup ephemeral validation environment
- on terminal failure, preserve logs/state/artifacts for inspection

Out of scope:
- production deployment
- cloud deployment
- automatic merge to main
- full tester-agent business/UAT tests
- modifying arbitrary product code
- persistent environment management

Acceptance:
- Deployer can run healthcheck plus smoke tests
- smoke tests are clearly distinguished from healthchecks in state/UI
- Deployer can run a bounded auto-fix loop after failures
- AI fixes are constrained to allowed deployment artifacts
- every iteration is persisted and observable
- successful loop ends with a functional ephemeral environment and cleanup
- failed loop ends cleanly with logs and iteration history
- no provider-specific AI SDK is hardcoded
- implementation remains generic and project-agnostic