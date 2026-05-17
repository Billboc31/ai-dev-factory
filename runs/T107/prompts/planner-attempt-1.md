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


# T107 — T107 — Project guardian regression agent

**Source**: GitHub Issue #49

## Description

# T107 — Project guardian regression agent

## Objectif

Créer un agent global projet chargé de surveiller la santé du projet après merge.

L’agent tourne indépendamment des tickets runtime.

Il surveille principalement :

- branche main
- stabilité globale
- régressions
- qualité runtime

---

## Vision

Flux cible :

```text
Ticket runtime
→ TEST_COMPLETE
→ automatic merge
→ guardian project agent
→ full validation
→ regression issue if needed
```

Le guardian doit fonctionner comme un framework générique capable de tester n’importe quel projet décrit par une configuration projet.

---

## Architecture

Le guardian doit être composé de :

```text
guardian core
+ project profile
```

Le guardian core gère :

- sandbox / clone temporaire
- orchestration runtime
- lancement services
- exécution checks
- smoke tests
- collecte logs
- création issues régression
- cleanup environnement

Le projet décrit ses propres besoins via un fichier de configuration.

---

## Configuration projet

Ajouter un fichier du type :

```text
.ai-dev-factory/project.yml
```

Exemple :

```yaml
project:
  name: ai-dev-factory

services:
  - name: api
    command: uvicorn services.control_api.main:app --reload
    healthcheck: http://localhost:8000/health

  - name: dashboard
    command: npm run dev
    cwd: apps/dashboard
    healthcheck: http://localhost:5173

checks:
  - name: python tests
    command: pytest

  - name: frontend build
    command: npm run build
    cwd: apps/dashboard

smoke_tests:
  - name: dashboard board loads
    type: playwright
    script: tests/e2e/board.spec.ts
```

---

## Fonctionnement

Le guardian peut tourner :

- périodiquement
- après merge
- après push main

Workflow cible :

```text
clone sandbox
→ install deps
→ start services
→ wait healthchecks
→ run checks
→ run smoke tests
→ collect logs
→ create regression issue if needed
→ cleanup sandbox
```

---

## Smoke runtime tests

Le guardian doit pouvoir tester le runtime sans appeler de vrai LLM.

Exemple :

```text
→ create fake smoke issue
→ daemon intake
→ fake planner/coder/reviewer/tester
→ vérifier transitions runtime
→ vérifier dashboard
→ vérifier branches/runs
→ cleanup
```

Le système doit permettre des agents fake/mock pour réduire coût et temps de test.

---

## Régression

Si une régression est détectée :

```text
→ create GitHub issue
→ attach logs
→ mark severity
→ label ai-ready
```

---

## Dashboard

Ajouter une vue :

```text
Project Health
```

avec :

- dernier scan guardian
- état main
- build status
- dernières régressions
- tendance stabilité
- runtime incidents

---

## Contraintes

- Git reste source de vérité
- pas d’auto-revert dans cette V1
- pas d’auto-fix
- pas d’auto-merge obligatoire
- garder logs observables
- compatible multi-projets
- ne pas hardcoder ai-dev-factory dans le guardian core

---

## Critères d’acceptation

- le guardian peut tester la branche main indépendamment des tickets
- les régressions créent automatiquement des issues
- les logs de validation sont persistés
- le dashboard affiche la santé globale du projet
- le guardian peut fonctionner via un fichier project.yml spécifique au projet