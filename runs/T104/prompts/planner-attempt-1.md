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


# T104 — T104 — Per-ticket worker worktrees and isolated runtime execution

**Source**: GitHub Issue #46

## Description

# T104 — Per-ticket worker worktrees and isolated runtime execution

## Contexte

Le modèle actuel exécute tous les tickets dans un seul clone Git local.

Même avec les améliorations T101/T102/T103, cette architecture provoque encore des problèmes structurels :

- conflit de branche courante
- dirty tree partagé
- checkpoint Git sensibles
- difficulté de parallélisation
- runtime fragile lorsqu’un ticket agit pendant qu’un autre est actif

Le problème principal est qu’un seul working tree Git est partagé entre plusieurs tickets.

---

## Vision cible

Transformer le daemon en architecture supervisor + workers isolés.

Le supervisor reste sur le repo principal et orchestre :

```text
issues
queue
capacity
board
worker lifecycle
```

Chaque ticket actif possède ensuite :

- son propre git worktree
- son propre cwd
- son propre runtime/logs/locks
- sa propre branche checkoutée

---

## Architecture cible

### Repo principal

```text
~/ai-dev-factory
```

Contient :

- supervisor daemon
- dashboard
- orchestration globale
- queue
- intake GitHub

---

### Worktrees ticket

```text
~/ai-dev-factory-worktrees/T104
~/ai-dev-factory-worktrees/T105
~/ai-dev-factory-worktrees/T106
```

Chaque worktree contient :

- branche ticket dédiée
- artefacts du ticket
- runtime isolé
- logs locaux du worker

---

## Objectif

Supprimer les conflits Git inter-ticket et préparer une vraie exécution parallèle contrôlée.

---

## Travail demandé

### 1. Créer un lifecycle worktree

Ajouter des helpers :

```text
create_ticket_worktree(ticket_id, branch)
remove_ticket_worktree(ticket_id)
get_ticket_worktree_path(ticket_id)
```

Utiliser :

```bash
git worktree add
```

Le worktree doit être créé automatiquement avant le lancement du worker.

---

### 2. Introduire la notion de worker ticket

Le supervisor daemon ne doit plus exécuter directement les étapes agent.

À la place :

```text
supervisor
→ lance worker T104
→ monitor worker
→ update board
```

Le worker exécute :

```text
planner
coder
reviewer
tester
```

uniquement dans son worktree.

---

### 3. Isoler les fichiers runtime

Chaque worker doit avoir :

```text
runs/T104/runtime.log
runs/T104/worker.pid
runs/T104/worker.lock
```

Le supervisor possède ses propres fichiers séparés.

---

### 4. Préparer la parallélisation future

Même si `max_active_workers=1` reste la valeur par défaut :

l’architecture doit permettre plus tard :

```text
T104 running
T105 waiting human
T106 running
```

sans conflit Git.

---

### 5. Intégrer au dashboard

Le dashboard doit afficher :

```text
Supervisor status
Workers list
Worker state
Worker branch
Worker cwd
Worker runtime status
```

Exemple :

```text
T104 — worker running planner
T105 — waiting human
T106 — queued
```

---

### 6. Gestion lifecycle worker

Définir clairement :

```text
worker start
worker stop
worker cleanup
worktree cleanup
worker crash handling
```

Ne jamais supprimer automatiquement un worktree contenant des changements non commités.

---

## Contraintes

- Git reste source de vérité
- pas de DB runtime dédiée
- pas de `git add .`
- pas d’auto-merge
- conserver les human gates
- supervisor et workers doivent être observables via logs
- éviter toute duplication de state machine

---

## Critères d’acceptation

- chaque ticket actif possède son propre worktree Git
- les tickets n’utilisent plus le même working tree local
- le supervisor n’exécute plus directement les étapes agent
- les logs/locks/runtime sont isolés par worker
- plus aucun conflit de branche courante entre tickets
- la board affiche les workers actifs
- l’architecture permet la parallélisation future