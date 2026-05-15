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

# Generic Planner Task

Read the ticket below and produce a detailed implementation plan.

The plan must include:
- changes to implement (files, functions, logic)
- out-of-scope items
- risks and dependencies
- acceptance criteria

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