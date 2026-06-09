## Objective

When `failing_step` is `healthcheck.sh`, the logs drawer must surface structured probe diagnostics (tested URLs, HTTP codes, curl results, Traefik/backend/network data) in a dedicated "Failure details" section above the raw full logs, without removing that raw view.

## Included

### `tools/agent_runner/run_sandbox.py`
- Add `_parse_healthcheck_output(stdout: str, stderr: str, exit_code: int) -> dict` that parses healthcheck.sh stdout into a structured dict:
  ```
  {
    "probes": [{"name": str, "url": str, "result": "pass"|"fail", "http_code": str, "note": str}],
    "passed": int,
    "failed": int,
    "exit_code": int,
    "raw_stderr": str
  }
  ```
  Parsed from the well-defined stdout patterns emitted by healthcheck.sh:
  `PASS  name  (url)`, `FAIL  name  (url)  — http=CODE after N attempts`, `healthcheck: X passed, Y failed`.
- Call `_parse_healthcheck_output()` for every healthcheck.sh step execution (both pass and fail), store result in a local variable.
- Add `healthcheck_diagnostics: dict | None = None` parameter to `_write_validation_json()`.
- Include `healthcheck_diagnostics` in the written JSON when provided.
- Pass the parsed result when calling `_write_validation_json()`.

### `services/control_api/routes/runtime_dashboard.py`
- Add `DiagnosticsResponse` Pydantic model:
  ```python
  class DiagnosticsResponse(BaseModel):
      healthcheck_diagnostics: dict | None = None
      backend_diagnostics: dict | None = None
  ```
- Add endpoint `GET /sandbox-runs/{sandbox_id}/diagnostics` → `DiagnosticsResponse`:
  - Validates `sandbox_id` with the existing regex.
  - Reads `validation.json` from the sandbox dir.
  - Returns `healthcheck_diagnostics` and `backend_diagnostics` fields from it (both nullable).
  - Returns empty `DiagnosticsResponse` (both fields `None`) if validation.json is absent or malformed.

### `apps/dashboard/src/api/runtimeDashboard.js`
- Add `getSandboxDiagnostics(sandboxId)` function calling `GET /api/runtime-dashboard/sandbox-runs/{sandboxId}/diagnostics`.

### `apps/dashboard/src/components/runtime-dashboard/LogViewerDrawer.jsx`
- Accept new `failingStep` prop.
- When `failingStep === "healthcheck.sh"`:
  - Fetch diagnostics once on mount via `getSandboxDiagnostics(sandboxId)`.
  - Render a "Failure details" collapsible section at the top of the drawer (above raw logs) showing:
    - Per-probe rows: name, URL, result badge (PASS/FAIL), HTTP code, note.
    - Summary: `X passed / Y failed`, exit code.
    - Traefik/backend/network fields from `backend_diagnostics` if present (proxy status, container status, networks).
- Raw full log section remains unchanged below.

### `apps/dashboard/src/pages/RuntimeDashboardPage.jsx`
- Look up the run object by `logSandboxId` from the existing sandbox run list.
- Pass `failingStep={run?.failing_step}` to `<LogViewerDrawer>`.

## Excluded

- Modifying healthcheck.sh to write a sidecar file (parsing stdout in run_sandbox.py is sufficient and avoids requiring a writable runtime path inside the script).
- Changes to smoke.sh or any other lifecycle step.
- Changes to the auto-fix / fix-proposer flow.
- Adding healthcheck_diagnostics to `SandboxRunSummary` or the `/overview` endpoint.
- Any UI changes outside `LogViewerDrawer.jsx` and `RuntimeDashboardPage.jsx`.
- Backend diagnostics collection logic (already gathered by existing code; only exposure and surfacing in UI are in scope).

## Acceptance criteria

- When a sandbox run has `failing_step = "healthcheck.sh"`, opening its log drawer shows a "Failure details" section above the raw logs listing each probe's URL, HTTP status code, and pass/fail result.
- `validation.json` for a healthcheck failure includes a `healthcheck_diagnostics` key with a `probes` array, `passed`/`failed` counts, and `exit_code`.
- `GET /api/runtime-dashboard/sandbox-runs/{id}/diagnostics` returns `healthcheck_diagnostics` and `backend_diagnostics` (both nullable) with a 200 for any existing sandbox, 404 for unknown.
- The raw full log section remains present and functional in the drawer regardless of `failing_step`.
- When `failing_step` is absent or not `"healthcheck.sh"`, the "Failure details" section is not rendered.
- Existing step summary behavior and `LogViewerDrawer` polling behavior are unchanged.

---

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



# T180 — T180 - Healthcheck failure logs must prioritize actionable Traefik and proxy diagnostics

**Source**: GitHub Issue #212

## Description

## Problem

Environment deploy failures are now mostly caused by `healthcheck.sh`, but the current logs UI does not surface actionable diagnostics first.

Even with the new Full Logs proposal, users would still need to manually inspect a large raw log dump to understand proxy/routing failures.

The most common current failures are related to:

- Traefik routing
- proxy/backend connectivity
- incorrect runtime URLs
- healthcheck endpoint failures
- container/network resolution

---

## Goal

When `failing_step=healthcheck.sh`, the logs UI must prioritize actionable diagnostics before the raw logs.

The raw full logs should still remain available.

---

## Required UI behavior

Add a dedicated "Failure details" section above the raw logs.

When the failing step is `healthcheck.sh`, surface:

- tested URLs
- HTTP status codes
- curl/wget stdout/stderr
- resolved backend URL
- Traefik route diagnostics
- backend container status
- network diagnostics
- validation.json failure_type
- healthcheck exit code

---

## Required backend behavior

Expose structured healthcheck diagnostics from:

- validation.json
- healthcheck stdout/stderr
- runtime proxy diagnostics

Prefer structured fields over raw text parsing when possible.

---

## Important constraint

Do not remove the raw Full Logs view.

The diagnostics section should augment the logs, not replace them.

---

## Acceptance criteria

- Healthcheck failures surface actionable diagnostics immediately
- Traefik/proxy routing issues are visible without opening raw logs
- Tested URLs and HTTP codes are displayed clearly
- validation.json diagnostics are surfaced in the UI
- Raw full logs are still accessible
- Existing step summary behavior remains unchanged