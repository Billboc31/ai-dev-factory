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


# T138 — T138 — Generic AI sandbox auto-fix loop

**Source**: GitHub Issue #124

## Description

# Objective

Add a generic AI-driven sandbox auto-fix loop able to analyze sandbox deployment failures, modify operational artifacts, rerun validation, and converge toward a successful runtime state.

The implementation must remain generic and must NOT contain ai-dev-factory-specific deployment assumptions.

## Context

T134 introduced sandbox deploy validation.

T137 introduces:
- isolated sandbox ports
- sandbox env files
- compose project isolation
- sandbox lifecycle management
- historical sandbox runs

The next step is an automated correction loop:

sandbox validation fails
→ logs captured
→ AI analyzes failure
→ AI modifies scripts/config
→ sandbox reruns
→ repeat until success or retry limit

## Included

### Generic auto-fix orchestration

- Add a sandbox auto-fix orchestrator.
- Retry loop must be bounded with configurable max retries.
- Each iteration must:
  - capture sandbox state
  - capture logs
  - capture operational scripts
  - call the configured AI runtime
  - apply modifications
  - rerun sandbox validation

### Generic project support

The loop must NOT assume:
- ai-dev-factory project structure
- api/web services
- fixed ports
- docker-only projects
- specific frameworks

The loop must rely on:
- deploy.yml
- sandbox state
- generated operational scripts
- runtime logs
- component definitions
- deploy metadata

### AI fix payload

Provide the AI runtime with:
- deploy profile
- sandbox state
- logs
- failing step
- operational scripts
- relevant runtime metadata

### Safe file modification

- Restrict modifications to allowed operational files.
- Track changed files per iteration.
- Persist iteration history.
- Never modify unrelated runtime state.

### Sandbox rerun

- After fixes are applied:
  - rerun validation
  - capture new logs/state
  - compare iterations

### Dashboard UI

Add auto-fix visibility:
- current iteration
- max retries
- iteration status
- changed files
- logs per iteration
- final outcome

### Failure handling

Handle safely:
- invalid AI output
- malformed patches
- repeated failures
- infinite retry risks
- sandbox crashes
- supervisor disconnects

### Tests

Add tests for:
- successful convergence after fix
- retry limit reached
- malformed AI output
- patch application failure
- generic deploy.yml handling
- iteration history persistence

## Excluded

- automatic merge to main
- production deployment
- cloud deployment
- tester-agent business tests
- self-modifying core runtime outside allowed sandbox artifacts

## Acceptance criteria

- sandbox failures can trigger a generic AI correction loop
- the loop works without ai-dev-factory-specific assumptions
- retries are bounded and observable
- iteration history is persisted and visible
- sandbox reruns after fixes
- malformed AI output is safely rejected
- the system never enters infinite retry loops
- successful fixes result in sandbox success state
- failed retries result in clean terminal failed state