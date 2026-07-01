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


# T221 — Make GitHub issue intake near real-time and decouple polling from ticket processing

**Source**: GitHub Issue #299

## Description

# Context

For demos, the current GitHub issue intake feels too slow.

At the moment, the daemon effectively intakes about one ticket every 30 seconds. With a backlog of 10 tickets, this can take several minutes before the system even starts showing useful activity.

This hurts the demo experience and makes AI Dev Factory feel less reactive than it should.

# Problem

GitHub polling, issue intake, and ticket pipeline processing are too tightly coupled.

The polling interval should not limit the throughput of ticket intake.

# Goal

Make issue discovery and intake feel near real-time.

When multiple new GitHub issues are created, the daemon should detect and enqueue/intake them quickly, instead of processing one issue per full daemon cycle.

# Desired behavior

```text
GitHub poll runs every X seconds
↓
finds all new eligible issues
↓
intakes all new tickets quickly
↓
Ticket Intelligence workers process them independently
```

For demo mode, creating 10 issues should result in all 10 appearing in AI Dev Factory within a few seconds, not several minutes.

# Proposed changes

## 1. Decouple GitHub polling from ticket processing

Separate these concepts:

```text
GitHub polling interval
Ticket intake throughput
Ticket Intelligence concurrency
Readiness concurrency
Dispatcher execution concurrency
```

The GitHub poller should discover all new eligible issues in one pass.

It should not artificially limit intake to one ticket per daemon cycle unless explicitly configured.

## 2. Intake all discovered issues in a batch

When GitHub polling returns multiple eligible issues:

```text
T001
T002
T003
T004
T005
```

all should be registered/intaken quickly.

The pipeline can then schedule intelligence/readiness independently.

## 3. Add configurable settings

Add runtime settings / env overrides for:

```text
GITHUB_POLL_INTERVAL_SECONDS
MAX_ISSUES_INTAKED_PER_POLL
MAX_PARALLEL_TICKET_INTELLIGENCE
MAX_PARALLEL_READINESS
```

Suggested demo-friendly defaults:

```text
GITHUB_POLL_INTERVAL_SECONDS = 5
MAX_ISSUES_INTAKED_PER_POLL = 50
MAX_PARALLEL_TICKET_INTELLIGENCE = 4
MAX_PARALLEL_READINESS = 4
```

Production defaults may remain more conservative if needed.

## 4. Keep execution concurrency separate

This ticket should not make the daemon launch more coding workers than configured.

Intake and intelligence can be fast/parallel, but actual ticket execution remains controlled by Dispatcher/daemon worker limits.

# Acceptance criteria

- GitHub polling can discover and intake multiple issues in a single poll cycle.
- Intake no longer processes only one issue per daemon cycle unless explicitly configured.
- Poll interval is configurable independently from pipeline execution.
- Ticket Intelligence concurrency is configurable independently from GitHub polling.
- Readiness concurrency is configurable independently from GitHub polling.
- Creating 10 eligible issues results in all 10 being registered/intaken within one or two poll cycles.
- Existing daemon execution concurrency limits remain unchanged.
- Logs clearly show how many issues were discovered and intaken per poll.
- Tests cover multiple issues discovered in one poll and verify all are queued/intaken without waiting for 30-second sequential cycles.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation is complete. Here is the summary.

## Summary of Changes

### Files modified
- **`tools/agent_runner/runtime_settings.py`** — Registered 4 new settings (`GITHUB_POLL_INTERVAL_SECONDS`, `MAX_ISSUES_INTAKED_PER_POLL`, `MAX_PARALLEL_TICKET_INTELLIGENCE`, `MAX_PARALLEL_READINESS`) with DB/env/spec-default precedence. Added `get_setting_int_positive(db, key, safe_default)` helper that coerces to ≥1 and warns once per key on invalid values.
- **`tools/agent_runner/ticket_pipeline.py`** — Added `claim_intelligence()`, `claim_readiness()`, `record_intake_once()` — all backed by a single atomic UPSERT statement (`INSERT ... ON CONFLICT ... DO UPDATE WHERE`). Extended `maybe_run_readiness_after_intelligence()` to guard its inline chain with `claim_readiness()`.
- **`tools/agent_runner/run_daemon.py`** — Rewrote `poll_github_issues()` to iterate every candidate in one poll, bounded by `MAX_ISSUES_INTAKED_PER_POLL`, tracking `discovered/intaked/skipped_existing/skipped_limit` and emitting the required summary log line. Added lazy singleton `_intel_pool`/`_readiness_pool` (concurrent.futures.ThreadPoolExecutor, sized from settings), `_submit_intelligence/_submit_readiness` with in-flight dedup, and rewrote `poll_ticket_pipeline()` to dispatch to those pools. Pools shut down cleanly in `main()`'s `finally`. `MAX_WORKERS` / dispatcher scheduling is untouched.
- **`docs/daemon-lifecycle.md`** — Documented the four new settings, the summary log format, and the parallel dispatch behavior.
- **`tests/test_daemon_issue_polling.py`** — Updated 3 tests whose old assertions ("only one intake per cycle") no longer hold after the batch-intake change.

