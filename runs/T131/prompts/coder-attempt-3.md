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

Both fixes applied and verified. Here's what changed:

**Files modified:**

- **`docker-compose.yml`** — Removed the extra leading space on line 24 before `- AI_DEV_FACTORY_SUPERVISOR_URL=...`. YAML now parses correctly and the env var is picked up by the container.

- **`services/control_api/models/schemas.py`** — Added `DaemonStartRequest` model with `restart_policy: str = "no-restart"`.

- **`services/control_api/services/daemon_manager.py`** — Added `restart_policy: str = "no-restart"` to `start()` and `restart()`. The supervisor call now passes `{"exec_cmd": exec_cmd, "restart_policy": restart_policy}`.

- **`services/control_api/routes/daemon.py`** — Updated all four start/restart endpoints (default and project-scoped) to accept an optional `DaemonStartRequest` body and forward `restart_policy` to the manager.

The `restart_policy` flows fully: dashboard → `POST /daemon/start` → `daemon_manager.start()` → `_call_supervisor(...)` → supervisor `POST /daemon/start`.

---

## Review

Now I have all I need. Let me write the structured review.

---

## Review — T131: Supervisor Daemon Persistence and Unexpected Exit Handling

### Summary

The implementation is complete, cohesive, and covers all seven acceptance criteria. The supervisor architecture is well-separated: daemon state lives in the supervisor process, the control-API delegates cleanly, and the dashboard exposes crash metadata. Tests cover the critical paths.

Below I document one notable correctness gap, a durability limitation, and minor observations.

---

### 1. Correctness Relative to Ticket Requirements

| Acceptance criterion | Status | Notes |
|---|---|---|
| Daemon survives after API request | ✅ | `start_new_session=True` on all Popen calls |
| Unexpected exits detected and reported | ✅ | Monitor polls `_is_alive()` every 5 s, sets `exit_unexpected` |
| Dashboard shows crash state | ✅ | `CrashBanner` with exit code, time, restart count |
| Restart-on-crash relaunches | ✅ | `_check_and_maybe_restart()` + `_spawn_daemon()` |
| Stale PID recovered automatically | ✅ | Both lifespan startup and `/daemon/status` handle it |
| Supervisor status API exposes runtime/crash info | ✅ | 10-field response from `GET /daemon/status` |
| Existing daemon workflows preserved | ✅ | All four start paths remain functional |

---

### 2. Notable Issue — `_daemon_state.pid` not cleared in `daemon_stop()` (main.py:400–416)

After `daemon_stop()` sends SIGTERM, `_daemon_state.pid` retains the old PID. The PID file is removed but the in-memory state is not updated until the monitor's next 5-second cycle.

**Consequence:** if a caller invokes `POST /daemon/start` immediately after `POST /daemon/stop`, `daemon_start()` reads `_daemon_state.pid` (old PID), calls `_is_alive(pid)` while the process is still dying, and returns `{"ok": False, "error": "already_running"}`. This window is typically milliseconds but it is observable from the dashboard (Stop → immediate Start).

**Recommended fix** — clear `_daemon_state.pid` in `daemon_stop()` before returning:

```python
os.kill(pid, signal.SIGTERM)
_daemon_state.pid = None  # add this line
_daemon_state.started_at = None  # and this
_remove_pid_file()
```

This matches the semantics (`_daemon_proc` is not cleared either, but the monitor handles that).

---

### 3. Durability Limitation — `_daemon_exec_cmd` and `restart_policy` lost on supervisor restart (main.py:237–257)

If the supervisor process itself restarts (crash or redeploy) while a daemon is running with a non-default `exec_cmd` and `restart_policy="restart-on-crash"`:

- The lifespan reconnects to the live daemon via the PID file — correct.
- `_daemon_exec_cmd` reverts to `"claude --dangerously-skip-permissions"` — wrong.
- `_daemon_state.restart_policy` reverts to `"no-restart"` — crash recovery silently disabled.

