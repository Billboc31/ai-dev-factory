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

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T218/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

## Objective
Introduce a batch-oriented backlog ingestion layer in the daemon so that newly discovered tickets are first analyzed individually by Ticket Intelligence, then grouped into a backlog batch that, once idle, is frozen and submitted to a new Global Dependency Analysis step. Readiness evaluation and Dispatcher scheduling will only run on tickets belonging to a finalized batch, while tickets arriving during execution are queued into the next batch.

## Included

### New module: backlog batch lifecycle
- New file `tools/agent_runner/backlog_batch.py`:
  - Defines `BatchStatus` enum with values: `collecting`, `frozen`, `dependency_analysis_running`, `dependency_analysis_failed`, `readiness_running`, `dispatching`, `completed`.
  - Functions:
    - `get_or_create_collecting_batch(db_path) -> batch_id` — returns the current open batch, creating one only if none exists or if existing collecting batch is full / parallel batches forbidden while a previous batch is `dispatching`.
    - `add_ticket_to_batch(db_path, batch_id, ticket_id)` — idempotent membership insert; bumps `last_activity_at`.
    - `try_freeze_idle_batches(db_path, idle_timeout_minutes, max_batch_size, now)` — transitions any `collecting` batch with `now - last_activity_at >= idle_timeout` (or size >= `max_batch_size`) to `frozen`. Returns list of frozen batch_ids.
    - `transition_batch(db_path, batch_id, from_status, to_status, *, reason=None)` — guarded transition with audit row.
    - `list_batch_tickets(db_path, batch_id) -> list[str]`.
    - `get_batch_status(db_path, batch_id)`.

### Schema additions in `tools/agent_runner/runtime_db.py`
- New table `backlog_batches`:
  - `batch_id TEXT PRIMARY KEY`, `status TEXT`, `created_at`, `frozen_at`, `last_activity_at`, `completed_at`, `notes TEXT NULL`.
- New table `backlog_batch_tickets`:
  - `batch_id TEXT`, `ticket_id TEXT`, `added_at`, PRIMARY KEY `(batch_id, ticket_id)`, UNIQUE `(ticket_id)` (a ticket belongs to at most one batch).
- New table `ticket_dependency_analysis`:
  - `ticket_id TEXT`, `batch_id TEXT`, `depends_on_json`, `blocks_json`, `parallel_group TEXT NULL`, `conflicting_tickets_json`, `execution_phase TEXT NULL`, `relationship_classifications_json`, `analyzed_at`, PRIMARY KEY `(ticket_id, batch_id)`.
- Helper functions: `upsert_dependency_analysis`, `get_dependency_analysis`, plus the batch helpers consumed by `backlog_batch.py`.
- Reuse the existing `runtime_events` table to log batch transitions (new `event_type`: `batch.transition`).

### Global Dependency Analyzer
- New file `tools/agent_runner/global_dependency_analyzer.py`:
  - Entry point `run_global_analysis(db_path, runs_dir, batch_id, *, exec_cmd, timeout_seconds)`.
  - Reads ticket.md + existing `ticket_intelligence.dependency_hints` for every ticket in the batch.
  - Builds a single prompt containing the batch summary (id, title, intelligence summary, hints) and calls the configured AI command (`exec_cmd`) using the same subprocess pattern as `ticket_intelligence_analyzer.py`.
  - Parses a strict JSON response of the form:
    ```json
    {
      "tickets": [
        { "ticket_id": "T011", "depends_on": ["T010"], "blocks": [], "parallel_group": "foundation", "conflicting_tickets": [], "execution_phase": 1 }
      ],
      "relationships": [
        { "from": "T011", "to": "T010", "type": "HARD_DEPENDENCY" }
      ]
    }
    ```
    where `type ∈ {HARD_DEPENDENCY, SOFT_DEPENDENCY, FOUNDATION_DEPENDENCY, PARALLEL_COMPATIBLE, CONFLICTING_SCOPE}`.
  - Persists results via `upsert_dependency_analysis` and merges `depends_on` into the union consumed by readiness (the union of markdown deps, intelligence hints, and now batch-analysis deps).
  - On failure (timeout, malformed JSON), marks batch `dependency_analysis_failed`, logs the failure, and never raises.
- New prompt template `prompts/global-dependency-analyzer-prompt.md` with placeholders for `{{batch_tickets}}` and explicit JSON output schema.

### Integration in the union of dependencies
- Extend `ticket_readiness_evaluator.py` and `ticket_execution_eligibility.py` so the dependency union also includes `ticket_dependency_analysis.depends_on_json` when present, with the same merge semantics already used for intelligence hints.

