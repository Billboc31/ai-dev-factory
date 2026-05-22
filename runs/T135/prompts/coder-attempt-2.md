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


# T135 — T135 — Isolated analysis and deploy worktrees

**Source**: GitHub Issue #108

## Description

Add isolated worktree and runtime environments for AI analysis, deploy generation and deploy validation workflows.

Scope:
- create dedicated analysis/deploy worktrees per ticket or job
- map Docker container paths to host worktree paths correctly
- isolated runtime roots
- isolated compose project names
- isolated env files and ports
- cleanup of completed/failed worktrees
- dashboard visibility for sandbox/worktree state
- tests for worktree isolation and host path mapping

Out of scope:
- deploy/test/fix retry loop
- tester agent
- production deployment
- remote/cloud deployment

Acceptance:
- analysis jobs never run against the main runtime worktree
- supervisor always receives valid host paths
- generated files are committed from isolated worktrees
- sandbox deploys cannot impact the main runtime
- cleanup works correctly
- existing daemon/runtime workflows continue to work

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation complete. Here's the summary:

## Files created/modified

**New files:**
- `services/supervisor/path_mapper.py` — `ContainerToHostMapper` class reading `CONTAINER_RUNTIME_ROOT` / `HOST_RUNTIME_ROOT` env vars
- `tests/test_host_path_mapping.py` — 4 unit tests for the mapper
- `tests/test_analysis_worktree_isolation.py` — 5 tests verifying worktree creation, file isolation, cleanup on success/failure, and state JSON

**Modified files:**
- `services/supervisor/main.py` — imports and instantiates mapper at module load; applies `mapper.map()` to `project_root` in `POST /analysis/start`; logs original→mapped path; forwards `--worktrees-dir` to subprocess; adds `GET /supervisor/status`
- `tools/agent_runner/run_analysis.py` — adds `--worktrees-dir` arg; on startup creates isolated worktree via `create_ticket_branch_and_worktree`; redirects all file writes and `commit_and_push` to `write_root` (worktree when provided, else `project_root` for backwards compat); cleans up worktree in `finally`; includes `worktree_path` in all state writes
- `services/control_api/models/schemas.py` — added `worktree_path: str | None = None` to `AnalysisStatus`
- `apps/dashboard/src/pages/DeployerPage.jsx` — `AnalysisStatusPanel` displays `Worktree: {path}` when non-null

The backwards-compatibility design: when `--worktrees-dir` is absent (existing tests), `write_root = project_root` and no worktree is created — all 9 pre-existing `test_run_analysis.py` tests pass unchanged.

---

## Review

The ambiguity is confirmed. Now I'll write the structured review.

---

# PR Review — T135: Isolated analysis and deploy worktrees

## Résumé

The implementation delivers the V1 scope correctly: isolated analysis worktrees, Docker-to-host path mapping in the supervisor, worktree cleanup, state visibility through the dashboard, and test coverage for the two new features. Backwards compatibility is preserved via the optional `--worktrees-dir` argument. One correctness bug in the path mapper requires a fix before approval.

---

## Vérifications effectuées

- `services/supervisor/path_mapper.py` — new file, full read
- `services/supervisor/main.py` — diff reviewed (mapper import, `/analysis/start`, `/supervisor/status`, `--worktrees-dir` forwarding)
- `tools/agent_runner/run_analysis.py` — diff reviewed (new arg, worktree lifecycle, `write_root` redirection, path escape check, `finally` cleanup)
- `tools/agent_runner/worktree_manager.py` — full read (pre-existing, reused unchanged)
- `services/control_api/models/schemas.py` — `AnalysisStatus.worktree_path` addition
- `apps/dashboard/src/pages/DeployerPage.jsx` — `AnalysisStatusPanel` addition
- `tests/test_host_path_mapping.py` — 4 unit tests
- `tests/test_analysis_worktree_isolation.py` — 5 integration tests
- `runs/T135/plan.md` — plan vs implementation cross-check
- Git diff `main...HEAD` to confirm scope bounds

---

## Points validés