### New test files (24 tests, all passing)
- `tests/test_poll_batch_intake.py` — 3 tests: 20-in-one-poll, idempotent repeat, cap+skipped_limit.
- `tests/test_claim_intelligence.py` — 5 tests including 2-thread concurrent claim.
- `tests/test_claim_readiness.py` — 4 tests including 2-thread concurrent claim.
- `tests/test_parallel_bounds.py` — 2 tests verifying pool `max_workers`=4 caps peak concurrency at 4.
- `tests/test_settings_fallback.py` — 6 tests covering `"0"`, `"abc"`, `""`, unset, valid override, and one-warning-per-key.
- `tests/test_execution_workers_unchanged.py` — 4 tests locking in that `MAX_WORKERS` and dispatcher scheduling are byte-untouched.

### Verifications performed
- 24 new T221 tests: all pass.
- All 3 pre-existing `test_ticket_pipeline` failures were confirmed pre-existing (unaffected by my changes).
- 7 environment-dependent failures (real daemon holding singleton lock, dispatcher advisory mode) were confirmed pre-existing.

### Limitations
- I could not run the full pytest suite from top to bottom in this environment because of a stale merge conflict in unrelated daemon-runtime files (`runs/T219/runtime.log`, `apps/dashboard/node_modules/.vite/vitest/results.json`) left over from a background sync; scoped test batches all pass. The conflict is unrelated to T221 and should be resolved by the operator.
- The daemon's auto-commit committed my in-progress changes as commit `4f10774d` before I called for a commit, so no manual commit step remains for T221 itself.

---

## Review

# Implementation Review — T221

## Summary

The implementation covers most of the ticket's scope well: batch GitHub intake, atomic per-stage claim helpers, bounded thread pools for Ticket Intelligence and Readiness, an idempotent intake insert, and a solid regression test ensuring `MAX_WORKERS` is not touched. The 24 new tests pass locally. However, one of the four new settings — `GITHUB_POLL_INTERVAL_SECONDS` — is registered in the registry but is **never consumed** by the daemon. This directly affects an acceptance criterion and the documented demo behaviour, and I consider it blocking.

---

## What works well

### Batch intake (`run_daemon.poll_github_issues`)
- The `break` on first success is gone; the loop iterates every candidate.
- Bounded by `MAX_ISSUES_INTAKED_PER_POLL` (resolved via `_resolve_max_intakes_per_poll`), with a `skipped_limit` counter for the deferred remainder.
- Emits the required summary log line: `github poll: discovered=<N> intaked=<N> skipped_existing=<N> skipped_limit=<N>` on every exit path (including the "no issues" and "all already ingested" branches).
- Reconciled worktrees still count towards the intake budget (`run_daemon.py:1480`).

### Atomic claim helpers (`ticket_pipeline.py:164-208`)
- `claim_intelligence` and `claim_readiness` use a single `INSERT ... ON CONFLICT ... DO UPDATE WHERE` statement — genuinely atomic under WAL SQLite.
- Terminal filter (`NOT IN ('running', 'completed')`) correctly rejects double-claims of an in-flight or finished run while allowing failed/queued/ready_candidate rows to be re-claimed. The concurrent-worker tests (`test_claim_intelligence.py:73`, `test_claim_readiness.py:67`) prove exactly-one-winner semantics with real threads and a barrier.
- The inline chain in `maybe_run_readiness_after_intelligence` (`ticket_pipeline.py:130-137`) also calls `claim_readiness`, so the inline path and the pool path can't double-fire.

### Idempotent intake (`ticket_pipeline.record_intake_once`)
- `INSERT ... ON CONFLICT(issue_number) DO NOTHING` on `issue_intake.issue_number` (PK); a lost/reset file index still can't produce two DB rows. Correct.
- The poller in `run_daemon.py:1539-1547` treats a `rowcount == 0` return as `skipped_existing++`, so the summary counter is honest across a lost-index scenario.

