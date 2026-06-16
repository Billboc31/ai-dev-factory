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

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

I have everything I need. Here is the implementation plan:

---

## Objective

Fix the supervisor's project bootstrap so it derives the runtime base root from its own environment variables (`RUNTIME_BASE_ROOT` → parent of `AI_DEV_FACTORY_RUNTIME_ROOT` → `~/runtime`) instead of trusting the `runtime_root` field sent by the Control API, which carries a container-side path (`/runtime`) that does not exist on the host. The directory layout changes from `{runtime_root}/projects/{project_id}/…` to `{RUNTIME_BASE_ROOT}/{project_id}/…`, `clones/` is added to the bootstrapped directories, and the supervisor fails loudly with a 422 if the resolved root is not writable.

## Included

**`services/supervisor/main.py`**
- Add `_runtime_base_root() -> Path` that resolves in order:
  1. `Path(os.environ["RUNTIME_BASE_ROOT"]).expanduser().resolve()` if set
  2. `Path(os.environ["AI_DEV_FACTORY_RUNTIME_ROOT"]).expanduser().resolve().parent` if set
  3. `Path.home() / "runtime"` as the safe local fallback
- Rewrite `bootstrap_project_host` (line 1510):
  - Call `_runtime_base_root()` — do **not** use `body.runtime_root` for path computation.
  - Compute `project_runtime_root = runtime_base_root / body.project_id`.
  - Before creating directories, check if `runtime_base_root` is writable (`os.access(runtime_base_root, os.W_OK)` or a try/except on `mkdir`); if not, return a structured 422 `{"error": "runtime_base_root_not_writable", "detail": str(runtime_base_root)}` instead of crashing.
  - Create subdirs: `clones/`, `worktrees/`, `runs/`, `state/`, `logs/` (adding `clones/` to the existing four).
  - Update `logger.info` call to log `runtime_base_root=`, `project_runtime_root=`, `project_id=`, `project_root=`.
  - Update the return dict: `runtime_root` field returns `str(project_runtime_root)`.

**`services/control_api/services/project_id.py`**
- Rewrite `assert_contained(runtime_base, project_id)` (line 52): remove the hardcoded `/projects/` path segment. The containment check and returned path become `{runtime_base}/{project_id}` staying inside `{runtime_base}/` (i.e., `base_resolved = runtime_base.resolve()`, `candidate = (base_resolved / project_id).resolve()`).

**`services/control_api/services/runtime_resolver.py`**
- In `resolve_runs_dir`, `resolve_worktrees_dir`, `resolve_state_dir`, `resolve_logs_dir`: when `project_id` is given, replace `Path(runtime_root) / "projects" / project_id / <subdir>` with `Path(runtime_root) / project_id / <subdir>` (lines 21, 35, 48, 62).
- `resolve_project_runtime_root` (line 69) inherits the fix via the updated `assert_contained`.

**`tests/test_project_id.py`**
- `test_assert_contained_returns_correct_path` (line 123): update expected path from `tmp_path / "projects" / "my-project"` to `tmp_path / "my-project"`.
- `test_assert_contained_different_ids_produce_different_paths` (line 138): update `startswith` checks from `str(tmp_path / "projects")` to `str(tmp_path)`.

**`tests/test_project_bootstrap.py`**
- `_mock_bootstrap_response` (line 24): change `base = f"{runtime_root}/projects/{project_id}"` to `base = f"{runtime_root}/{project_id}"`.
- `test_bootstrap_returns_paths_from_supervisor` (line 59) and `test_bootstrap_runtime_dirs_are_under_project_runtime_root` (line 66): update `expected_base` / `expected_prefix` from `runtime_root / "projects" / "my-project"` to `runtime_root / "my-project"`.

## Excluded

- Removing the `runtime_root` field from `ProjectBootstrapHostRequest` (kept for API compatibility; the field is accepted but no longer used for path computation).
- Changes to `services/supervisor/path_mapper.py` (path-mapping layer is a separate concern).
- Creating the actual git clone inside `clones/` (only the empty directory is created).
- Updating `deploy/.env` or any deployment-level env documentation for `RUNTIME_BASE_ROOT`.
- Changing Control API logic that decides what value to pass as `runtime_root` in the request body.

## Acceptance criteria

- With `RUNTIME_BASE_ROOT=/Users/pierrebocquet/runtime`, importing `/Users/pierrebocquet/test-ai-dev` causes the supervisor to create `/Users/pierrebocquet/runtime/test-ai-dev/{clones,worktrees,runs,state,logs}` — no path under `/runtime/projects/` is attempted.
- Without `RUNTIME_BASE_ROOT` set but with `AI_DEV_FACTORY_RUNTIME_ROOT=/Users/pierrebocquet/runtime/ai-dev-factory`, `_runtime_base_root()` resolves to `/Users/pierrebocquet/runtime`.
- Supervisor returns `{"error": "runtime_base_root_not_writable", "detail": "/runtime"}` (HTTP 422) when the resolved base root is not writable, instead of an unhandled `OSError`.
- Supervisor bootstrap log line includes `runtime_base_root=`, `project_runtime_root=`, `project_id=`, `project_root=`.
- `pytest tests/test_project_id.py` passes with the updated assertions.
- `pytest tests/test_project_bootstrap.py` passes with the updated mock response and path assertions.
- The existing `ai-dev-factory` runtime at `/Users/pierrebocquet/runtime/ai-dev-factory` is not touched by any code path introduced in this ticket.