The ticket says "restart-on-crash policy successfully relaunches the daemon" — this fails after a supervisor restart if custom parameters were used.

**Recommended fix** — persist `exec_cmd` and `restart_policy` in the PID file and reload them in lifespan:

```python
# _write_pid_file: add exec_cmd and restart_policy to JSON
# lifespan: restore _daemon_exec_cmd and _daemon_state.restart_policy from file
```

This is a 3-line change to both `_write_pid_file` and the lifespan startup block.

---

### 4. Minor Observations

**a. No restart backoff or max-retry cap** (main.py:214–226)  
If the daemon binary crashes immediately on start (bad config, missing dependency), the monitor will loop respawning it every 5 seconds forever. Not a ticket requirement, but worth noting as a follow-up.

**b. `_check_and_maybe_restart()` blocks the event loop** (main.py:229–232)  
This sync function is called directly from async `_monitor_daemon()`. It calls `_is_alive()` (fast syscall) and potentially `_spawn_daemon()` (file I/O, `Popen`). For a single-process supervisor with no concurrent load, this is benign in practice, but technically incorrect asyncio usage.

**c. `supervisor_available` and `supervisor_url` fields on `DaemonStatus` are never populated** (schemas.py:18–19, daemon_manager.py:231–267)  
These two fields exist in the schema but `get_status()` never sets them. They are always `None`. Either populate them or remove them to avoid dead schema surface.

**d. "Restarting…" badge has no test coverage** (DaemonPage.jsx:165–169, DaemonPage.test.jsx)  
The badge is correct: it appears when `restart_policy="restart-on-crash" && exit_unexpected && !running`. No test exercises this. Low-risk since the CrashBanner test covers the surrounding logic.

---

### 5. Code Quality

- `services/supervisor/main.py` is clean, well-factored, and all state mutations are in one place.
- PID file format is stable (JSON, versioned-safe).
- `_voluntary_stop` flag is straightforward and correctly reset after use.
- The four-path delegation in `daemon_manager.start()` is explicit and well-documented.
- Tests cover all acceptance criteria behaviors with proper monkeypatching.

---

### Decision

The two issues raised in §2 and §3 are real correctness gaps. Issue §2 (stop/start race) is directly observable from the dashboard. Issue §3 (state lost on supervisor restart) violates the restart-on-crash acceptance criterion in a specific but realistic scenario.

Both fixes are small and low-risk. The implementation should address them before merge.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T131/reviews/implementation-review.md
- generated at: 2026-05-21T22:27:42Z

---

Now I have all I need. Let me write the structured review.

---

## Review — T131: Supervisor Daemon Persistence and Unexpected Exit Handling

### Summary

The implementation is complete, cohesive, and covers all seven acceptance criteria. The supervisor architecture is well-separated: daemon state lives in the supervisor process, the control-API delegates cleanly, and the dashboard exposes crash metadata. Tests cover the critical paths.

Below I document one notable correctness gap, a durability limitation, and minor observations.

---

### 1. Correctness Relative to Ticket Requirements

| Acceptance criterion | Status | Notes |
|---|---|---|
| Daemon survives after API request | ✅ | `start_new_session=True` on all Popen calls |
| Unexpected exits detected and reported | ✅ | Monitor polls `_is_alive()` every 5 s, sets `exit_unexpected` |
| Dashboard shows crash state | ✅ | `CrashBanner` with exit code, time, restart count |
| Restart-on-crash relaunches | ✅ | `_check_and_maybe_restart()` + `_spawn_daemon()` |
| Stale PID recovered automatically | ✅ | Both lifespan startup and `/daemon/status` handle it |
| Supervisor status API exposes runtime/crash info | ✅ | 10-field response from `GET /daemon/status` |
| Existing daemon workflows preserved | ✅ | All four start paths remain functional |

---

### 2. Notable Issue — `_daemon_state.pid` not cleared in `daemon_stop()` (main.py:400–416)

