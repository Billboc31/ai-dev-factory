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


# T182 — T182 - Add full multi-project workspace UI and project dashboards

**Source**: GitHub Issue #217

## Description

# Objective

Build the real multi-project workspace UI on top of the T181 backend/project-bootstrap foundation.

T181 introduces the backend runtime/project isolation and a minimal import UI.

T182 must introduce the actual project-centric UX:

- workspace sidebar
- project switcher
- per-project dashboards
- daemon/supervisor controls
- ticket/worktree visibility
- logs/runtime visibility

The goal is to move AI Dev Factory away from a single-project environment-centric UI into a true multi-project software factory workspace.

---

# Scope

## 1. Workspace shell

Add a persistent workspace shell/layout.

Required:

- left sidebar
- active project selection
- project switcher
- project quick actions
- global workspace header

Sidebar should expose:

- Projects
- Active project
- Tickets
- Worktrees
- Agents
- Logs
- Runtime
- Settings

---

# 2. Projects dashboard

Add a real project dashboard page.

Each project dashboard must display:

- project name
- detected stack
- project root
- runtime root
- daemon state
- supervisor state
- number of active tickets
- number of active worktrees
- recent activity

Add project actions:

- Start daemon
- Stop daemon
- Open logs
- Open tickets
- Open worktrees
- Re-import/rescan project

---

# 3. Per-project runtime status cards

Add runtime cards/components for:

- supervisor
- daemon
- runtime paths
- logs paths
- PID state
- active workers

The UI must clearly distinguish:

- global runtime
- project runtime
- project daemon

to avoid the confusion seen in previous deploy/runtime debugging.

---

# 4. Tickets/worktrees visibility

Add per-project views for:

- tickets
- ticket states
- branches
- worktrees
- active agent runs

The user must immediately understand:

- which tickets belong to which project
- which daemon is managing which worktree
- which worktrees are active

---

# 5. Logs visibility

Add project-level logs views.

Required:

- daemon logs
- supervisor logs
- recent runtime events
- runtime paths visibility
- quick copy/open actions

Do not require shell access for basic runtime inspection.

---

# 6. Routing and project context

Add project-aware routing.

Preferred direction:

```text
/projects/:projectId/*
```

Examples:

```text
/projects/personal-rag/dashboard
/projects/personal-rag/tickets
/projects/personal-rag/worktrees
/projects/personal-rag/logs
```

The active project context must survive navigation and refresh.

---

# Important constraints

- Do NOT reintroduce deployment complexity.
- Do NOT depend on Traefik or sandbox deploys.
- Focus on the software-factory workflow.
- The UI must remain lightweight and developer-focused.

---

# Acceptance criteria

- Workspace sidebar exists
- Multiple projects can be navigated from the UI
- Active project context is visible everywhere
- Project dashboards display runtime and daemon state
- Per-project ticket/worktree views exist
- Logs can be inspected from the UI
- Daemon start/stop works from the UI
- The user can clearly distinguish project runtimes from the global runtime
- Refresh/navigation preserves project context