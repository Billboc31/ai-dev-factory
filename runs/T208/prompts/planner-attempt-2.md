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

## Artifact-only output (strict)

Your response will be written verbatim to `runs/<ticket>/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.

This rule applies to both initial plans and rewrites after a review.
Examples of forbidden openings: "The plan has been rewritten…",
"This plan now covers…", "Plan rewritten as a real implementation
document…", "Key points covered…", "The document now contains…".

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



# T208 — Fix Ticket Intelligence analysis stuck in running state

**Source**: GitHub Issue #272

## Description

# Fix Ticket Intelligence analysis stuck in running state

## Context

The Ticket Intelligence feature currently fails to complete analyses reliably.

Observed behavior:

```text
User clicks 'Analyze'
↓
analysis status = running
↓
analysis never completes
↓
after 900 seconds
↓
reaper marks analysis as failed
```

UI error:

```text
Analysis failed

Analysis stuck in 'running' for 900s — auto-recovered by reaper.
```

This makes Ticket Intelligence effectively unusable.

## Problem

The analysis lifecycle enters:

```text
running
```

but never reaches:

```text
completed
```

or

```text
failed
```

The reaper eventually detects the stale analysis and forces failure.

Possible causes include:

- background worker never starts
- exception swallowed inside background task
- AI call hangs indefinitely
- subprocess never exits
- missing timeout on LLM execution
- analysis result never persisted
- status transition never executed
- deadlock while updating runtime database

## Goal

Guarantee that every Ticket Intelligence analysis eventually reaches:

```text
completed
```

or

```text
failed
```

with a meaningful error message.

No analysis should remain indefinitely in:

```text
running
```

## Scope

Investigate the complete Ticket Intelligence execution pipeline:

```text
UI trigger
↓
Control API endpoint
↓
background execution
↓
AI invocation
↓
database persistence
↓
status transitions
↓
reaper interaction
```

## Required changes

### Background execution reliability

Verify that analysis jobs always start and always terminate.

Unexpected exceptions must never be silently swallowed.

All exceptions must:

```text
log error
persist failure reason
set status = failed
```

### AI timeout handling

Ensure all AI/model invocations have explicit timeouts.

### Runtime persistence

Successful analyses always persist:

```text
status = completed
completed_at
analysis payload
```

Failures must persist:

```text
status = failed
error_message
failed_at
```

### Observability

Add detailed runtime logging:

```text
analysis started
analysis step started
AI request started
AI request completed
analysis persisted
analysis failed
```

### Reaper improvements

The reaper should preserve original failure causes when known instead of always replacing them with the generic timeout message.

## Tests

Add tests covering:

- successful execution
- AI timeout
- unexpected exception path
- reaper recovery
- no silent failures

## Acceptance criteria

- No Ticket Intelligence analysis remains indefinitely in `running`.
- Every analysis eventually becomes `completed` or `failed`.
- AI calls use explicit timeouts.
- Exceptions are logged and persisted.
- Failure reasons are visible in UI.
- Reaper preserves original failure causes when available.
- Runtime logs clearly show analysis lifecycle steps.
- Existing Ticket Intelligence functionality continues to work.
- All new and existing tests pass.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T208/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

## Objective
Eliminate the "stuck in running" failure mode of Ticket Intelligence analyses. Every analysis must reach `completed` or `failed` quickly with a meaningful, preserved error message — never relying on the 900 s reaper to mask a swallowed exception or a dead worker.

## Included

### 1. Background-thread lifecycle hardening
- `services/control_api/routes/intelligence.py` (`analyze_intelligence._bg`, ~L353-363) and `services/supervisor/main.py` (`project_ticket_intelligence_analyze._bg`, ~L2339-2348):
  - On any exception escaping `run_analysis`, the `_bg` wrapper must persist `analysis_status="failed"` with `analysis_summary="Background thread crashed: <exc>"` and `failed_at=<utc-iso>`. Today the `except` only logs.
  - Wrap the entire body of `tools/agent_runner/ticket_intelligence_analyzer.py::run_analysis` in a top-level `try/finally`. The `finally` block re-reads the row; if status is still `queued` or `running`, force-transition it to `failed` with summary `"Analyzer exited without terminal status"`. This closes the path where any code between the `running` write and a terminal write raises (currently `_normalize`, `_load_prompt_template`, `extract_signals`, JSON serialization can do so).
  - Move the `analysis_status="running"` upsert to the very first statement of the `try` block (already there) and add a matching `started_at=<utc-iso>` column write.

### 2. Subprocess execution made forcibly bounded
- In `ticket_intelligence_analyzer.run_analysis`, replace the `subprocess.run(..., timeout=_ANALYSIS_TIMEOUT)` call (L271-280) with a `subprocess.Popen` + `proc.communicate(timeout=_ANALYSIS_TIMEOUT)` pattern that, on `TimeoutExpired`, calls `proc.kill()` then a second `proc.communicate()` to drain pipes, ensuring no orphaned child holds the worker thread.
- Add a configurable `_ANALYSIS_TIMEOUT = int(os.environ.get("AI_DEV_FACTORY_INTEL_TIMEOUT", "120"))` so the upper bound is explicit and tunable.
- Log `intel.ai_request.started` (with command, timeout, prompt_size) before `Popen` and `intel.ai_request.completed` (with rc, stdout_len, stderr_len, duration_ms) after `communicate`. Both at INFO level on `_intel_log`.

### 3. Schema and persistence
- `tools/agent_runner/runtime_db.py`:
  - Add columns `started_at TEXT`, `completed_at TEXT`, `failed_at TEXT`, `failure_origin TEXT` to the `ticket_intelligence` table. Use `ALTER TABLE … ADD COLUMN IF NOT EXISTS` style: an idempotent migration in `init_runtime_db` that introspects `PRAGMA table_info('ticket_intelligence')` and adds missing columns.
  - Extend `upsert_ticket_intelligence` to accept these fields (already passes through `**fields`, but verify no allow-list filtering).
- In `ticket_intelligence_analyzer.run_analysis`, set `completed_at=<utc-iso>` on the success path (L340-346) and `failed_at=<utc-iso>` together with `failure_origin` (`"timeout"`, `"nonzero_rc"`, `"json_parse"`, `"exception"`, `"finally_guard"`) on every failure path.

### 4. Reaper preserves original cause
- `tools/agent_runner/ticket_intelligence_recovery.py::reap_stale_intelligence` (L72-121):
  - Before overwriting, `SELECT analysis_summary, failure_origin` for the row.
  - If `analysis_summary` is non-empty and `failure_origin` is set, keep them and only append `" (reaper-confirmed after Xs)"`. Set `failure_origin="reaper-confirmed"` only when no prior origin exists.
  - When no prior summary exists, write the current generic message but with `failure_origin="reaper-stale"`.
- Add `failed_at=<utc-iso>` to the reaper's upsert so failure timestamp is recorded uniformly.

### 5. Observability — additional structured log lines
In `ticket_intelligence_analyzer.run_analysis`, emit on `_intel_log` (INFO):
- `intel.step.signals_extracted ticket_id=… signals_count=N`
- `intel.step.prompt_built ticket_id=… prompt_len=N`
- `intel.ai_request.started` / `intel.ai_request.completed` (see §2)
- `intel.step.json_parsed ticket_id=… fields=…`
- `intel.persisted ticket_id=… status=completed|failed db_path=…`

### 6. Tests (in `tests/`)
- `test_ticket_intelligence_analyzer.py` — add cases:
  - `test_completed_persists_completed_at` — happy path writes `completed_at`.
  - `test_timeout_uses_kill_and_persists_failed_at` — patch `Popen` so `communicate` raises `TimeoutExpired`; assert `proc.kill()` called, status `failed`, `failure_origin="timeout"`, `failed_at` set.
  - `test_unexpected_exception_in_extract_persists_failed` — monkey-patch `extract_signals` to raise; assert status `failed`, `failure_origin="exception"`.
  - `test_finally_guard_marks_running_row_failed` — monkey-patch `_normalize` to call `os._exit`-equivalent via raising `BaseException`; the `finally` re-checks and writes `failed`.
- `test_ticket_intelligence_recovery.py` — add:
  - `test_reaper_preserves_existing_summary` — pre-seed a `running` row with a real error in `analysis_summary` and `failure_origin="exception"`; expect those preserved with a `(reaper-confirmed after Xs)` suffix.
  - `test_reaper_writes_failed_at` — assert `failed_at` populated.
- `test_ticket_intelligence_api.py` — add:
  - `test_bg_thread_crash_persists_failed` — patch `_analyzer.run_analysis` to raise immediately; after the POST, GET returns `failed` with a `"Background thread crashed"` summary (no need for the 900 s reaper).

### 7. Files modified
- `services/control_api/routes/intelligence.py`
- `services/supervisor/main.py`
- `tools/agent_runner/ticket_intelligence_analyzer.py`
- `tools/agent_runner/ticket_intelligence_recovery.py`
- `tools/agent_runner/runtime_db.py`
- `services/control_api/models/schemas.py` (extend `TicketIntelligence` with optional `started_at`, `completed_at`, `failed_at`, `failure_origin` so the new columns surface to the dashboard)
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx` (display `failure_origin` and `failed_at` alongside the failure message; minor JSX-only change)
- New/extended tests under `tests/`

