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


# T130 — T130 — AI-assisted operational project analysis and deploy profile generation

**Source**: GitHub Issue #99

## Description

# T130 — AI-assisted operational project analysis and deploy profile generation

## Objective

Add an AI-assisted deployer workflow able to analyze any managed repository and generate reviewable operational documentation and deployment profiles.

The workflow must use the LLM runtime configured by the daemon/executor environment instead of hardcoding a specific AI provider.

## Included

- Add an “Analyze Project” action to the deployer UI.
- Use deterministic Python project scanning as structured context input.
- Send repository structure + scan result to the configured LLM runtime.
- Generate:
  - `.ai-dev-factory/deploy.yml`
  - `.ai-dev-factory/deployment.md`
  - optional `.ai-dev-factory/runtime-notes.md`
- Infer:
  - required tools
  - docker services
  - host-side processes
  - build commands
  - startup commands
  - restart commands
  - healthchecks
  - runtime dependencies
  - environment variables
  - known operational constraints
- Commit generated operational files to a dedicated branch.
- Create or update a PR for human review.
- Show analysis progress, logs and failures in the dashboard.
- Add tests for:
  - prompt generation
  - AI execution orchestration
  - file generation
  - Git branch workflow
  - PR creation/update

## Excluded

- Automatic deployment execution.
- Automatic install of missing dependencies.
- Automatic merge.
- Secrets management.
- Remote/cloud deployment orchestration.

## Acceptance criteria

- A user can trigger repository operational analysis from the dashboard.
- The configured LLM runtime analyzes the repository and generates reviewable operational files.
- Generated deploy.yml is valid and compatible with the deployer runtime.
- Generated documentation explains how to build/start/restart/check the project.
- Generated files are committed to a dedicated branch.
- A PR is created or updated automatically.
- Existing deployer/runtime workflows remain functional.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

36/36 pass. All good. Let me now do a final summary of everything created and modified.

---

## Summary

Implementation complete. Here's what was built:

### New files (7)

| File | Purpose |
|------|---------|
| `tools/agent_runner/analysis_prompt_builder.py` | Pure string construction of the LLM prompt (file tree + scan + DeployProfile schema + generation instructions) |
| `tools/agent_runner/analysis_git_service.py` | Creates `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}` branch, commits `.ai-dev-factory/`, pushes, creates or updates PR via `gh` |
| `tools/agent_runner/run_analysis.py` | Host-side analysis worker: scans project, builds prompt, invokes LLM via `exec_cmd`, parses `--- BEGIN FILE ---` blocks, writes files, calls git service |
| `services/control_api/services/analysis_manager.py` | HTTP proxy from control API to supervisor for start/status/logs |
| `tests/test_analysis_prompt_builder.py` | 4 tests: file tree, schema, all 3 file instructions, determinism |
| `tests/test_analysis_manager.py` | 5 tests: delegation, unreachable supervisor, 409 lock, no supervisor URL, status proxy |
| `tests/test_analysis_git_service.py` | 3 tests: branch name format, PR create on new branch, PR edit on existing branch |

### Modified files (5)

| File | Changes |
|------|---------|
| `services/supervisor/main.py` | Added `_state_dir()`, analysis PID/log/state helpers, per-project lock, 4 endpoints: `POST /analysis/start`, `GET /analysis/{id}/status` (with zombie detection), `GET /analysis/{id}/logs`, `POST /analysis/{id}/stop` |
| `services/control_api/models/schemas.py` | Added `AnalysisStatus` model |
| `services/control_api/routes/deployer.py` | Added 3 routes: `POST /analyze` (202), `GET /analysis/status`, `GET /analysis/logs` |
| `apps/dashboard/src/api/deployer.js` | Added `analyzeProject`, `getAnalysisStatus`, `getAnalysisLogs` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | Added `AnalysisStatusPanel`, `AnalysisLogsPanel`, "Analyze Project" button, analysis polling |

All 36 deployer + analysis tests pass. The 44 pre-existing failures are unrelated to this ticket (daemon/ticket workflow tests) and were failing before these changes.

---

## Review

I now have enough information to write the review.

---

# Review — T130: AI-assisted operational project analysis and deploy profile generation

## Summary

The implementation is architecturally clean and covers the majority of ticket requirements: the "Analyze Project" button is present, LLM invocation is environment-driven, file generation follows the specified schema, git branching and PR creation/update are implemented, and the dashboard surfaces status and logs. The layering (worker → supervisor → control API → frontend) mirrors the existing deployer pattern correctly.

However, there are two blocking issues that prevent approval.

---

## Blocking Issues

### 1. Missing required tests — AI execution orchestration and file generation

The ticket explicitly requires:
> Add tests for: prompt generation, **AI execution orchestration**, **file generation**, Git branch workflow, PR creation/update