After `daemon_stop()` sends SIGTERM, `_daemon_state.pid` retains the old PID. The PID file is removed but the in-memory state is not updated until the monitor's next 5-second cycle.

**Consequence:** if a caller invokes `POST /daemon/start` immediately after `POST /daemon/stop`, `daemon_start()` reads `_daemon_state.pid` (old PID), calls `_is_alive(pid)` while the process is still dying, and returns `{"ok": False, "error": "already_running"}`. This window is typically milliseconds but it is observable from the dashboard (Stop → immediate Start).

**Recommended fix** — clear `_daemon_state.pid` in `daemon_stop()` before returning:

```python
os.kill(pid, signal.SIGTERM)
_daemon_state.pid = None  # add this line
_daemon_state.started_at = None  # and this
_remove_pid_file()
```

This matches the semantics (`_daemon_proc` is not cleared either, but the monitor handles that).

---

### 3. Durability Limitation — `_daemon_exec_cmd` and `restart_policy` lost on supervisor restart (main.py:237–257)

If the supervisor process itself restarts (crash or redeploy) while a daemon is running with a non-default `exec_cmd` and `restart_policy="restart-on-crash"`:

- The lifespan reconnects to the live daemon via the PID file — correct.
- `_daemon_exec_cmd` reverts to `"claude --dangerously-skip-permissions"` — wrong.
- `_daemon_state.restart_policy` reverts to `"no-restart"` — crash recovery silently disabled.

The ticket says "restart-on-crash policy successfully relaunches the daemon" — this fails after a supervisor restart if custom parameters were used.

**Recommended fix** — persist `exec_cmd` and `restart_policy` in the PID file and reload them in lifespan:

```python
# _write_pid_file: add exec_cmd and restart_policy to JSON
# lifespan: restore _daemon_exec_cmd and _daemon_state.restart_policy from file
```

This is a 3-line change to both `_write_pid_file` and the lifespan startup block.

---

### 4. Minor Observations

**a. No restart backoff or max-retry cap** (main.py:214–226)  
If the daemon binary crashes immediately on start (bad config, missing dependency), the monitor will loop respawning it every 5 seconds forever. Not a ticket requirement, but worth noting as a follow-up.

**b. `_check_and_maybe_restart()` blocks the event loop** (main.py:229–232)  
This sync function is called directly from async `_monitor_daemon()`. It calls `_is_alive()` (fast syscall) and potentially `_spawn_daemon()` (file I/O, `Popen`). For a single-process supervisor with no concurrent load, this is benign in practice, but technically incorrect asyncio usage.

**c. `supervisor_available` and `supervisor_url` fields on `DaemonStatus` are never populated** (schemas.py:18–19, daemon_manager.py:231–267)  
These two fields exist in the schema but `get_status()` never sets them. They are always `None`. Either populate them or remove them to avoid dead schema surface.

**d. "Restarting…" badge has no test coverage** (DaemonPage.jsx:165–169, DaemonPage.test.jsx)  
The badge is correct: it appears when `restart_policy="restart-on-crash" && exit_unexpected && !running`. No test exercises this. Low-risk since the CrashBanner test covers the surrounding logic.

---

### 5. Code Quality

- `services/supervisor/main.py` is clean, well-factored, and all state mutations are in one place.
- PID file format is stable (JSON, versioned-safe).
- `_voluntary_stop` flag is straightforward and correctly reset after use.
- The four-path delegation in `daemon_manager.start()` is explicit and well-documented.
- Tests cover all acceptance criteria behaviors with proper monkeypatching.

---

### Decision

The two issues raised in §2 and §3 are real correctness gaps. Issue §2 (stop/start race) is directly observable from the dashboard. Issue §3 (state lost on supervisor restart) violates the restart-on-crash acceptance criterion in a specific but realistic scenario.

Both fixes are small and low-risk. The implementation should address them before merge.

IMPLEMENTATION_FIX_REQUIRED