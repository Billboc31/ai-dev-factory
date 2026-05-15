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


# T030 — T030 — Live daemon activity feed and auto-refresh

**Source**: GitHub Issue #30

## Description

# T030 — Live daemon activity feed and auto-refresh

## Contexte

Le système dispose maintenant :

- d’un daemon d’orchestration
- d’une Control API REST
- d’un dashboard UI React
- de tickets pilotables depuis l’UI

Mais l’UI reste principalement statique.

Les tickets ne se mettent pas à jour automatiquement et les logs/runtime nécessitent des refresh manuels.

Le prochain cap est d’obtenir une expérience “runtime vivant” permettant de suivre l’activité du daemon en quasi temps réel.

Architecture cible :

```text
Daemon runtime
↓
Control API
↓
Dashboard auto-refresh
```

## Objectif

Ajouter un système de rafraîchissement automatique et un feed d’activité daemon.

Le dashboard doit montrer les changements runtime sans nécessiter de refresh manuel.

## Inclus

### 1. Auto-refresh tickets list

`TicketsPage` doit se rafraîchir automatiquement.

Exemple :

```text
polling 5s
```

Les changements d’état doivent apparaître automatiquement :

```text
PLANNER_RUNNING
→ PLAN_REVIEW_NEEDED
→ CODER_RUNNING
→ IMPLEMENTATION_REVIEW_NEEDED
```

### 2. Auto-refresh TicketDetailPage

Quand un ticket est ouvert :

- refresh automatique de `state.json`
- refresh automatique des logs
- refresh automatique des reviews/tests/artefacts si le ticket change

### 3. Daemon activity feed

Ajouter un panneau montrant les dernières activités daemon.

Exemples :

```text
[10:41:02] daemon started
[10:41:18] T030 planner started
[10:41:44] T030 PLAN_REVIEW_NEEDED
[10:42:01] T030 coder started
```

Le feed peut être basé sur :

```text
runtime.log
ou
un nouveau daemon.log
```

### 4. Live daemon status

Le statut daemon doit être rafraîchi automatiquement.

Exemple :

```text
running
stopped
last heartbeat
current ticket
```

### 5. Polling management

Le polling doit être proprement nettoyé :

- `clearInterval`
- pas de memory leak
- pas de polling multiple accidentel

### 6. UX minimale

Ajouter :

- indicateurs loading subtils
- badges runtime plus vivants
- indication “updated X seconds ago” si simple à implémenter

Pas de design avancé requis.

### 7. Tests

Ajouter des tests pour :

- polling lifecycle
- cleanup interval
- refresh automatique
- daemon feed rendering
- changement d’état runtime

## Hors scope

- websocket
- SSE
- push realtime serveur
- auth
- multi-user
- notifications push
- mobile app
- animations avancées
- terminal intégré

## Critères d’acceptation

- les tickets se rafraîchissent automatiquement
- TicketDetailPage se met à jour automatiquement
- le statut daemon est live
- un feed daemon existe
- les changements runtime apparaissent sans refresh manuel
- aucun polling zombie
- les tests couvrent les mécanismes de polling
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
apps/dashboard/
services/control_api/
tests/
README.md
```