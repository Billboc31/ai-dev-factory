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

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

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

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


# T114 — T114 — Separate Human Clones from Runtime Clones and Isolate Managed Project Worktrees

**Source**: GitHub Issue #63

## Description

# T114 — Separate Human Clones from Runtime Clones and Isolate Managed Project Worktrees

## Contexte

T113 a révélé plusieurs limites structurelles importantes dans l’architecture actuelle :

* conflits Git/worktree
* branche `main` verrouillée par `_intake`
* pollution runtime (`runtime.log`, SQLite live DB, caches)
* friction entre développement humain et exécution agentique
* difficulté à maintenir un working tree propre
* framework et agents partageant le même clone Git

Le problème principal identifié est :

```text
Le clone Git utilisé par le développeur humain ne doit jamais être utilisé directement par les agents runtime.
```

L’architecture actuelle mélange :

* développement humain
* runtime daemon
* worktrees agents
* projets gérés

Ce couplage provoque :

* pollution Git
* conflits worktree
* état runtime fragile
* workflows difficiles à maintenir

---

## Objectif

Introduire une séparation stricte entre :

* clones humains
* clones runtime
* worktrees runtime
* projets gérés

afin de :

* protéger les workspaces humains
* isoler les agents
* éviter les conflits Git
* permettre plusieurs versions runtime
* préparer le multi-projets
* permettre rollback runtime
* rendre le daemon jetable/recréable

---

## Architecture cible

### Clone humain

Exemple :

```text
~/dev/ai-dev-factory
~/dev/doc-platform
```

Utilisé pour :

* développement humain
* architecture
* reviews
* expérimentation
* debugging manuel

Le daemon ne doit jamais tourner ici.

---

### Runtime root unique

```text
~/runtime/ai-dev-factory/
```

Ce dossier contient tout le runtime agentique.

---

### Clones runtime

```text
~/runtime/ai-dev-factory/clones/
```

Exemples :

```text
~/runtime/ai-dev-factory/clones/ai-dev-factory
~/runtime/ai-dev-factory/clones/doc-platform
~/runtime/ai-dev-factory/clones/rag-admin
```

Les agents travaillent uniquement dans ces clones runtime.

---

### Worktrees runtime

```text
~/runtime/ai-dev-factory/worktrees/
```

Organisation :

```text
~/runtime/ai-dev-factory/worktrees/<project>/<ticket>
```

Exemples :

```text
~/runtime/ai-dev-factory/worktrees/ai-dev-factory/T114
~/runtime/ai-dev-factory/worktrees/doc-platform/T041
```

Les worktrees ne doivent jamais être créés dans les clones humains.

---

### Runtime state

```text
~/runtime/ai-dev-factory/state/
```

Contient :

* SQLite runtime DB
* registries
* daemon state
* worker state

---

### Runtime logs

```text
~/runtime/ai-dev-factory/logs/
```

Contient :

* daemon logs
* runtime logs
* execution logs

Les logs ne doivent plus être versionnés dans Git.

---

## Inclus

* définir architecture runtime officielle
* définir séparation humain/runtime
* définir runtime root unique
* définir structure clones/worktrees/state/logs
* définir isolation projets gérés
* empêcher daemon sur clone humain
* définir règles Git/worktree
* définir invariants runtime
* préparer multi-version runtime
* préparer multi-instance runtime

---

## Exclus

* orchestration distribuée
* Kubernetes
* Dockerisation complète
* CI distante
* merge automatique
* memory system
* cloud orchestration

---

## Travail attendu

Créer ou mettre à jour :

```text
docs/ai/architecture.md
docs/ai/runtime-layout.md
docs/ai/workflow-invariants.md
```

Documenter :

* clone humain
* clone runtime
* runtime root
* worktrees runtime
* managed repositories
* runtime state
* runtime logs
* règles Git/worktree

Ajouter protections :

* refuser daemon sur clone humain
* détecter runtime root invalide
* empêcher création worktree hors runtime
* empêcher pollution runtime dans clones humains

---

## Invariants à formaliser

```text
Le daemon ne doit jamais tourner dans un clone humain.
```

```text
Les worktrees agents doivent être créés uniquement sous runtime/worktrees/.
```

```text
Les projets gérés doivent être isolés du framework.
```

```text
Les fichiers runtime ne doivent jamais polluer les clones humains.
```

```text
Une branche Git ne doit être checkoutée qu’une seule fois.
```

```text
Les logs runtime ne doivent jamais être versionnés.
```

---

## Critères d’acceptation

Le ticket est terminé si :

* architecture runtime documentée
* séparation humain/runtime claire
* runtime root défini
* structure clones/worktrees définie
* isolation projets gérés définie
* runtime DB/logs hors clones humains
* invariants documentés
* daemon protégé contre mauvais clone
* worktrees runtime isolés
* conflits Git/worktree réduits
* workflow développeur simplifié