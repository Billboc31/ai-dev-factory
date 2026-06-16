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

## Structure obligatoire

Tout plan doit contenir au minimum **les sections suivantes** (titres
Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :

| Français (recommandé)         | English equivalent       |
|-------------------------------|--------------------------|
| `## Contexte`                 | `## Context`             |
| `## Objectif`                 | `## Objective`           |
| `## Inclus`                   | `## Included`            |
| `## Hors scope`               | `## Excluded`            |
| `## Critères d'acceptation`   | `## Acceptance criteria` |

Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.

Ces titres sont obligatoires même si une section est courte : un ticket
trivial peut produire un plan court, mais la structure doit rester stable.

Ne jamais produire uniquement un résumé.
Ne jamais produire un compte rendu d’implémentation.

## Interdictions absolues

Tu ne dois jamais écrire :
- "implémentation terminée"
- "syntaxe valide"
- "changements appliqués"
- "voici ce qui a été fait"

Tu dois produire uniquement un plan futur, pas un compte rendu passé.

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

The ticket follows.
# Generic Planner Task Read the ticket below and produce a detailed implementation plan. 

## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
## Objective
## Included
## Excluded
## Acceptance criteria
These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
markdown
## Objective
Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
naming convention. Behaviour is preserved.

## Included
- `utils.py`: rename `foo` → `bar`, update the docstring.
- `tests/test_utils.py`: update the single import and assertion.

## Excluded
- Renaming callers in other modules (tracked in a follow-up ticket).
- Any logic change inside `foo` / `bar`.

## Acceptance criteria
- `utils.py` no longer defines `foo`.
- `pytest tests/test_utils.py` passes.
- No other file references the old name.

The ticket follows.



# T190 — T190 - Fix supervisor runtime base resolution for project bootstrap

**Source**: GitHub Issue #230

## Description

# Objective

T189 is still failing because the running supervisor continues to bootstrap imported projects under an absolute container-style path:

```text
/runtime/projects/<project_id>/...
```

This is wrong for the local host runtime model.

The supervisor must resolve the runtime base explicitly and must never fall back to `/runtime/projects/...` silently.

---

# Current failure

When importing:

```text
/Users/pierrebocquet/test-ai-dev
```

Supervisor receives:

```text
POST /projects/validate-path -> 200 OK
POST /projects/bootstrap -> 500
```

and tries to create:

```text
/runtime/projects/test-ai-dev/runs
```

which fails with:

```text
OSError: [Errno 30] Read-only file system: '/runtime'
```

This proves that path validation now goes through supervisor, but runtime root resolution is still incorrect.

---

# Expected runtime model

The runtime base root is the parent folder containing one runtime per managed project.

Example:

```text
/Users/pierrebocquet/runtime/
├── ai-dev-factory/
│   ├── clones/ai-dev-factory
│   ├── worktrees/
│   ├── runs/
│   ├── state/
│   └── logs/
│
└── test-ai-dev/
    ├── clones/test-ai-dev
    ├── worktrees/
    ├── runs/
    ├── state/
    └── logs/
```

So for project id `test-ai-dev`, bootstrap must create:

```text
/Users/pierrebocquet/runtime/test-ai-dev/{clones,worktrees,runs,state,logs}
```

not:

```text
/runtime/projects/test-ai-dev/...
```

and not:

```text
/Users/pierrebocquet/runtime/ai-dev-factory/projects/test-ai-dev/...
```

---

# Required fix

## 1. Introduce explicit runtime base root resolution

Supervisor must resolve runtime base root in this order:

1. `RUNTIME_BASE_ROOT`
2. parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. safe local fallback such as `~/runtime`

It must not default to `/runtime` unless explicitly configured.

## 2. Bootstrap under runtime base root

Project runtime root must be:

```text
<RUNTIME_BASE_ROOT>/<project_id>
```

Bootstrap creates:

```text
clones/
worktrees/
runs/
state/
logs/
```

inside that root.

## 3. Fail loudly on unsafe root

If the resolved runtime base root is `/runtime` and it is not writable, return a structured 400/422 error instead of crashing with 500.

## 4. Add diagnostics

Supervisor bootstrap logs must include:

```text
runtime_base_root=<...>
project_runtime_root=<...>
project_id=<...>
project_root=<...>
```

This must make path mistakes obvious.

---

# Acceptance criteria

- Importing `/Users/pierrebocquet/test-ai-dev` does not attempt to create anything under `/runtime/projects`.
- Runtime dirs are created under `/Users/pierrebocquet/runtime/test-ai-dev/` when `RUNTIME_BASE_ROOT=/Users/pierrebocquet/runtime`.
- Supervisor returns a structured error if runtime base root is missing or not writable.
- No unhandled `OSError: Read-only file system: '/runtime'` reaches the user.
- Logs clearly show the resolved runtime base root and project runtime root.
- Existing `ai-dev-factory` runtime remains at `/Users/pierrebocquet/runtime/ai-dev-factory`.