### Daemon loop integration in `tools/agent_runner/run_daemon.py`
- After `poll_github_issues()` and per-ticket `call_issue_intake()`, attach each newly intaken ticket to the current collecting batch via `add_ticket_to_batch`. This call happens **before** `poll_ticket_pipeline()`.
- Modify `poll_ticket_pipeline()` (or split it) so that:
  - Ticket Intelligence still runs per-ticket continuously, regardless of batch state.
  - Readiness evaluation only runs for tickets whose batch status is `readiness_running` (and afterwards, kept idempotent for already-evaluated tickets).
- Add a new periodic step `process_backlog_batches(db_path, runs_dir, settings)` called once per daemon cycle, just after the pipeline step:
  - Call `try_freeze_idle_batches`.
  - For each newly-frozen batch (or batch in `frozen`): transition to `dependency_analysis_running`, run `global_dependency_analyzer.run_global_analysis`, then transition to `readiness_running` on success.
  - When all tickets in `readiness_running` batches have a completed readiness evaluation, transition to `dispatching`.
  - When all tickets in `dispatching` have reached a terminal state (merged, cancelled, or failed final), transition to `completed`.
- Gate Dispatcher (`ticket_dispatcher.py`) ranking so it only considers tickets whose batch status is `dispatching` (legacy non-dispatcher path remains untouched).
- Honour `allow_parallel_batches`: when `false`, refuse to create a new collecting batch while another batch is in `dispatching` — the next batch creation is deferred until completion; tickets ingested in the meantime still land in *a* new collecting batch (`pending_collecting`), but it never transitions to `frozen` until the previous batch is `completed`.

### Configuration in `tools/agent_runner/runtime_settings.py`
- Register four new settings with sane defaults and env-var overrides:
  - `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` (default: existing `--interval`, fallback 60).
  - `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES` (default: 10).
  - `BACKLOG_MAX_BATCH_SIZE` (default: 50).
  - `BACKLOG_ALLOW_PARALLEL_BATCHES` (default: `false`).
- Expose them via the existing DB-override → env-var → default precedence used by the other settings.

### Logging and observability
- Use `runtime_events` to emit at minimum: `batch.created`, `batch.ticket_added`, `batch.frozen`, `batch.dependency_analysis_started`, `batch.dependency_analysis_completed`, `batch.dependency_analysis_failed`, `batch.readiness_started`, `batch.dispatching`, `batch.completed`. Each event carries `batch_id`, ticket counts, and the previous/next status.
- Mirror key transitions to stderr logs in `run_daemon.py` (already the existing pattern for other periodic steps).

### Tests in `tests/`
- `test_backlog_batch.py`:
  - Creating a collecting batch; adding tickets; idempotency; UNIQUE membership.
  - Idle freeze: a batch with no activity for `idle_timeout` transitions to `frozen`; an active batch does not.
  - `max_batch_size` triggers an immediate freeze even before idle timeout.
  - `allow_parallel_batches=false`: while a prior batch is `dispatching`, a new ticket goes into a new `collecting` batch that does not freeze until the prior reaches `completed`.
- `test_global_dependency_analyzer.py`:
  - Builds the prompt from a batch of fake tickets.
  - Parses a well-formed JSON response and persists `depends_on`, `blocks`, `parallel_group`, `conflicting_tickets`, `execution_phase`.
  - Rejects malformed JSON (status → `dependency_analysis_failed`, no exception bubbled up).
  - Subprocess invocation is mocked.
- `test_daemon_batch_lifecycle.py`:
  - End-to-end with a stubbed `exec_cmd`: tickets are intaken → intelligence runs → no readiness yet → batch idle → dependency analysis runs → readiness runs → dispatcher sees tickets only after batch reaches `dispatching`.
  - Tickets arriving while a batch is in `dispatching` land in a new batch and do not affect the executing batch.
- Extend `test_ticket_readiness_evaluator.py` with a case where `ticket_dependency_analysis.depends_on_json` provides a dep that is not in markdown or intelligence hints.
- Extend `test_run_daemon.py` to assert the new `process_backlog_batches` call site exists in the cycle.

## Excluded
- Replacing or restructuring the existing per-ticket Ticket Intelligence module — only its scheduling context changes, not its analyzer.
- Changing the Dispatcher's ranking algorithm, scoring, or eligibility evaluator beyond gating it on batch status and consuming the new dependency union.
- Any UI, dashboard, CLI inspector, or API endpoint to visualise batches — observability is limited to `runtime_events` and stderr logs.
- Backfilling existing tickets (already in `runs/`) into batches: only tickets discovered after the feature is enabled are placed into batches; legacy tickets continue to follow the pre-existing non-batch flow.
- Cross-batch dependency analysis (each batch is analyzed in isolation; dependencies on tickets from previous batches use the existing markdown / intelligence-hint union).
- Persisting the global dependency *graph* as a separate first-class object beyond the per-ticket rows already covered by `ticket_dependency_analysis`.
- Changing GitHub polling semantics other than honouring the new `BACKLOG_GITHUB_POLL_INTERVAL_SECONDS` setting; the existing `gh`-based fetch is preserved.
- Migrating settings to a config file format; new settings reuse the current env-var / SQLite override registry.
- Modifying the worker spawn path / `launch_ticket` beyond the indirect effect of the dispatcher gate.