## Excluded
- Replacing the threading-based background execution with a real queue or process pool (Celery, RQ, asyncio worker). Out of scope — would require new infrastructure.
- Changing the dashboard polling cadence or auto-retry behaviour (`apps/dashboard/src/components/TicketIntelligencePanel.jsx` polling logic stays as-is).
- Reworking the supervisor delegation HTTP protocol between the Docker API and the host supervisor.
- Adding metrics/Prometheus instrumentation (logging only for now).
- Reaper threshold tuning (`STALE_QUEUED_SECONDS=600`, `STALE_RUNNING_SECONDS=900`). Values stay; we only change what the reaper writes.
- Touching the `ticket_intelligence_extractor` deterministic signal logic.
- Backfilling `completed_at` / `failed_at` for historical rows (NULL on existing rows is acceptable; only new analyses populate them).

## Acceptance criteria
- A POST to `/tickets/{id}/intelligence/analyze` whose background thread raises before `run_analysis` returns leaves the row in `failed` (not `queued` or `running`) within the next poll — verified by `test_bg_thread_crash_persists_failed`.
- A simulated AI subprocess hang produces `failed`, `failure_origin="timeout"`, `failed_at` set, and the `claude` child process is killed (no zombie). Verified by `test_timeout_uses_kill_and_persists_failed_at`.
- A success path writes `analysis_status="completed"`, `completed_at`, and full payload in a single `upsert_ticket_intelligence` call.
- The reaper, when triggered on a row whose `analysis_summary` already contains a real error, preserves that summary and only appends `" (reaper-confirmed after Xs)"`. Verified by `test_reaper_preserves_existing_summary`.
- `PRAGMA table_info('ticket_intelligence')` on a freshly initialised DB lists `started_at`, `completed_at`, `failed_at`, `failure_origin`. An already-populated DB receives the same columns via `init_runtime_db` without data loss.
- `_intel_log` produces, for every analysis, the ordered sequence: `intel.queued` → `intel.started` → `intel.step.signals_extracted` → `intel.step.prompt_built` → `intel.ai_request.started` → `intel.ai_request.completed` → (`intel.step.json_parsed` →) `intel.persisted` (status=`completed` or `failed`).
- The dashboard panel renders the original failure summary and `failure_origin` for `failed` analyses (visual check; no logic regression in StatusBadge).
- `pytest tests/test_ticket_intelligence_*.py` passes — both new and pre-existing tests.
- `ruff` / existing lint config passes on all touched files.
- No analysis row remains in `queued` or `running` for longer than `_ANALYSIS_TIMEOUT + 30 s` under any code path covered by the tests above.

