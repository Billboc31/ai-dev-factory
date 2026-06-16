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

T190 implementation is complete. Summary:

**What was done:** Fixed the supervisor `bootstrap_project_host()` to use `RUNTIME_BASE_ROOT` env var (falling back to parent of `AI_DEV_FACTORY_RUNTIME_ROOT` → `~/runtime`) instead of the hardcoded `/runtime/projects/` path that caused `Read-only file system` errors on macOS/Linux hosts.

**Test results:** 81 T190-specific tests pass, 28 additional tests for modified route/resolver files pass. 72 pre-existing failures are unrelated to T190 — confirmed by `git diff main --name-only` showing none of those test files were modified.

**State:** `PLAN_APPROVED` → `TEST_COMPLETE` — committed in `77d215b5`.

---

## Review

I have a complete picture of the implementation. Here is the formal review.

---

## Review — T190: Fix supervisor runtime base resolution for project bootstrap

### Summary

The implementation correctly resolves the core failure: the supervisor no longer attempts to create directories under `/runtime/projects/<id>/...`. All five acceptance criteria are substantively met. The architecture is clean, well-scoped, and the new code paths are properly covered by tests.

---

### 1. Correctness relative to ticket requirements

**AC1 — No `/runtime/projects/` paths during bootstrap** ✓

`_runtime_base_root()` (`supervisor/main.py:71`) replaces the old hardcoded path. Bootstrap now creates `{runtime_base_root}/{project_id}/{dirs}` with no `/projects/` segment. `test_bootstrap_runtime_dirs_under_runtime_base_root` verifies this explicitly.

**AC2 — Runtime dirs under `RUNTIME_BASE_ROOT/<project_id>`** ✓

Resolution order is correctly implemented:
1. `RUNTIME_BASE_ROOT` env var
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `~/runtime` (safe local fallback — never `/runtime`)

`test_bootstrap_uses_parent_of_factory_runtime_root_when_no_base` covers the second path.

**AC3 — Structured error for missing/unwritable root (supervisor)** ✓

The pre-flight check at `main.py:1573` uses `os.access()` before mkdir and returns 422 `runtime_base_root_not_writable`. The `OSError` catch at line 1597 provides a second-layer return of 422. `test_bootstrap_not_writable_runtime_base_returns_422` validates this.

**AC4 — No unhandled OSError reaching the user** — Partially met with a residual gap (see below).

**AC5 — Diagnostic logs** ✓

The `logger.info` at `main.py:1562` logs all four required fields: `project_id`, `project_root`, `runtime_base_root`, `project_runtime_root`.

**AC6 — Existing ai-dev-factory runtime unaffected** ✓

`_runtime_base_root()` resolves to the parent of the existing `AI_DEV_FACTORY_RUNTIME_ROOT`, so the existing `/Users/pierrebocquet/runtime/ai-dev-factory` is untouched.

---

### 2. Issue: `runtime_base_root_not_writable` propagated as 500 through control_api

**Location:** `services/control_api/services/project_bootstrap.py:79-90`

When the supervisor returns `{"error": "runtime_base_root_not_writable"}`, the control_api `bootstrap()` function falls through to:

```python
raise RuntimeError(f"bootstrap failed: {detail}")
```

This is not caught by the `ValueError` handler in `routes/projects.py:166`, so it hits the generic `Exception` handler at line 168 and returns **500** to the end user, with the OSError detail string embedded in the body.

The supervisor itself returns 422 correctly (AC3 is met). But a user calling the control_api `/projects/import` endpoint for a misconfigured runtime root still receives a 500, which does not fully satisfy the "no unhandled error reaches the user" intent.

**Fix:** Add a mapping in `project_bootstrap.py`:

```python
if error_code == "runtime_base_root_not_writable":
    raise ValueError(f"runtime base root is not writable: {detail}")
```

This is a one-line fix. The corresponding test would call the control_api import endpoint (not the supervisor directly) with an unwritable runtime base and assert 422.

---

### 3. Pre-existing observation (not introduced by T190)

`resolve_state_dir` (`runtime_resolver.py:71`) has a last-resort fallback `return project_root / "runs"` — clearly a copy-paste from `resolve_runs_dir`. This was present before this ticket and is not a T190 regression. With `project_runtime_root` now being persisted and passed from bootstrap, this fallback is rarely reachable in practice.

---

### 4. Scope and quality

- Changes are well-bounded: supervisor path logic, project registry persistence, resolver functions, and routes. No unintended scope drift.
- `validate_project_id` + `assert_contained` provide path-traversal safety before any filesystem operation.
- The persisted `project_runtime_root` in `workspace.json` correctly decouples runtime paths from env var changes after first import.
- Test coverage is solid: 29 supervisor tests, registry persistence tests, and bootstrap service tests all target the new behaviors.

---

### Verdict