The implementation provides:
- ✅ `test_analysis_prompt_builder.py` — prompt generation (4 tests)
- ✅ `test_analysis_git_service.py` — git branch, PR create, PR update
- ✅ `test_analysis_manager.py` — HTTP proxy

But **no tests exist** for `run_analysis.py`, which contains:
- `_extract_files(llm_output)` — the regex file block parser, which is the most critical parsing logic
- `_scan_project(path)` — project scanner
- `_build_file_tree(path)` — tree generator
- The orchestration flow in `main()` (state machine: scan → prompt → LLM → parse → validate → write → commit)

`_extract_files` in particular is non-trivial: it's a regex over LLM output that the whole workflow depends on. A test like "given a well-formed LLM response, returns the three expected files" and "given a response missing deploy.yml, raises RuntimeError" is straightforward to write and directly covers a ticket acceptance criterion.

These tests were explicitly named in the ticket scope and are absent.

### 2. Path traversal in `run_analysis.py` via LLM-generated file paths

In `run_analysis.py:186-189`:

```python
for rel_path, content in generated_files.items():
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
```

The `rel_path` comes directly from LLM output regex capture groups. If the LLM (or a prompt injection via the file tree) returns a path like `../../sensitive_file`, `target` resolves outside `project_root`. The `required` check only validates that two specific paths are present — it does not prevent arbitrary additional paths from being written anywhere.

Fix: validate all extracted paths stay within `.ai-dev-factory/` before writing:

```python
for rel_path, content in generated_files.items():
    if not rel_path.startswith(".ai-dev-factory/"):
        raise RuntimeError(f"LLM returned unexpected path outside .ai-dev-factory/: {rel_path}")
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
```

---

## Important Observation (Non-Blocking)

### `--print` flag hardcoded in `_invoke_llm()`

`run_analysis.py:115`:
```python
cmd_parts = shlex.split(exec_cmd) + ["--print"]
```

The ticket states: *"use the LLM runtime configured by the daemon/executor environment instead of hardcoding a specific AI provider."* Appending `--print` unconditionally ties the implementation to the Claude CLI interface. A different `exec_cmd` (e.g., an OpenAI proxy or a local model) would need to accept `--print`. This is an architectural tension with the ticket's stated intent.

This is non-blocking because the existing daemon already uses Claude CLI exclusively, and the `exec_cmd` is a Claude CLI invocation in practice. But it should be noted in runtime documentation or addressed if multi-provider support is a real near-term requirement.

---

## Minor Observations (Non-Blocking)

- `analysis_git_service.py`: `git checkout -b {branch}` runs from whatever branch the project is currently on, with no prior `git fetch` or `git checkout main`. If the managed repo is mid-operation or on a non-default branch, the analysis branch will diverge from the wrong base. Low-risk in current usage; worth a note.

- `analysis_git_service.py`: `gh pr create` has no `--base` argument. Defaults to the repo's default branch, which is correct in nearly all cases.

- `supervisor/main.py:283`: `from fastapi.responses import JSONResponse` imported inside the endpoint function body. Functional, but inconsistent with module-level imports used elsewhere.

- `AnalysisStatusPanel` returns `null` for `idle` state, so there's no visual indication that analysis has never run, unlike the deploy status panel which is always visible. Minor UX inconsistency.

---

## Acceptance Criteria Check

| Criterion | Status |
|---|---|
| "Analyze Project" button in dashboard | ✅ |
| LLM analyzes repo via configured runtime | ✅ |
| Generates deploy.yml compatible with deployer runtime | ✅ |
| Generated documentation covers build/start/restart/check | ✅ |
| Files committed to dedicated branch | ✅ |
| PR created or updated automatically | ✅ |
| Dashboard shows progress, logs, failures | ✅ |
| Existing deployer workflows remain functional | ✅ |
| Tests: prompt generation | ✅ |
| Tests: AI execution orchestration | ❌ |
| Tests: file generation | ❌ |
| Tests: Git branch workflow | ✅ |
| Tests: PR creation/update | ✅ |

---

## Required Fixes

1. Add unit tests for `run_analysis.py`:
   - `_extract_files()` — at minimum: valid multi-file response, missing required file raises error, malformed delimiter handling
   - `main()` orchestration — with mocked `_invoke_llm`, `_scan_project`, `commit_and_push`

2. Add path validation in `run_analysis.py` before writing extracted files to prevent path traversal.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T130/reviews/implementation-review.md
- generated at: 2026-05-21T21:29:35Z

---

I now have enough information to write the review.

---

# Review — T130: AI-assisted operational project analysis and deploy profile generation

## Summary

The implementation is architecturally clean and covers the majority of ticket requirements: the "Analyze Project" button is present, LLM invocation is environment-driven, file generation follows the specified schema, git branching and PR creation/update are implemented, and the dashboard surfaces status and logs. The layering (worker → supervisor → control API → frontend) mirrors the existing deployer pattern correctly.

