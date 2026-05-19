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


# T116 — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

**Source**: GitHub Issue #68

## Description

# T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

## Contexte

T113/T114/T115 ont introduit :

* runtime root séparé du clone humain
* clones runtime
* worktrees runtime
* Docker Compose runtime
* API/dashboard containerisés
* daemon host-side

L’architecture fonctionne globalement mais plusieurs problèmes majeurs ont été découverts en runtime réel.

---

## Problèmes observés

### Runtime ownership ambigu

Plusieurs DB runtime concurrentes existent :

```text
.runtime/ai-dev-factory.sqlite
```

présentes :

* dans le clone humain
* dans les clones runtime
* dans les worktrees
* dans `_intake`

Cela provoque :

* board incohérent
* états divergents
* confusion runtime source-of-truth

---

### Runtime artifacts encore mélangés

Les éléments suivants continuent parfois à vivre dans les clones/worktrees :

* runs/
* logs/
* state/
* sqlite runtime
* daemon artifacts

Alors qu’ils doivent vivre uniquement dans :

```text
RUNTIME_ROOT/
```

---

### Worktrees runtime encore couplés au clone runtime

Les worktrees utilisent encore des données runtime locales.

Objectif :

* worktrees = jetables
* runtime = persistant

---

### Docker/runtime sync fragile

L’API Docker lit désormais correctement :

```text
/runtime/.runtime/ai-dev-factory.sqlite
```

mais :

* bootstrap migration absente
* hydratation runtime absente
* board fragile
* ownership non formalisé

---

## Objectif

Formaliser le runtime comme entité canonique indépendante du code source.

Le runtime devient :

```text
stateful
persistent
non-versioned
multi-instance capable
```

Le repo Git devient :

```text
product code only
```

---

# Architecture cible

## Runtime root canonique

```text
/runtime/<instance>/
```

Contient uniquement :

```text
.runtime/
runs/
logs/
state/
registry/
worktrees/
clones/
cache/
artifacts/
```

---

## Source de vérité runtime unique

UNE seule DB autorisée :

```text
/runtime/<instance>/.runtime/ai-dev-factory.sqlite
```

Interdictions :

* aucune DB dans worktree
* aucune DB dans clone
* aucune DB dans repo humain

---

## Worktrees jetables

Les worktrees :

* ne stockent aucun état persistant
* ne possèdent aucune DB
* ne possèdent aucun logs runtime
* peuvent être détruits/recréés à volonté

---

## Runtime-aware services

Tous les composants doivent résoudre leurs paths via :

```text
AI_DEV_FACTORY_RUNTIME_ROOT
```

Plus aucun fallback implicite vers :

```text
/app
repo root
cwd
```

---

## Préparation multi-runtime

Préparer le terrain pour :

```text
runtime-dev
runtime-prod
runtime-client-x
runtime-doc-platform
```

avec :

* isolation complète
* DB dédiée
* logs dédiés
* worktrees dédiés
* ports dédiés
* registry dédiée

---

## Livrables

* runtime ownership spec
* migration bootstrap runtime
* suppression DB locales worktrees/clones
* cleanup runtime artifacts
* runtime hydration au démarrage Docker
* board stable après restart
* invariant checks runtime
* documentation architecture runtime

---

## Contraintes

* aucun retour au modèle “repo = runtime”
* compatibilité daemon host-side conservée
* Docker API/dashboard doivent fonctionner
* worktrees existants ne doivent pas être cassés brutalement
* migration progressive acceptable

---

## Future work (hors scope)

* daemon containerisé
* runtime manager UI
* runtime create/start/stop
* runtime registry global
* distributed runtimes
* remote workers