## Acceptance criteria
- Running the daemon on a fresh runtime DB creates the four new tables (`backlog_batches`, `backlog_batch_tickets`, `ticket_dependency_analysis`, plus migrations applied to existing DBs) without errors.
- A newly intaken ticket is recorded in a `collecting` batch and receives Ticket Intelligence within the next pipeline cycle; its `ticket_readiness` row is **not** populated while the batch is still `collecting` or `frozen`.
- A batch with no new tickets for `BACKLOG_BATCH_IDLE_TIMEOUT_MINUTES` transitions to `frozen` on the next daemon cycle; this is asserted by `test_backlog_batch.py` and observable in `runtime_events`.
- After freeze, `global_dependency_analyzer.run_global_analysis` is invoked exactly once for the batch; on success the batch transitions to `readiness_running`, and `ticket_dependency_analysis` rows exist for every ticket in the batch.
- Dependencies returned by the analyzer are merged into the union consumed by the readiness evaluator and the eligibility gate (verified by an integration test that uses an analyzer-only dependency).
- The Dispatcher's ranked recommendations only include tickets whose batch is in status `dispatching`; tickets in batches still in `collecting`, `frozen`, `dependency_analysis_running`, or `readiness_running` are absent from its output.
- With `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, while a batch is in `dispatching`, any ticket discovered in the meantime is attached to a new `collecting` batch that does not transition to `frozen` until the prior batch reaches `completed`; covered by `test_backlog_batch.py`.
- The full batch lifecycle (`collecting → frozen → dependency_analysis_running → readiness_running → dispatching → completed`) is observable through `runtime_events` rows with the documented event types.
- Disabling the dispatcher (`AI_DEV_FACTORY_DISPATCHER_MODE=off`) reproduces the previous legacy non-batched behaviour: existing daemon and pipeline tests in `tests/` continue to pass without modification (except for the targeted additions described above).
- `pytest tests/test_backlog_batch.py tests/test_global_dependency_analyzer.py tests/test_daemon_batch_lifecycle.py` passes; the full repository test suite still passes after the changes.
- A malformed or timeout AI response for the dependency analyzer leaves the batch in `dependency_analysis_failed`, never raises out of `process_backlog_batches`, and is retried on the next cycle without duplicating already-persisted rows.

---

## Review

# Plan review — batch status and dependency analysis retry semantics

The T218 plan is strong overall. It introduces a coherent batch-oriented ingestion flow:

```text
collect tickets
→ run Ticket Intelligence
→ freeze batch
→ run Global Dependency Analysis
→ run Readiness
→ allow Dispatcher scheduling
```

This matches the desired architecture for stable Dispatcher execution.

However, two points must be corrected before implementation.

## 1. `pending_collecting` is referenced but not defined

The plan defines the following `BatchStatus` values:

```text
collecting
frozen
dependency_analysis_running
dependency_analysis_failed
readiness_running
dispatching
completed
```

But later it says that when `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, new tickets discovered while another batch is dispatching should land in a new `pending_collecting` batch.

That status does not exist in the planned enum.

This creates ambiguity for:

- schema constraints
- lifecycle transitions
- freeze behavior
- tests
- Dispatcher gating

The plan must choose one explicit strategy.

Recommended strategy for V1:

```text
collecting + blocked_from_freezing flag/reason
```

instead of introducing `pending_collecting` as a separate lifecycle status.

Alternative acceptable strategy:

```text
add pending_collecting to BatchStatus
```

but then transitions must be fully defined.

## 2. `dependency_analysis_failed` retry behavior is unclear

The plan says that dependency analysis failures transition the batch to:

```text
dependency_analysis_failed
```

without raising.

But the acceptance criteria says malformed or timeout AI responses are retried on the next cycle.

The retry policy is not defined.

The plan must explicitly define:

- whether retry is automatic or manual
- max retry count
- retry cooldown
- where retry metadata is stored
- what happens after retries are exhausted
- whether partial persisted rows are cleared or reused

Recommended V1 strategy:

```text
- automatic retry
- max 3 attempts
- cooldown controlled by setting or default 5 minutes
- store retry_count and last_error in backlog_batches
- after max attempts, keep dependency_analysis_failed and require manual reset/future ticket
```

The analyzer must remain idempotent:

```text
retrying the same batch must not duplicate dependency rows or events incorrectly
```

## Review verdict

PLAN_FIX_REQUIRED until:

1. the `pending_collecting` / blocked collecting behavior is made explicit;
2. dependency analysis retry semantics are fully specified.

---

## Instructions de fix

# Plan fix — clarify collecting batches and dependency analysis retries

Update `runs/T218/plan.md` before implementation.

The current plan must be corrected in two areas:

1. remove or explicitly define `pending_collecting`;
2. define retry semantics for `dependency_analysis_failed`.

## 1. Batch lifecycle when parallel batches are disabled

T218 V1 should avoid introducing an undefined `pending_collecting` status.

### Required V1 approach

Use only the planned statuses:

```text
collecting
frozen
dependency_analysis_running
dependency_analysis_failed
readiness_running
dispatching
completed
```

When `BACKLOG_ALLOW_PARALLEL_BATCHES=false` and a batch is already `dispatching`, newly discovered tickets should still be placed into a new `collecting` batch.

However, that collecting batch must be prevented from freezing until the active dispatching batch is completed.

Add explicit metadata to `backlog_batches`, for example:

```text
freeze_blocked BOOLEAN DEFAULT FALSE
freeze_blocked_reason TEXT NULL
```

or an equivalent field.

Expected behavior:

```text
Batch A = dispatching
new tickets arrive
→ Batch B created with status collecting
→ Batch B receives tickets and Ticket Intelligence runs
→ Batch B does not freeze while Batch A is dispatching
→ when Batch A reaches completed, Batch B becomes eligible for idle/max-size freeze
```

Do not use `pending_collecting` unless it is added to `BatchStatus` and fully documented.

### Required plan edits

Replace wording like:

```text
pending_collecting
```

with:

```text
collecting batch blocked from freezing while another batch is dispatching
```

Update tests accordingly:

```text
allow_parallel_batches=false:
- while Batch A is dispatching, Batch B remains collecting even if idle timeout is exceeded
- after Batch A completed, Batch B can freeze on the next cycle
```

## 2. Dependency analysis retry semantics

The plan must define what happens after:

```text
dependency_analysis_failed
```

### Required V1 retry policy

Use automatic retry with bounded attempts.

Add metadata to `backlog_batches`, for example:

```text
dependency_analysis_attempts INTEGER DEFAULT 0
last_dependency_analysis_error TEXT NULL
next_dependency_analysis_retry_at TEXT NULL
```

Defaults:

```text
max attempts = 3
retry cooldown = 5 minutes
```

These may be hardcoded in V1 or exposed as settings if simple.

### State behavior

On dependency analysis start:

```text
frozen or dependency_analysis_failed eligible for retry
→ dependency_analysis_running
→ attempts += 1
```

On success:

```text
dependency_analysis_running
→ readiness_running
```

On failure before max attempts:

```text
dependency_analysis_running
→ dependency_analysis_failed
next_dependency_analysis_retry_at = now + cooldown
```

On next daemon cycles:

```text
if status = dependency_analysis_failed
and attempts < max_attempts
and now >= next_dependency_analysis_retry_at
→ retry automatically
```

After max attempts:

```text
status remains dependency_analysis_failed
no automatic retry
batch is not dispatchable
log explicit terminal failure
future manual reset can be handled by another ticket
```

### Idempotency requirements

Retries must be safe:

```text
- upsert ticket_dependency_analysis rows
- do not duplicate dependency rows
- do not duplicate membership rows
- emit clear runtime_events per attempt
```

If a previous failed attempt partially persisted rows, the next successful attempt may overwrite/upsert them.

## Acceptance criteria updates

Add or update acceptance criteria:

- No undefined `pending_collecting` status is used.
- With `BACKLOG_ALLOW_PARALLEL_BATCHES=false`, a second collecting batch cannot freeze while an earlier batch is dispatching.
- After the earlier batch completes, the second collecting batch can freeze normally.
- Dependency analysis failure increments attempt count and records last error.
- Failed dependency analysis retries automatically after cooldown until max attempts.
- After max attempts, the batch remains `dependency_analysis_failed` and is not scheduled by Dispatcher.
- Retry logic is idempotent and uses upserts for `ticket_dependency_analysis`.
- Tests cover failure, retry success, and max-attempt exhaustion.

## Non-goals

Keep these out of T218:

- UI for manually resetting failed dependency analysis batches
- dashboard visualization for batches
- cross-batch dependency recomputation
- human approval UI for dependency suggestions

Those can be future tickets.