- **Path mapping**: `ContainerToHostMapper` is instantiated at module load, applied in `/analysis/start` before subprocess launch, and exposed in `/supervisor/status`. Matches plan §2.
- **Analysis worktree isolation**: `run_analysis.py` creates a timestamped `analysis/{job_id}` worktree, redirects all file writes and `commit_and_push` to `write_root`, and removes the worktree in `finally` on both success and failure paths. Matches plan §3–4.
- **Path escape hardening** (`run_analysis.py:219`): LLM-generated paths are validated against `write_root` before write — correct security measure.
- **Backwards compatibility**: `--worktrees-dir` is optional; when absent, `write_root = project_root` and no worktree is created. Existing tests remain unaffected.
- **Schema**: `AnalysisStatus.worktree_path: str | None = None` is a non-breaking additive change.
- **Dashboard**: `AnalysisStatusPanel` renders worktree path and hides when `null`. Matches plan §5.
- **Test coverage**: `test_host_path_mapping.py` covers all four mapper cases; `test_analysis_worktree_isolation.py` covers worktree creation, file isolation, success cleanup, failure cleanup, and state JSON. Matches plan §6.
- **Scope compliance**: `run_scripts.py` isolation, compose project names, dynamic ports, cleanup endpoints, retry loop, and production deployment are all absent — matching the explicit V1 exclusions.

---

## Problèmes détectés

### [BLOCKING] Path prefix ambiguity in `ContainerToHostMapper.map()` — `path_mapper.py:18`

```python
if path.startswith(self.container_root):
```

Raw string `.startswith()` does not respect path separator boundaries. If `CONTAINER_RUNTIME_ROOT=/app`, the path `/applications/foo` matches and is incorrectly translated to `{HOST_RUNTIME_ROOT}lications/foo`. This violates the acceptance criterion "supervisor always receives valid host paths".

Verified:
```
'/applications/foo'.startswith('/app') = True   # incorrectly matches
```

**Fix required** — replace with:
```python
if path == self.container_root or path.startswith(self.container_root + "/"):
```

The existing test `test_unrelated_path_not_mutated` passes only because `/other/path` does not share a prefix with `/app`; there is no test for the ambiguous case.

---

## Risques éventuels (non bloquants)

1. **Scripts path not mapped** (`main.py:639-645`): `scripts_start` passes `body.project_root` to the subprocess without `mapper.map()`. This is explicitly excluded from V1 scope, but it means scripts jobs launched from a container context will receive container-internal paths. Should be addressed in V2 or documented.

2. **Local analysis branches accumulate**: `remove_ticket_worktree` removes the worktree directory but not the local git branch (`analysis/{job_id}`). After many analysis runs, local branches pile up. The `cleanup_failed_intake` helper (pre-existing) handles both; the analysis path could use a similar approach, or a periodic cleanup routine.

3. **No `fetch_origin_main` before branch creation**: `create_ticket_branch_and_worktree` branches from `origin/main` without fetching first. This is pre-existing behavior, not introduced here. For analysis jobs this is low risk (the branch is only used for file writes, not for running the analysed project), but worth noting for future iterations.

4. **Unusual test lambda** (`test_analysis_worktree_isolation.py:104`): `(_ for _ in ()).throw(RuntimeError("LLM failed"))` is functionally correct but non-obvious. A plain `def` raising helper would be clearer.

---

## Décision

- REQUEST_CHANGES — one blocking fix required before approval

## Actions demandées

1. **[Required]** Fix `path_mapper.py:18` — change `path.startswith(self.container_root)` to `path == self.container_root or path.startswith(self.container_root + "/")`. Add a test case for the ambiguous-prefix scenario (e.g., `CONTAINER_RUNTIME_ROOT=/app`, path=`/applications/foo` → identity, not mapped).

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T135/reviews/implementation-review.md
- generated at: 2026-05-22T06:58:56Z

---

The ambiguity is confirmed. Now I'll write the structured review.

---

# PR Review — T135: Isolated analysis and deploy worktrees

## Résumé

The implementation delivers the V1 scope correctly: isolated analysis worktrees, Docker-to-host path mapping in the supervisor, worktree cleanup, state visibility through the dashboard, and test coverage for the two new features. Backwards compatibility is preserved via the optional `--worktrees-dir` argument. One correctness bug in the path mapper requires a fix before approval.

---

## Vérifications effectuées