---

## Review

# Plan review — T208 must cover Postgres runtime DB

The T208 plan is directionally correct and addresses the observed failure mode: Ticket Intelligence analyses can remain stuck in `running` until the 900s reaper marks them failed.

The plan correctly includes:

- hardening background thread exception handling
- bounding AI subprocess execution with explicit timeout and kill
- persisting terminal failure states
- adding lifecycle timestamps
- improving reaper behavior
- adding structured logs and tests

However, the plan currently only describes schema/persistence changes for the SQLite runtime DB:

```text
tools/agent_runner/runtime_db.py
```

This is incomplete because AI Dev Factory also has a Postgres runtime DB path:

```text
tools/agent_runner/runtime_db_pg.py
```

If T208 adds these fields only to SQLite:

```text
started_at
completed_at
failed_at
failure_origin
```

then Ticket Intelligence may work in SQLite but fail or silently lose data in Postgres-backed runtimes.

## Blocking issue

The plan must explicitly verify and update the Postgres implementation for the `ticket_intelligence` table and related upsert/select helpers.

Required coverage:

1. Add the same columns to Postgres schema initialization if `ticket_intelligence` exists there.
2. Ensure idempotent schema migration for existing Postgres databases.
3. Ensure `upsert_ticket_intelligence` / read helpers persist and return the new fields.
4. Ensure API schema exposure remains compatible across both SQLite and Postgres runtimes.
5. Add at least one test or acceptance criterion that validates Postgres compatibility.