However, there are two blocking issues that prevent approval.

---

## Blocking Issues

### 1. Missing required tests — AI execution orchestration and file generation

The ticket explicitly requires:
> Add tests for: prompt generation, **AI execution orchestration**, **file generation**, Git branch workflow, PR creation/update

The implementation provides:
- ✅ `test_analysis_prompt_builder.py` — prompt generation (4 tests)
- ✅ `test_analysis_git_service.py` — git branch, PR create, PR update
- ✅ `test_analysis_manager.py` — HTTP proxy

But **no tests exist** for `run_analysis.py`, which contains:
- `_extract_files(llm_output)` — the regex file block parser, which is the most critical parsing logic
- `_scan_project(path)` — project scanner
- `_build_file_tree(path)` — tree generator
- The orchestration flow in `main()` (state machine: scan → prompt → LLM → parse → validate → write → commit)

`_extract_files` in particular is non-trivial: it's a regex over LLM output that the whole workflow depends on. A test like "given a well-formed LLM response, returns the three expected files" and "given a response missing deploy.yml, raises RuntimeError" is straightforward to write and directly covers a ticket acceptance criterion.

These tests were explicitly named in the ticket scope and are absent.

### 2. Path traversal in `run_analysis.py` via LLM-generated file paths

In `run_analysis.py:186-189`:

```python
for rel_path, content in generated_files.items():
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
```

The `rel_path` comes directly from LLM output regex capture groups. If the LLM (or a prompt injection via the file tree) returns a path like `../../sensitive_file`, `target` resolves outside `project_root`. The `required` check only validates that two specific paths are present — it does not prevent arbitrary additional paths from being written anywhere.

Fix: validate all extracted paths stay within `.ai-dev-factory/` before writing:

```python
for rel_path, content in generated_files.items():
    if not rel_path.startswith(".ai-dev-factory/"):
        raise RuntimeError(f"LLM returned unexpected path outside .ai-dev-factory/: {rel_path}")
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
```

---

## Important Observation (Non-Blocking)

### `--print` flag hardcoded in `_invoke_llm()`

`run_analysis.py:115`:
```python
cmd_parts = shlex.split(exec_cmd) + ["--print"]
```

The ticket states: *"use the LLM runtime configured by the daemon/executor environment instead of hardcoding a specific AI provider."* Appending `--print` unconditionally ties the implementation to the Claude CLI interface. A different `exec_cmd` (e.g., an OpenAI proxy or a local model) would need to accept `--print`. This is an architectural tension with the ticket's stated intent.

This is non-blocking because the existing daemon already uses Claude CLI exclusively, and the `exec_cmd` is a Claude CLI invocation in practice. But it should be noted in runtime documentation or addressed if multi-provider support is a real near-term requirement.

---

## Minor Observations (Non-Blocking)

- `analysis_git_service.py`: `git checkout -b {branch}` runs from whatever branch the project is currently on, with no prior `git fetch` or `git checkout main`. If the managed repo is mid-operation or on a non-default branch, the analysis branch will diverge from the wrong base. Low-risk in current usage; worth a note.

- `analysis_git_service.py`: `gh pr create` has no `--base` argument. Defaults to the repo's default branch, which is correct in nearly all cases.

- `supervisor/main.py:283`: `from fastapi.responses import JSONResponse` imported inside the endpoint function body. Functional, but inconsistent with module-level imports used elsewhere.

- `AnalysisStatusPanel` returns `null` for `idle` state, so there's no visual indication that analysis has never run, unlike the deploy status panel which is always visible. Minor UX inconsistency.

---

## Acceptance Criteria Check

| Criterion | Status |
|---|---|
| "Analyze Project" button in dashboard | ✅ |
| LLM analyzes repo via configured runtime | ✅ |
| Generates deploy.yml compatible with deployer runtime | ✅ |
| Generated documentation covers build/start/restart/check | ✅ |
| Files committed to dedicated branch | ✅ |
| PR created or updated automatically | ✅ |
| Dashboard shows progress, logs, failures | ✅ |
| Existing deployer workflows remain functional | ✅ |
| Tests: prompt generation | ✅ |
| Tests: AI execution orchestration | ❌ |
| Tests: file generation | ❌ |
| Tests: Git branch workflow | ✅ |
| Tests: PR creation/update | ✅ |

---

## Required Fixes

1. Add unit tests for `run_analysis.py`:
   - `_extract_files()` — at minimum: valid multi-file response, missing required file raises error, malformed delimiter handling
   - `main()` orchestration — with mocked `_invoke_llm`, `_scan_project`, `commit_and_push`

2. Add path validation in `run_analysis.py` before writing extracted files to prevent path traversal.

IMPLEMENTATION_FIX_REQUIRED