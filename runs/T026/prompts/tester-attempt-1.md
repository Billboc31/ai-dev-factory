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


# T026 — T026 — Continuous checkpoint publishing and PR lifecycle

**Source**: GitHub Issue #21

## Description

# T026 — Continuous checkpoint publishing and PR lifecycle

## Contexte

Le daemon peut déjà orchestrer les runs locaux, mais pour un usage à distance il ne suffit pas de publier à `TEST_COMPLETE`.

Après chaque step réussi, il faut publier un checkpoint pour que :

- le workspace reste clean
- le step suivant ne soit pas bloqué par les guards Git
- les artefacts soient visibles depuis GitHub
- un reviewer externe puisse lire le plan, le code, les reviews et les logs

Architecture cible :

```text
step success
→ transition workflow
→ commit checkpoint --include-code
→ push branch
→ daemon continue
```

Puis à la fin :

```text
TEST_COMPLETE
→ final checkpoint
→ push
→ create/update PR
→ human merge
→ close source issue
```

## Objectif

Ajouter une publication continue des checkpoints et un lifecycle PR minimal.

## Inclus

### 1. Continuous checkpoint publishing

Après chaque step réussi et transition workflow, le daemon déclenche un commit/push du checkpoint du ticket.

États typiques publiés :

```text
PLAN_REVIEW_NEEDED
IMPLEMENTATION_REVIEW_NEEDED
IMPLEMENTATION_APPROVED
TEST_COMPLETE
PLAN_FIX_REQUIRED
IMPLEMENTATION_FIX_REQUIRED
```

### 2. Remote visibility

Après chaque checkpoint, GitHub doit contenir les artefacts runtime et les fichiers modifiés :

```text
runs/TXXX/plan.md
runs/TXXX/implementation-output.md
runs/TXXX/reviews/*
runs/TXXX/tests/*
runs/TXXX/runtime.log
runs/TXXX/prompts/*
code/tests/docs modifiés
```

### 3. PR lifecycle à TEST_COMPLETE

Quand le ticket atteint `TEST_COMPLETE`, le daemon doit :

- vérifier que le checkpoint final est publié
- créer une PR si absente
- réutiliser ou mettre à jour la PR si elle existe
- lier la PR à l’issue source
- écrire une description utile

### 4. Issue closing après merge

Après merge manuel de la PR, le daemon doit :

- détecter la PR merged
- fermer l’issue source
- retirer le label `ai-ready`
- logguer l’action

### 5. Guardrails

- aucun merge automatique
- aucune PR avant `TEST_COMPLETE`
- aucune mauvaise branche poussée
- respect de `state.json`
- logs explicites

## Hors scope

- auto merge
- slash commands
- review GitHub automatique
- model routing
- UI web
- distributed workers

## Critères d’acceptation

- checkpoint commit/push après chaque step réussi
- pas de commit/push si step échoue
- workspace clean entre les étapes
- artefacts visibles à distance
- PR créée ou mise à jour à `TEST_COMPLETE`
- issue source liée à la PR
- issue fermée après merge détecté
- label `ai-ready` retiré après completion
- aucun merge automatique
- workflow existant compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tools/agent_runner/run_issue_intake.py
tests/
README.md
```