## Required correction

Update `runs/T208/plan.md` so that:

- `tools/agent_runner/runtime_db_pg.py` is included in the files modified if it owns the Postgres ticket intelligence schema.
- Postgres schema initialization/migration includes `started_at`, `completed_at`, `failed_at`, and `failure_origin`.
- Postgres persistence/read paths are verified for the new fields.
- Tests or acceptance criteria explicitly cover the Postgres path.

## Review verdict

PLAN_FIX_REQUIRED until Postgres runtime DB coverage is explicitly included or explicitly proven unnecessary.

---

## Instructions de fix

# Plan fix — include Postgres runtime DB coverage for Ticket Intelligence lifecycle fields

## Required plan update

Update `runs/T208/plan.md` before implementation starts.

The plan must not only update the SQLite runtime database implementation.

It must also verify and update the Postgres runtime database implementation when it owns the same `ticket_intelligence` persistence path.

## New lifecycle fields

T208 introduces these fields:

```text
started_at
completed_at
failed_at
failure_origin
```

They must be consistently supported across runtime DB implementations.

## SQLite path

Already planned:

```text
tools/agent_runner/runtime_db.py
```

Keep the existing SQLite plan:

- introspect `PRAGMA table_info('ticket_intelligence')`
- add missing columns idempotently
- persist fields through `upsert_ticket_intelligence`
- return fields through read helpers

## Postgres path

Add explicit coverage for:

```text
tools/agent_runner/runtime_db_pg.py
```

Required behavior:

1. If `ticket_intelligence` is defined in `runtime_db_pg.py`, add the same columns:

```sql
started_at TEXT
completed_at TEXT
failed_at TEXT
failure_origin TEXT
```

or the equivalent Postgres-compatible column types already used by the project.

2. Use idempotent Postgres migration syntax, for example:

```sql
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS started_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS completed_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failed_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failure_origin TEXT;
```

3. Ensure Postgres upsert logic persists these fields.

4. Ensure Postgres read/list helpers return these fields.

5. Ensure API schema compatibility remains identical whether the runtime DB is SQLite or Postgres.

## Tests / acceptance criteria

Add at least one of the following:

### Preferred

A focused Postgres runtime DB unit test if the project already has PG test infrastructure.

Example:

```text
test_pg_ticket_intelligence_lifecycle_fields_are_created_and_round_trip
```

### Acceptable fallback

If no PG test infrastructure exists, add explicit acceptance criteria and comments near `runtime_db_pg.py` changes explaining that:

- Postgres schema creation includes the fields
- Postgres upsert accepts the fields
- Postgres read helpers return the fields
- SQLite and Postgres expose the same public Ticket Intelligence shape

## Acceptance criteria additions

Add these to the corrected plan:

- `runtime_db_pg.py` is checked for `ticket_intelligence` support.
- If Postgres stores Ticket Intelligence, it includes `started_at`, `completed_at`, `failed_at`, and `failure_origin`.
- SQLite and Postgres Ticket Intelligence persistence expose the same lifecycle fields.
- The API `TicketIntelligence` schema remains backend-agnostic.
- Tests or explicit acceptance criteria cover the Postgres path.

## Non-goals reminder

Do not introduce a new database abstraction layer in T208.

Do not migrate historical rows.

Do not change the reaper thresholds.

Do not replace the existing background execution model with a queue system.