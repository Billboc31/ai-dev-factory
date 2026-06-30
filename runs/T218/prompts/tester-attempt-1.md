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


# T218 — Add batch-based backlog ingestion and dependency analysis pipeline before Dispatcher execution

**Source**: GitHub Issue #292

## Description

# Context

The current workflow continuously polls GitHub issues and immediately runs Ticket Intelligence and Readiness.

This works for isolated tickets but is not ideal for Dispatcher-driven execution because dependencies between newly created tickets may not yet be known.

We want to introduce a batch-oriented backlog ingestion workflow.

# Goal

Create batches of newly discovered tickets.

Tickets in a batch should first receive individual Ticket Intelligence analysis.

Once the backlog has been stable for a configurable amount of time, a global dependency analysis should run on the entire batch.

Only after dependency analysis is complete should Readiness and Dispatcher scheduling occur.

# Proposed workflow

```text
Poll GitHub every X seconds
↓
New ticket discovered
↓
Run Ticket Intelligence only
↓
Store ticket in current collecting batch
↓
No new tickets received for Y minutes
↓
Freeze batch
↓
Run Global Dependency Analysis on the whole batch
↓
Update dependencies on tickets
↓
Run Readiness for all tickets in the batch
↓
Dispatcher computes queue
↓
Daemon executes tickets
```

# Global Dependency Analysis responsibilities

The Global Dependency Analysis agent is responsible for building and maintaining a dependency graph for the entire batch.

The agent must analyze all tickets in the batch together and:

- detect implicit dependencies between tickets
- detect foundation/bootstrap tickets
- detect architectural prerequisites
- detect implementation ordering constraints
- detect tickets that can safely run in parallel
- detect conflicting tickets touching the same scope
- propose or update ticket dependencies

Examples:

```text
T001 - Define architecture
T010 - Bootstrap project

→ T010 depends on T001

T011 - Backend foundation
T012 - Frontend foundation

→ T011 depends on T010
→ T012 depends on T010

T015 - Task CRUD API
T016 - Frontend task client

→ T016 depends on T015
```

The analyzer should classify relationships:

```text
HARD_DEPENDENCY
SOFT_DEPENDENCY
FOUNDATION_DEPENDENCY
PARALLEL_COMPATIBLE
CONFLICTING_SCOPE
```

Outputs produced by the analyzer:

- depends_on[]
- blocks[]
- parallel_group
- conflicting_tickets[]
- execution_phase

The analyzer must also produce a global dependency graph.

Example:

```text
T001
└── T010
    ├── T011
    └── T012
         └── T016
```

The analyzer never directly decides execution order.

```text
Dependency Analyzer
→ builds and updates the graph

Dispatcher
→ computes scheduling and execution order
```

# Additional rule

While a batch is actively being executed by the Dispatcher:

```text
new incoming tickets
→ intelligence only
→ placed into next batch
→ no dependency analysis yet
```

This prevents changing the dependency graph while execution is in progress.

# New concepts

Introduce backlog batches with statuses such as:

```text
collecting
frozen
dependency_analysis_running
readiness_running
dispatching
completed
```

# Configuration

Add configurable settings:

```text
github_poll_interval_seconds
batch_idle_timeout_minutes
max_batch_size
allow_parallel_batches
```

# Acceptance criteria

- New tickets are grouped into batches.
- Ticket Intelligence still runs continuously for newly discovered tickets.
- Global Dependency Analysis only runs once a batch becomes idle.
- Dependencies discovered by the analysis are persisted back onto tickets.
- Readiness starts only after dependency analysis completes.
- Dispatcher only schedules tickets from a finalized batch.
- Tickets arriving while a batch is executing are queued for the next batch.
- Batch lifecycle and status are visible in logs.
- Existing non-dispatcher workflows remain supported.