- `services/supervisor/path_mapper.py` — new file, full read
- `services/supervisor/main.py` — diff reviewed (mapper import, `/analysis/start`, `/supervisor/status`, `--worktrees-dir` forwarding)
- `tools/agent_runner/run_analysis.py` — diff reviewed (new arg, worktree lifecycle, `write_root` redirection, path escape check, `finally` cleanup)
- `tools/agent_runner/worktree_manager.py` — full read (pre-existing, reused unchanged)
- `services/control_api/models/schemas.py` — `AnalysisStatus.worktree_path` addition
- `apps/dashboard/src/pages/DeployerPage.jsx` — `AnalysisStatusPanel` addition
- `tests/test_host_path_mapping.py` — 4 unit tests
- `tests/test_analysis_worktree_isolation.py` — 5 integration tests
- `runs/T135/plan.md` — plan vs implementation cross-check
- Git diff `main...HEAD` to confirm scope bounds

---

## Points validés

- **Path mapping**: `ContainerToHostMapper` is instantiated at module load, applied in `/analysis/start` before subprocess launch, and exposed in `/supervisor/status`. Matches plan §2.
- **Analysis worktree isolation**: `run_analysis.py` creates a timestamped `analysis/{job_id}` worktree, redirects all file writes and `commit_and_push` to `write_root`, and removes the worktree in `finally` on both success and failure paths. Matches plan §3–4.
- **Path escape hardening** (`run_analysis.py:219`): LLM-generated paths are validated against `write_root` before write — correct security measure.
- **Backwards compatibility**: `--worktrees-dir` is optional; when absent, `write_root = project_root` and no worktree is created. Existing tests remain unaffected.
- **Schema**: `AnalysisStatus.worktree_path: str | None = None` is a non-breaking additive change.
- **Dashboard**: `AnalysisStatusPanel` renders worktree path and hides when `null`. Matches plan §5.
- **Test coverage**: `test_host_path_mapping.py` covers all four mapper cases; `test_analysis_worktree_isolation.py` covers worktree creation, file isolation, success cleanup, failure cleanup, and state JSON. Matches plan §6.
- **Scope compliance**: `run_scripts.py` isolation, compose project names, dynamic ports, cleanup endpoints, retry loop, and production deployment are all absent — matching the explicit V1 exclusions.

---

## Problèmes détectés

### [BLOCKING] Path prefix ambiguity in `ContainerToHostMapper.map()` — `path_mapper.py:18`

```python
if path.startswith(self.container_root):
```

Raw string `.startswith()` does not respect path separator boundaries. If `CONTAINER_RUNTIME_ROOT=/app`, the path `/applications/foo` matches and is incorrectly translated to `{HOST_RUNTIME_ROOT}lications/foo`. This violates the acceptance criterion "supervisor always receives valid host paths".

Verified:
```
'/applications/foo'.startswith('/app') = True   # incorrectly matches
```

**Fix required** — replace with:
```python
if path == self.container_root or path.startswith(self.container_root + "/"):
```

The existing test `test_unrelated_path_not_mutated` passes only because `/other/path` does not share a prefix with `/app`; there is no test for the ambiguous case.

---

## Risques éventuels (non bloquants)

1. **Scripts path not mapped** (`main.py:639-645`): `scripts_start` passes `body.project_root` to the subprocess without `mapper.map()`. This is explicitly excluded from V1 scope, but it means scripts jobs launched from a container context will receive container-internal paths. Should be addressed in V2 or documented.

2. **Local analysis branches accumulate**: `remove_ticket_worktree` removes the worktree directory but not the local git branch (`analysis/{job_id}`). After many analysis runs, local branches pile up. The `cleanup_failed_intake` helper (pre-existing) handles both; the analysis path could use a similar approach, or a periodic cleanup routine.

3. **No `fetch_origin_main` before branch creation**: `create_ticket_branch_and_worktree` branches from `origin/main` without fetching first. This is pre-existing behavior, not introduced here. For analysis jobs this is low risk (the branch is only used for file writes, not for running the analysed project), but worth noting for future iterations.

4. **Unusual test lambda** (`test_analysis_worktree_isolation.py:104`): `(_ for _ in ()).throw(RuntimeError("LLM failed"))` is functionally correct but non-obvious. A plain `def` raising helper would be clearer.

---

## Décision

- REQUEST_CHANGES — one blocking fix required before approval

## Actions demandées

1. **[Required]** Fix `path_mapper.py:18` — change `path.startswith(self.container_root)` to `path == self.container_root or path.startswith(self.container_root + "/")`. Add a test case for the ambiguous-prefix scenario (e.g., `CONTAINER_RUNTIME_ROOT=/app`, path=`/applications/foo` → identity, not mapped).

---

IMPLEMENTATION_FIX_REQUIRED