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



# T176 — T176 - Redeploy must rehydrate missing sandbox source clone and support advanced runtime path override

**Source**: GitHub Issue #204

## Description

# T176 - Redeploy must rehydrate missing sandbox source clone and support advanced runtime path override

## Problem

Environment redeploy currently fails when the sandbox source clone is missing or incomplete.

Observed failure:

```text
runtime mismatch: scripts directory not found at
/Users/.../sandboxes/.../source/.ai-dev-factory/scripts
— sandbox source clone missing or not initialized
```

This means redeploy assumes the `source/` clone already exists and is fully initialized.

However:

- stopped environments may lose their source clone
- partial/incomplete bootstrap can leave a broken source state
- runtime cleanup may remove source data
- redeploy should be resilient and self-healing

---

## Root cause

Current redeploy flow:

```text
resolve scripts path
→ expect source/.ai-dev-factory/scripts to exist
→ fail hard if missing
```

Expected behavior:

```text
redeploy
→ verify source clone exists
→ if missing/incomplete:
   - recreate sandbox source clone
   - checkout correct branch/ref
   - restore scripts
→ continue bootstrap
```

---

## Goal

Make redeploy self-healing and resilient.

If the sandbox source clone is missing or invalid:

- automatically recreate it
- restore the correct branch/ref
- continue deployment

Additionally:

- expose advanced runtime path override options in the environment creation UI
- while keeping auto-configuration as the default

---

## Required backend behavior

### Redeploy validation

Before resolving script paths:

validate:

- `sandbox_dir/source` exists
- `.git` exists
- `.ai-dev-factory/scripts` exists
- branch/ref is available

If invalid:

- log explicit diagnostics
- recreate source clone automatically
- checkout requested branch/ref
- continue deployment

---

## Required logging

On redeploy:

```text
source clone missing or invalid
rehydrating sandbox source clone
repo=<repo>
branch=<branch>
source_path=<path>
```

After restore:

```text
sandbox source clone restored successfully
```

---

## UI changes

Keep runtime path auto-configuration by default.

Add an optional advanced section:

```text
[ Advanced runtime options ]
```

Allow overriding:

- sandbox root
- runtime root
- source path

Also allow:

- force source clone refresh
- reset/reclone source

---

## Important constraints

Default/simple flow must remain automatic.

Advanced runtime controls:

- hidden by default
- intended for debugging/recovery
- must validate path ownership and consistency

---

## Acceptance criteria

- Redeploy no longer fails when `source/.ai-dev-factory/scripts` is missing
- Missing source clone is automatically recreated
- Correct branch/ref is restored automatically
- Logs clearly indicate clone rehydration
- Advanced runtime options are available but collapsed by default
- Users can force source refresh/reclone
- Runtime validation still prevents cross-runtime path mismatches

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

The corrected plan is written to `runs/T176/plan.md`. Here is a summary of what changed and why:

**Root cause of the rejection:** The previous plan accepted `runtime_root` in the API request but explicitly excluded wiring it to any backend behavior — making the UI field a no-op that misleads users.

**Key changes in the fix:**

1. **`SandboxState`** now gains three fields: `runtime_root` (user input), `effective_runtime_root` (resolved at deploy time), and `force_source_refresh`.

2. **`_resolve_runtime_root()`** added to `sandbox_runtime_deploy.py` — selects between the user override and auto-detected default, validates path safety (absolute, no `..`, within allowed roots, sandbox_dir descends from it), and returns `(path, "auto"|"override")`.

3. **`deploy_operational_runtime()`** calls `_resolve_runtime_root` early, logs `runtime_root=… runtime_root_source=…`, derives `sandbox_dir` from the effective root when the user supplied one, and persists `effective_runtime_root` back to state.

4. **API boundary validation** rejects non-absolute or path-traversal `runtime_root` values with a `400` before they reach the service layer.

5. **UI live preview** updates the displayed sandbox destination as the user types in the `runtime_root` field.

The source-clone rehydration logic (`_is_source_clone_valid`, `_rehydrate_source_clone`) is unchanged from the prior attempt.

---

## Review

# T176 — Plan Review

## Verdict

The plan correctly addresses the redeploy failure: redeploy must not assume that `sandbox_dir/source` is still present and valid. It should detect a missing or incomplete source clone, rehydrate it, and only then resolve `.ai-dev-factory/scripts`.

This is the right backend fix for the observed error:

```text
runtime mismatch: scripts directory not found at <sandbox>/source/.ai-dev-factory/scripts
```

## What is good

- Adds explicit source clone validation before script resolution.
- Adds automatic rehydration when `source/`, `.git`, or `.ai-dev-factory/scripts` is missing.
- Adds a `force_source_refresh` option.
- Keeps the default create flow automatic.
- Adds UI affordance for advanced runtime options.

## Main issue

The plan currently adds `runtime_root` to the UI/API request but explicitly excludes backend wiring of the runtime root override.

That means the UI may appear to let the user choose a runtime root, while the backend still ignores it. This would create a misleading UX and repeat the same confusion this ticket is trying to remove.

## Required correction

Do not ship a non-functional `runtime_root` override.

Either:

1. fully wire `runtime_root` end-to-end in this ticket; or
2. remove/disable the `runtime_root` input from this ticket and only keep `force_source_refresh`.

The preferred option is to wire it properly because the original issue asks for choosing the path from the UI when needed.

## Final recommendation

Approve the plan only after adding backend handling for `runtime_root` override, including validation and persistence.

---

## Instructions de fix

# Plan Fix — Runtime Root Override Must Be Fully Wired

## Problem

The current T176 plan introduces a `runtime_root` field in the UI/API but explicitly excludes backend wiring for the override.

This creates a misleading UX where users can appear to choose a runtime root while the backend silently ignores it.

## Required fix

The plan must fully wire `runtime_root` override support end-to-end.

## Required backend additions

### Runtime root resolution

Add a central runtime root resolver:

```text
_resolve_runtime_root(...)
```

Behavior:

- use explicit override when provided;
- otherwise use auto-detected runtime root;
- validate ownership and consistency.

### Validation

Validate that:

- sandbox_dir belongs to runtime_root;
- source_path belongs to sandbox_dir;
- runtime_root exists or can be created safely;
- runtime_root cannot escape allowed sandbox/runtime roots.

### Persistence

Persist the effective runtime root in `SandboxState`.

### Logging

Before deploy:

```text
runtime_root=<effective runtime root>
runtime_root_source=<auto|override>
```

### UI behavior

When advanced runtime options are enabled:

- runtime_root override updates sandbox destination preview live.

## Acceptance criteria additions

- runtime_root override actually changes deploy target
- invalid runtime_root values fail validation explicitly
- logs clearly indicate runtime root source
- sandbox paths derive from effective runtime root
- UI preview updates when runtime_root changes