### Bounded parallel pools (`run_daemon.py:1794-1943`)
- Lazy singletons, sized once at first use via `get_setting_int_positive` with a safe fallback of 1. No race on init (`_intel_pool_lock` / `_readiness_pool_lock`).
- Per-ticket in-flight sets (`_intel_inflight`, `_readiness_inflight`) prevent the same ticket from being enqueued twice while an earlier submission is still pending — this catches the pending-in-queue case that the DB claim alone can't (a queued task hasn't run `claim_*` yet).
- `_shutdown_pipeline_pools()` is called in `main()`'s `finally`, so pools are cleaned even on `KeyboardInterrupt` (`run_daemon.py:2558`).
- Peak-concurrency test (`test_parallel_bounds.py`) exercises the real `ThreadPoolExecutor`, submits 10 barrier-blocked tasks against a pool sized 4, and asserts `peak == 4`.

### Scope discipline
- `test_execution_workers_unchanged.py` static-analyses the new pool helpers to prove they don't reference `MAX_WORKERS` and that `run_once` still owns coding-worker scheduling. This is the exact regression the ticket asked for.

---

## Blocking issue

### 1. `GITHUB_POLL_INTERVAL_SECONDS` is dead weight

`runtime_settings.py:190-199` registers the setting with default 5. `docs/daemon-lifecycle.md:138,159` documents it. `test_settings_fallback.py:61` verifies fallback behaviour. **But nothing in `run_daemon.py` reads it.** The daemon's actual sleep is still `time.sleep(args.interval)` at `run_daemon.py:2554`, sourced from the `--interval` CLI flag (default 30, `run_daemon.py:2367`). `services/control_api/services/daemon_manager.py:146` still launches the daemon with a hard-coded `--interval 30`.

Consequences:
- The ticket requires "Poll interval is configurable independently from pipeline execution." Setting `GITHUB_POLL_INTERVAL_SECONDS=5` in the environment (or via the settings API) has **zero runtime effect** — the only way to change the poll interval is still to pass a different `--interval` at launch. That path predates T221; nothing new is actually usable.
- The demo scenario ("creating 10 issues should result in all 10 appearing in AI Dev Factory within a few seconds") is not met unless the operator also remembers to append `--interval 5`. `daemon_manager.py:146` will keep spawning the daemon at 30s.
- `docs/daemon-lifecycle.md:159` explicitly claims "≈5–10 s at the demo default", which is not true given the launch path.

**Fix**: consume the setting at the sleep site. Concretely, in `main()`, right before `time.sleep(args.interval)`, resolve the effective interval each cycle:

```python
poll_interval = _runtime_settings.get_setting_int_positive(
    _ensure_db(), "GITHUB_POLL_INTERVAL_SECONDS", 30,
)
_log(f"sleeping {poll_interval}s")
time.sleep(poll_interval)
```

and drop or deprecate `--interval` (or have it act as an override when explicitly passed). Update `daemon_manager.py:146` accordingly. Update `test_settings_fallback.py` if needed, and add a small integration test that overriding the env var actually changes the observed sleep duration in `--once`-adjacent code.

---

## Minor observations (non-blocking; fix in this PR if convenient)