---

## Review

# Plan review — fix required

The current T190 plan fixes the immediate `/runtime/projects/...` failure, but it is incomplete as a durable architecture fix.

## Required fixes before implementation

### 1. Persist `project_runtime_root` as the source of truth

The supervisor may compute the initial project runtime root during bootstrap, but after that the value must be persisted and reused.

After bootstrap, routes must not recompute the project runtime root from:

- `project_id`
- `RUNTIME_BASE_ROOT`
- `AI_DEV_FACTORY_RUNTIME_ROOT`
- `runtime_root`
- `/projects/<project_id>` conventions

Required flow:

1. Supervisor resolves `runtime_base_root`.
2. Supervisor computes `project_runtime_root = runtime_base_root / project_id`.
3. Supervisor creates `project_runtime_root/{clones,worktrees,runs,state,logs}`.
4. Supervisor returns `project_runtime_root` in the bootstrap response.
5. Control API persists `project_runtime_root` in the project registry.
6. All daemon/worktree/log/ticket operations use the persisted `project_runtime_root`.

Acceptance additions:

- `project_runtime_root` is persisted per project.
- API restart does not change the project runtime root.
- Runtime path helpers use persisted `project_runtime_root` when available.

### 2. Make runtime base resolution explicit and observable

The supervisor must not silently fall back to `/runtime`.

Resolution order:

1. `RUNTIME_BASE_ROOT`
2. parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `Path.home() / "runtime"`

Supervisor bootstrap must log before directory creation:

```text
runtime_base_root=<...>
project_runtime_root=<...>
project_id=<...>
project_root=<...>
```

If the resolved runtime base root is not writable, return a structured HTTP error instead of crashing.

Example:

```json
{
  "error": "runtime_base_root_not_writable",
  "detail": "/runtime"
}
```

## Review verdict

PLAN_FIX_REQUIRED

The plan can be approved once it explicitly persists `project_runtime_root` and treats it as the durable runtime location for every project operation.

---

## Instructions de fix

# T190 plan fix — runtime base resolution contract

The T190 plan must make the runtime base resolution explicit and observable.

The current failure happened because the supervisor silently used a container-style absolute path:

```text
/runtime/projects/<project_id>
```

That must never happen silently again.

## Required runtime model

There are two distinct concepts:

```text
AI_DEV_FACTORY_RUNTIME_ROOT
```

Runtime root of the AI Dev Factory project itself.

Example:

```text
/Users/pierrebocquet/runtime/ai-dev-factory
```

and:

```text
RUNTIME_BASE_ROOT
```

Parent directory containing one runtime root per managed project.

Example:

```text
/Users/pierrebocquet/runtime
```

For an imported project `test-ai-dev`, the project runtime root is:

```text
/Users/pierrebocquet/runtime/test-ai-dev
```

not:

```text
/runtime/projects/test-ai-dev
```

and not:

```text
/Users/pierrebocquet/runtime/ai-dev-factory/projects/test-ai-dev
```

## Required resolution order

Supervisor resolves `runtime_base_root` in this order:

1. `RUNTIME_BASE_ROOT` if explicitly set.
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT` if set.
3. `Path.home() / "runtime"` as local fallback.

It must not default to `/runtime` unless explicitly configured.

## Required diagnostics

On every project bootstrap, supervisor must log:

```text
runtime_base_root=<...>
project_runtime_root=<...>
project_id=<...>
project_root=<...>
```

This log must appear before directory creation.

## Required error handling

If the resolved runtime base root is not writable, supervisor must return a structured HTTP error instead of crashing.

Example payload:

```json
{
  "error": "runtime_base_root_not_writable",
  "detail": "/runtime"
}
```

## Acceptance criteria

- No code path creates `/runtime/projects/...` unless `/runtime` was explicitly configured as `RUNTIME_BASE_ROOT` and is writable.
- Bootstrap with `RUNTIME_BASE_ROOT=/Users/pierrebocquet/runtime` creates `/Users/pierrebocquet/runtime/<project_id>/...`.
- Bootstrap without `RUNTIME_BASE_ROOT` but with `AI_DEV_FACTORY_RUNTIME_ROOT=/Users/pierrebocquet/runtime/ai-dev-factory` resolves base root to `/Users/pierrebocquet/runtime`.
- Bootstrap logs the resolved paths before `mkdir`.
- Read-only filesystem errors are converted to structured supervisor errors.