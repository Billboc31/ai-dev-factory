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


# T102 — T102 — Daemon intake synchronization, queue policy and board view

**Source**: GitHub Issue #43

## Description

# T102 — Daemon intake synchronization, queue policy and board view

## Contexte

Après les premiers runs réels du daemon, plusieurs besoins apparaissent au-delà des bugs corrigés par T101.

T101 traite le hardening immédiat : timeline mapping, ticket id allocation, dirty tree, checkpoint/push avant PR.

Ce ticket T102 cible le comportement d’orchestration global du daemon :

- synchronisation Git avant intake
- éviter d’aspirer toutes les issues `ai-ready`
- politique de queue/concurrence
- visibilité globale dans le dashboard

---

## Problèmes observés / risques

### 1. Intake lancé depuis une branche non-main ou main stale

Le daemon peut être lancé alors que le repo local est sur une branche ticket.

Avant d’ingérer une nouvelle issue GitHub, il faut garantir :

```text
checkout main
pull origin main
then compute ticket id
then create ticket branch
```

Sinon risques :

- ticket id calculé sur un état local stale
- branche créée depuis une mauvaise base
- collisions ou runs incohérents
- dashboard/PR basés sur une branche inattendue

---

### 2. Trop d’issues `ai-ready` peuvent être ingérées d’un coup

Le daemon ne doit pas être un aspirateur à issues.

Si plusieurs issues ont le label `ai-ready`, il faut une politique claire :

```text
max_active_tickets = 1 par défaut
```

Le daemon doit pouvoir décider :

- intake une seule issue
- attendre si un ticket est déjà actif
- ne pas lancer de nouveaux tickets si le système est occupé
- plus tard, autoriser certains tickets parallélisables

---

### 3. Besoin d’une vue board globale

La timeline par ticket est utile, mais il manque une vue globale pour piloter le daemon.

Il faut voir :

```text
Backlog ai-ready
Queued
Running
Waiting human
Retry cooldown
Blocked
PR ready
Done
```

Cette vue doit aider à comprendre :

- ce que le daemon va prendre ensuite
- ce qui est bloqué
- ce qui attend une action humaine
- ce qui est en PR
- pourquoi une issue n’est pas encore lancée

---

## Objectif

Transformer le daemon en orchestrateur contrôlé avec une queue explicite et une visibilité globale.

Le daemon doit rester local-first et Git-native.

---

## Travail demandé

### 1. Synchroniser Git avant intake

Avant tout intake d’une issue GitHub :

```text
assert working tree clean or abort safely
checkout main
pull origin main
then run issue intake
```

Contraintes :

- ne pas écraser de changements locaux
- ne pas checkout main si working tree dirty inconnu
- logs explicites :

```text
syncing main before issue intake
checkout main completed
pull origin main completed
```

---

### 2. Ajouter une politique de queue/concurrence

Ajouter une configuration simple :

```text
max_active_tickets = 1
```

Un ticket est actif si :

- state auto-runnable en cours
- lock présent
- étape running détectée
- PR lifecycle en cours
- retry cooldown actif

À discuter/implémenter prudemment : les tickets en gate humaine peuvent soit bloquer la queue, soit permettre un autre ticket selon une option future.

Pour cette V1 : comportement conservateur recommandé :

```text
si un ticket non terminal existe et n’est pas archivé → ne pas intake une nouvelle issue
```

ou variante :

```text
si uniquement waiting human → intake autorisé seulement si config allow_parallel_waiting_human=true
```

---

### 3. Ne pas intake toutes les issues `ai-ready`

Quand plusieurs issues sont candidates :

- trier par priorité/date
- sélectionner au maximum 1 issue si capacité disponible
- logger les autres comme queued/skipped-for-capacity

Labels futurs possibles :

```text
ai-priority-high
ai-parallelizable
ai-blocked
ai-manual-only
```

Ne pas forcément implémenter tous les labels dans cette V1, mais garder le design extensible.

---

### 4. Ajouter une API board

Ajouter un endpoint :

```text
GET /daemon/board
```

ou :

```text
GET /tickets/board
```

La réponse doit regrouper les tickets/issues par colonnes :

```json
{
  "columns": [
    { "id": "backlog", "label": "Backlog", "items": [] },
    { "id": "queued", "label": "Queued", "items": [] },
    { "id": "running", "label": "Running", "items": [] },
    { "id": "waiting_human", "label": "Waiting human", "items": [] },
    { "id": "blocked", "label": "Blocked", "items": [] },
    { "id": "pr_ready", "label": "PR ready", "items": [] },
    { "id": "done", "label": "Done", "items": [] }
  ]
}
```

La board doit être une projection des artefacts existants, pas une nouvelle source de vérité.

---

### 5. Ajouter une vue dashboard board

Ajouter dans l’IHM une page ou section :

```text
Daemon Board
```

Elle doit afficher :

- backlog issues `ai-ready`
- tickets locaux
- état courant
- gate humaine éventuelle
- retry/cooldown éventuel
- PR si connue
- raison si non lancé

---

## Contraintes

- Ne pas dupliquer la state machine de `run_ticket.py`
- Ne pas créer de DB dédiée pour la queue en V1
- Git reste source de vérité
- Pas de `git add .`
- Pas d’auto-merge
- Le dashboard reste client de la Control API
- Aucun checkout/pull si le working tree contient des changements inconnus

---

## Critères d’acceptation

- le daemon synchronise `main` avant intake d’une nouvelle issue
- le daemon ne lance pas toutes les issues `ai-ready` simultanément
- une limite de capacité existe, au moins `max_active_tickets=1`
- les issues non lancées sont visibles comme queued/skipped-for-capacity
- une API board expose les colonnes principales
- le dashboard affiche une vue board globale
- les logs expliquent pourquoi une issue est lancée ou non
- aucun `git add .`