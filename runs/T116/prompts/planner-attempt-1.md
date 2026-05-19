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