The core fix is correct, the architecture is clean, and all acceptance criteria are met at the supervisor level. The single actionable gap — the control_api propagating `runtime_base_root_not_writable` as 500 instead of 422 — does not change the fundamental correctness of the supervisor fix, but it leaves end users with an opaque error in the misconfigured-root case. The fix is trivial (one extra `if` branch in `project_bootstrap.py`).

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T190/reviews/implementation-review.md
- generated at: 2026-06-16T12:51:30Z

---

I have a complete picture of the implementation. Here is the formal review.

---

## Review — T190: Fix supervisor runtime base resolution for project bootstrap

### Summary

The implementation correctly resolves the core failure: the supervisor no longer attempts to create directories under `/runtime/projects/<id>/...`. All five acceptance criteria are substantively met. The architecture is clean, well-scoped, and the new code paths are properly covered by tests.

---

### 1. Correctness relative to ticket requirements

**AC1 — No `/runtime/projects/` paths during bootstrap** ✓

`_runtime_base_root()` (`supervisor/main.py:71`) replaces the old hardcoded path. Bootstrap now creates `{runtime_base_root}/{project_id}/{dirs}` with no `/projects/` segment. `test_bootstrap_runtime_dirs_under_runtime_base_root` verifies this explicitly.

**AC2 — Runtime dirs under `RUNTIME_BASE_ROOT/<project_id>`** ✓

Resolution order is correctly implemented:
1. `RUNTIME_BASE_ROOT` env var
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `~/runtime` (safe local fallback — never `/runtime`)

`test_bootstrap_uses_parent_of_factory_runtime_root_when_no_base` covers the second path.

**AC3 — Structured error for missing/unwritable root (supervisor)** ✓

The pre-flight check at `main.py:1573` uses `os.access()` before mkdir and returns 422 `runtime_base_root_not_writable`. The `OSError` catch at line 1597 provides a second-layer return of 422. `test_bootstrap_not_writable_runtime_base_returns_422` validates this.

**AC4 — No unhandled OSError reaching the user** — Partially met with a residual gap (see below).

**AC5 — Diagnostic logs** ✓

The `logger.info` at `main.py:1562` logs all four required fields: `project_id`, `project_root`, `runtime_base_root`, `project_runtime_root`.

**AC6 — Existing ai-dev-factory runtime unaffected** ✓

`_runtime_base_root()` resolves to the parent of the existing `AI_DEV_FACTORY_RUNTIME_ROOT`, so the existing `/Users/pierrebocquet/runtime/ai-dev-factory` is untouched.

---

### 2. Issue: `runtime_base_root_not_writable` propagated as 500 through control_api

**Location:** `services/control_api/services/project_bootstrap.py:79-90`

When the supervisor returns `{"error": "runtime_base_root_not_writable"}`, the control_api `bootstrap()` function falls through to:

```python
raise RuntimeError(f"bootstrap failed: {detail}")
```

This is not caught by the `ValueError` handler in `routes/projects.py:166`, so it hits the generic `Exception` handler at line 168 and returns **500** to the end user, with the OSError detail string embedded in the body.

The supervisor itself returns 422 correctly (AC3 is met). But a user calling the control_api `/projects/import` endpoint for a misconfigured runtime root still receives a 500, which does not fully satisfy the "no unhandled error reaches the user" intent.

**Fix:** Add a mapping in `project_bootstrap.py`:

```python
if error_code == "runtime_base_root_not_writable":
    raise ValueError(f"runtime base root is not writable: {detail}")
```

This is a one-line fix. The corresponding test would call the control_api import endpoint (not the supervisor directly) with an unwritable runtime base and assert 422.

---

### 3. Pre-existing observation (not introduced by T190)

`resolve_state_dir` (`runtime_resolver.py:71`) has a last-resort fallback `return project_root / "runs"` — clearly a copy-paste from `resolve_runs_dir`. This was present before this ticket and is not a T190 regression. With `project_runtime_root` now being persisted and passed from bootstrap, this fallback is rarely reachable in practice.

---

### 4. Scope and quality

- Changes are well-bounded: supervisor path logic, project registry persistence, resolver functions, and routes. No unintended scope drift.
- `validate_project_id` + `assert_contained` provide path-traversal safety before any filesystem operation.
- The persisted `project_runtime_root` in `workspace.json` correctly decouples runtime paths from env var changes after first import.
- Test coverage is solid: 29 supervisor tests, registry persistence tests, and bootstrap service tests all target the new behaviors.

---

### Verdict

The core fix is correct, the architecture is clean, and all acceptance criteria are met at the supervisor level. The single actionable gap — the control_api propagating `runtime_base_root_not_writable` as 500 instead of 422 — does not change the fundamental correctness of the supervisor fix, but it leaves end users with an opaque error in the misconfigured-root case. The fix is trivial (one extra `if` branch in `project_bootstrap.py`).

IMPLEMENTATION_FIX_REQUIRED