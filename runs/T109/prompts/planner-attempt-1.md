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


# T109 — T109 — Atomic runtime checkpoint and worktree-safe commit/push lifecycle

**Source**: GitHub Issue #54

## Description

# T109 — Atomic runtime checkpoint and worktree-safe commit/push lifecycle

## Contexte

Avant l’introduction des worktrees (T104), les transitions runtime fonctionnaient implicitement dans un seul repo/cwd.

Après T104/T105, plusieurs bugs sont apparus :

- état runtime modifié mais non commit/push
- dirty worktree après transition runtime
- commit/push exécuté depuis le mauvais cwd
- restart daemon refusé à cause d’un dirty tree
- transitions planner/coder/reviewer/tester non atomiques

Exemple observé :

```text
PLAN_APPROVED
→ implementation-output.md créé
→ state.json modifié
→ aucun commit/push final
→ daemon refuse relaunch : working tree is not clean
```

Le système a maintenant besoin d’une primitive unique et centralisée pour toutes les transitions runtime.

---

## Objectif

Créer un lifecycle de checkpoint runtime atomique et worktree-aware.

Toutes les transitions runtime doivent passer par la même primitive.

---

## Vision cible

Créer une abstraction centrale :

```python
checkpoint_transition(ticket_id, ...)
```

qui garantit toujours :

```text
1. resolve runtime cwd/worktree
2. git add runtime artifacts
3. commit checkpoint
4. push branche ticket
5. verify clean tree
6. fail loudly if persistence failed
```

---

## Runtime artifacts à gérer

Minimum :

```text
runs/TXXX/state.json
runs/TXXX/runtime.log
runs/TXXX/plan.md
runs/TXXX/review.md
runs/TXXX/test-report.md
runs/TXXX/implementation-output.md
runs/TXXX/*.json
```

Le système doit rester extensible.

---

## Travaux demandés

### 1. Nouveau module runtime checkpoint

Créer :

```text
tools/agent_runner/runtime_checkpoint.py
```

Fonctions proposées :

```python
resolve_ticket_cwd(ticket_id)
collect_runtime_artifacts(ticket_id)
checkpoint_transition(ticket_id, message, push=True)
verify_clean_tree(ticket_id)
```

---

### 2. Utilisation obligatoire partout

Toutes les transitions runtime doivent utiliser cette primitive :

- planner
- coder
- reviewer
- tester
- dashboard actions
- daemon transitions
- approve-plan
- request-fix
- TEST_COMPLETE
- auto-merge lifecycle

Aucun `git add/commit/push` ad-hoc ne doit rester.

---

### 3. Dirty tree safety

Le daemon doit pouvoir classifier :

```text
DIRTY_RUNTIME_CHECKPOINT
```

au lieu de juste :

```text
working tree is not clean
```

Le dashboard doit afficher explicitement :

- artifacts non persistés
- dernier commit runtime
- dernier push runtime
- fichiers dirty

---

### 4. Vérifications

Après checkpoint :

```text
git status --porcelain
```

must be empty.

Sinon :

- log erreur explicite
- état runtime FAILED ou BLOCKED_RUNTIME
- ne jamais continuer silencieusement

---

## Tests

Ajouter :

```text
tests/test_runtime_checkpoint.py
```

Cas minimum :

- checkpoint success
- push failure
- dirty tree remaining
- worktree cwd resolution
- ignored file handling (`git add -f`)
- concurrent ticket isolation

---

## Contraintes

- compatible legacy mode sans worktree
- compatible multi-worktree
- ne jamais commit sur `main`
- ne jamais masquer un push failure
- aucune transition runtime sans persistence Git validée

---

## Critères d’acceptation

- toutes les transitions runtime utilisent la même primitive
- plus aucun dirty tree après transition valide
- plus aucun commit/push oublié
- le daemon refuse proprement un runtime incohérent
- le dashboard expose clairement les erreurs de persistence runtime
- plusieurs tickets worktree peuvent tourner sans collision Git