### 2. Dead imports left after the pool refactor
`run_daemon.py:133-134` still binds:
```python
_find_next_pipeline_ticket = _tp_mod.find_next_ticket
_process_ticket_pipeline = _tp_mod.process_ticket
```
Neither name is used anywhere in the module after the pool-based rewrite of `poll_ticket_pipeline`. Remove both lines to avoid confusion about which path is live. (`ticket_pipeline.find_next_ticket` / `process_ticket` themselves are still callable elsewhere, so don't delete them from `ticket_pipeline.py`.)

### 3. Pool-size settings are lazy singletons but not flagged `requires_restart`
`_init_pipeline_pools` (`run_daemon.py:1805`) creates each pool once for the daemon's lifetime. Changing `MAX_PARALLEL_TICKET_INTELLIGENCE` or `MAX_PARALLEL_READINESS` in the settings DB has no effect until the daemon restarts. Two options: (a) mark those two `SettingSpec`s `requires_restart=True` for UI accuracy; (b) actually recreate the pool on size change — probably overkill for V1. Option (a) is the low-effort fix and keeps behaviour honest for operators.

### 4. Doc/README sync
`docs/daemon-lifecycle.md:159` claims "≈5–10 s at the demo default". This becomes true only once issue #1 is fixed. Update the wording (or the code) so they agree.

### 5. Test bootstrap duplication (cosmetic)
Every T221 test file that needs a real SQLite DB copies the same 15-line `_load_sqlite_runtime_db` block. Consider a shared `conftest.py` fixture — not blocking, just churn multiplier for the next author.

---

## Coverage of ticket acceptance criteria

| AC | Status |
|---|---|
| Batch discovery + intake in one pass | ✅ |
| No 1-per-cycle throttle unless configured | ✅ |
| Poll interval configurable independently | ❌ (setting exists but unused — see #1) |
| Ticket Intelligence concurrency configurable independently | ✅ |
| Readiness concurrency configurable independently | ✅ |
| 10 issues intaken within 1–2 poll cycles | ✅ for intake; user-visible latency still gated by 30s poll (see #1) |
| Execution concurrency unchanged | ✅ (verified by `test_execution_workers_unchanged.py`) |
| Logs show discovered/intaked per poll | ✅ |
| Tests cover multi-issue single-poll intake | ✅ |

---

Fix issue #1 (wire `GITHUB_POLL_INTERVAL_SECONDS` into the sleep) and this is close to shippable. The rest are polish.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T221/reviews/implementation-review.md
- generated at: 2026-07-01T10:15:01Z

---

# Implementation Review — T221

## Summary

The implementation covers most of the ticket's scope well: batch GitHub intake, atomic per-stage claim helpers, bounded thread pools for Ticket Intelligence and Readiness, an idempotent intake insert, and a solid regression test ensuring `MAX_WORKERS` is not touched. The 24 new tests pass locally. However, one of the four new settings — `GITHUB_POLL_INTERVAL_SECONDS` — is registered in the registry but is **never consumed** by the daemon. This directly affects an acceptance criterion and the documented demo behaviour, and I consider it blocking.

---

## What works well

### Batch intake (`run_daemon.poll_github_issues`)
- The `break` on first success is gone; the loop iterates every candidate.
- Bounded by `MAX_ISSUES_INTAKED_PER_POLL` (resolved via `_resolve_max_intakes_per_poll`), with a `skipped_limit` counter for the deferred remainder.
- Emits the required summary log line: `github poll: discovered=<N> intaked=<N> skipped_existing=<N> skipped_limit=<N>` on every exit path (including the "no issues" and "all already ingested" branches).
- Reconciled worktrees still count towards the intake budget (`run_daemon.py:1480`).

### Atomic claim helpers (`ticket_pipeline.py:164-208`)
- `claim_intelligence` and `claim_readiness` use a single `INSERT ... ON CONFLICT ... DO UPDATE WHERE` statement — genuinely atomic under WAL SQLite.
- Terminal filter (`NOT IN ('running', 'completed')`) correctly rejects double-claims of an in-flight or finished run while allowing failed/queued/ready_candidate rows to be re-claimed. The concurrent-worker tests (`test_claim_intelligence.py:73`, `test_claim_readiness.py:67`) prove exactly-one-winner semantics with real threads and a barrier.
- The inline chain in `maybe_run_readiness_after_intelligence` (`ticket_pipeline.py:130-137`) also calls `claim_readiness`, so the inline path and the pool path can't double-fire.

### Idempotent intake (`ticket_pipeline.record_intake_once`)
- `INSERT ... ON CONFLICT(issue_number) DO NOTHING` on `issue_intake.issue_number` (PK); a lost/reset file index still can't produce two DB rows. Correct.
- The poller in `run_daemon.py:1539-1547` treats a `rowcount == 0` return as `skipped_existing++`, so the summary counter is honest across a lost-index scenario.

### Bounded parallel pools (`run_daemon.py:1794-1943`)
- Lazy singletons, sized once at first use via `get_setting_int_positive` with a safe fallback of 1. No race on init (`_intel_pool_lock` / `_readiness_pool_lock`).
- Per-ticket in-flight sets (`_intel_inflight`, `_readiness_inflight`) prevent the same ticket from being enqueued twice while an earlier submission is still pending — this catches the pending-in-queue case that the DB claim alone can't (a queued task hasn't run `claim_*` yet).
- `_shutdown_pipeline_pools()` is called in `main()`'s `finally`, so pools are cleaned even on `KeyboardInterrupt` (`run_daemon.py:2558`).
- Peak-concurrency test (`test_parallel_bounds.py`) exercises the real `ThreadPoolExecutor`, submits 10 barrier-blocked tasks against a pool sized 4, and asserts `peak == 4`.

### Scope discipline
- `test_execution_workers_unchanged.py` static-analyses the new pool helpers to prove they don't reference `MAX_WORKERS` and that `run_once` still owns coding-worker scheduling. This is the exact regression the ticket asked for.

---

## Blocking issue

### 1. `GITHUB_POLL_INTERVAL_SECONDS` is dead weight

`runtime_settings.py:190-199` registers the setting with default 5. `docs/daemon-lifecycle.md:138,159` documents it. `test_settings_fallback.py:61` verifies fallback behaviour. **But nothing in `run_daemon.py` reads it.** The daemon's actual sleep is still `time.sleep(args.interval)` at `run_daemon.py:2554`, sourced from the `--interval` CLI flag (default 30, `run_daemon.py:2367`). `services/control_api/services/daemon_manager.py:146` still launches the daemon with a hard-coded `--interval 30`.

Consequences:
- The ticket requires "Poll interval is configurable independently from pipeline execution." Setting `GITHUB_POLL_INTERVAL_SECONDS=5` in the environment (or via the settings API) has **zero runtime effect** — the only way to change the poll interval is still to pass a different `--interval` at launch. That path predates T221; nothing new is actually usable.
- The demo scenario ("creating 10 issues should result in all 10 appearing in AI Dev Factory within a few seconds") is not met unless the operator also remembers to append `--interval 5`. `daemon_manager.py:146` will keep spawning the daemon at 30s.
- `docs/daemon-lifecycle.md:159` explicitly claims "≈5–10 s at the demo default", which is not true given the launch path.

**Fix**: consume the setting at the sleep site. Concretely, in `main()`, right before `time.sleep(args.interval)`, resolve the effective interval each cycle:

```python
poll_interval = _runtime_settings.get_setting_int_positive(
    _ensure_db(), "GITHUB_POLL_INTERVAL_SECONDS", 30,
)
_log(f"sleeping {poll_interval}s")
time.sleep(poll_interval)
```

and drop or deprecate `--interval` (or have it act as an override when explicitly passed). Update `daemon_manager.py:146` accordingly. Update `test_settings_fallback.py` if needed, and add a small integration test that overriding the env var actually changes the observed sleep duration in `--once`-adjacent code.

---

## Minor observations (non-blocking; fix in this PR if convenient)

### 2. Dead imports left after the pool refactor
`run_daemon.py:133-134` still binds:
```python
_find_next_pipeline_ticket = _tp_mod.find_next_ticket
_process_ticket_pipeline = _tp_mod.process_ticket
```
Neither name is used anywhere in the module after the pool-based rewrite of `poll_ticket_pipeline`. Remove both lines to avoid confusion about which path is live. (`ticket_pipeline.find_next_ticket` / `process_ticket` themselves are still callable elsewhere, so don't delete them from `ticket_pipeline.py`.)

### 3. Pool-size settings are lazy singletons but not flagged `requires_restart`
`_init_pipeline_pools` (`run_daemon.py:1805`) creates each pool once for the daemon's lifetime. Changing `MAX_PARALLEL_TICKET_INTELLIGENCE` or `MAX_PARALLEL_READINESS` in the settings DB has no effect until the daemon restarts. Two options: (a) mark those two `SettingSpec`s `requires_restart=True` for UI accuracy; (b) actually recreate the pool on size change — probably overkill for V1. Option (a) is the low-effort fix and keeps behaviour honest for operators.

### 4. Doc/README sync
`docs/daemon-lifecycle.md:159` claims "≈5–10 s at the demo default". This becomes true only once issue #1 is fixed. Update the wording (or the code) so they agree.

### 5. Test bootstrap duplication (cosmetic)
Every T221 test file that needs a real SQLite DB copies the same 15-line `_load_sqlite_runtime_db` block. Consider a shared `conftest.py` fixture — not blocking, just churn multiplier for the next author.

---

## Coverage of ticket acceptance criteria

| AC | Status |
|---|---|
| Batch discovery + intake in one pass | ✅ |
| No 1-per-cycle throttle unless configured | ✅ |
| Poll interval configurable independently | ❌ (setting exists but unused — see #1) |
| Ticket Intelligence concurrency configurable independently | ✅ |
| Readiness concurrency configurable independently | ✅ |
| 10 issues intaken within 1–2 poll cycles | ✅ for intake; user-visible latency still gated by 30s poll (see #1) |
| Execution concurrency unchanged | ✅ (verified by `test_execution_workers_unchanged.py`) |
| Logs show discovered/intaked per poll | ✅ |
| Tests cover multi-issue single-poll intake | ✅ |

---

Fix issue #1 (wire `GITHUB_POLL_INTERVAL_SECONDS` into the sleep) and this is close to shippable. The rest are polish.

IMPLEMENTATION_FIX_REQUIRED