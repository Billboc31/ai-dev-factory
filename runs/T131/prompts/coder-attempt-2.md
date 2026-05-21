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


# T131 — T131 — Supervisor daemon persistence and unexpected exit handling

**Source**: GitHub Issue #100

## Description

# Objective

Improve the host supervisor so the daemon lifecycle is durable, observable and resilient to unexpected exits.

## Included

- Detect when the supervised daemon process exits unexpectedly.
- Preserve daemon exit metadata:
  - last_exit_code
  - last_exit_time
  - last_error
- Expose daemon runtime state through the supervisor API.
- Add restart policy support:
  - no-restart
  - restart-on-crash
- Ensure the daemon is fully detached from transient API requests.
- Improve PID/liveness handling.
- Surface supervisor/daemon errors clearly in the dashboard.
- Add dashboard visibility for:
  - daemon crashed
  - daemon stopped unexpectedly
  - restart attempts
- Add tests for:
  - unexpected daemon exit
  - stale PID recovery
  - restart policy behavior
  - supervisor status reporting

## Excluded

- Generic job supervisor.
- Multi-process orchestration.
- Deployment supervision.
- Remote host execution.
- Kubernetes/systemd integration.

## Acceptance criteria

- The daemon continues running after dashboard/API requests complete.
- Unexpected daemon exits are detected and reported.
- Dashboard clearly shows daemon crash state.
- Restart-on-crash policy successfully relaunches the daemon.
- Stale PID files are recovered automatically.
- Supervisor status API exposes runtime and crash information.
- Existing daemon workflows continue to work.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Implementation complete. Here's a summary of what was done:

---

**Files modified:**

- **`services/supervisor/main.py`** — Full rewrite: added `DaemonState` dataclass, module globals (`_daemon_state`, `_daemon_proc`, `_voluntary_stop`, `_daemon_exec_cmd`), `_spawn_daemon()` helper, `_check_and_maybe_restart()` sync monitor step, `_monitor_daemon()` async background task, FastAPI `lifespan` (init from PID file + task management). Updated `daemon_status()` to return all new fields + stale PID recovery, `daemon_start()` to accept `restart_policy`, `daemon_stop()` to set `_voluntary_stop` flag.

- **`services/control_api/models/schemas.py`** — Extended `DaemonStatus` with 6 optional fields: `last_exit_code`, `last_exit_time`, `last_error`, `exit_unexpected`, `restart_count`, `restart_policy`.

- **`services/control_api/services/daemon_manager.py`** — `get_status()` now forwards all new fields from the supervisor `/daemon/status` response.

- **`apps/dashboard/src/pages/DaemonPage.jsx`** — Added `CrashBanner` component (shown when `exit_unexpected=true`, displays exit code / time / restart count) and a "Restarting…" badge inside the status card when `restart-on-crash` policy is active.

- **`tests/supervisor/test_supervisor.py`** — Added 4 new tests (8 total, all pass): unexpected exit detection, stale PID recovery, restart-on-crash policy, voluntary stop not flagged unexpected.

- **`apps/dashboard/tests/DaemonPage.test.jsx`** — Added 2 new tests (10 total, all pass): crash banner shown / not shown on normal stop.

---

## Review

Review written to `runs/T131/reviews/implementation-review.md`. Here's the summary:

---

## Review — T131: Supervisor Daemon Persistence

**Core implementation: correct.** The supervisor monitor loop, crash metadata, voluntary-stop flag, stale PID recovery, restart-on-crash policy, and dashboard CrashBanner all work as designed. Test coverage is solid across the critical paths.

**Two blocking issues require fixes before merge:**

### [BLOCKING 1] `docker-compose.yml` YAML indentation bug (line 24)
An extra space was inserted before `- AI_DEV_FACTORY_SUPERVISOR_URL=...`, breaking YAML parsing. The env var will either cause a Docker Compose parse error or be silently dropped, meaning the supervisor URL is never set in the container and the entire supervisor integration path is bypassed.

**Fix:** Remove the extra leading space on line 24.

### [BLOCKING 2] `restart_policy` not forwarded to supervisor
`daemon_manager.start()` sends only `{"exec_cmd": exec_cmd}` to the supervisor — `restart_policy` is omitted, so the supervisor always defaults to `"no-restart"`. Restart-on-crash can only be configured by calling the supervisor on port 8090 directly, not via the dashboard or control API.

**Fix:** Add `restart_policy: str = "no-restart"` to `daemon_manager.start()` and pass it through `_call_supervisor(...)`.

**Observations (non-blocking):** `supervisor_available` field is never populated; `last_exit_code` is `None` after a supervisor restart + crash (best-effort); no max restart count or backoff (follow-up).

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T131/reviews/implementation-review.md
- generated at: 2026-05-21T22:20:34Z

---

Review written to `runs/T131/reviews/implementation-review.md`. Here's the summary:

---

## Review — T131: Supervisor Daemon Persistence

**Core implementation: correct.** The supervisor monitor loop, crash metadata, voluntary-stop flag, stale PID recovery, restart-on-crash policy, and dashboard CrashBanner all work as designed. Test coverage is solid across the critical paths.

**Two blocking issues require fixes before merge:**

### [BLOCKING 1] `docker-compose.yml` YAML indentation bug (line 24)
An extra space was inserted before `- AI_DEV_FACTORY_SUPERVISOR_URL=...`, breaking YAML parsing. The env var will either cause a Docker Compose parse error or be silently dropped, meaning the supervisor URL is never set in the container and the entire supervisor integration path is bypassed.

**Fix:** Remove the extra leading space on line 24.

### [BLOCKING 2] `restart_policy` not forwarded to supervisor
`daemon_manager.start()` sends only `{"exec_cmd": exec_cmd}` to the supervisor — `restart_policy` is omitted, so the supervisor always defaults to `"no-restart"`. Restart-on-crash can only be configured by calling the supervisor on port 8090 directly, not via the dashboard or control API.

**Fix:** Add `restart_policy: str = "no-restart"` to `daemon_manager.start()` and pass it through `_call_supervisor(...)`.

**Observations (non-blocking):** `supervisor_available` field is never populated; `last_exit_code` is `None` after a supervisor restart + crash (best-effort); no max restart count or backoff (follow-up).

IMPLEMENTATION_FIX_REQUIRED