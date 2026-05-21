# PR Review — T121 — Reconnect dashboard controls to canonical runtime daemon

## Résumé

L'implémentation relie correctement les chemins du daemon manager (PID, log, worktrees dir) au résolveur canonique `runtime_resolver`, et expose un nouvel endpoint `POST /daemon/sync-main` avec son bouton UI. Le changement est minimal (4 fichiers sources, ~35 lignes), cohérent avec les conventions existantes, et conforme au plan approuvé.

## Vérifications effectuées

- Lecture du diff complet `main...HEAD` sur les 4 fichiers source modifiés
- Vérification de `runtime_resolver.py` (fonctions importées et comportement effectif)
- Vérification de la cohérence avec les acceptance criteria du plan
- Lecture du plan (`runs/T121/plan.md`) et de l'output d'implémentation
- Vérification de l'intégration frontend (`daemonApi.syncMain` utilisable via import wildcard existant)

## Points validés

### `daemon_manager.py`

- `_pid_path()` → `resolve_runs_dir(project_root) / _PID_FILENAME` ✓
- `_log_path()` → `resolve_logs_dir(project_root) / _LOG_FILENAME` ✓
- `_current_ticket()` → scanne `resolve_runs_dir(project_root)` ✓
- `--worktrees-dir` → `resolve_worktrees_dir(project_root)` ✓
- `log.parent.mkdir(parents=True, exist_ok=True)` avant ouverture du log ✓
- `sync_main()` : subprocess avec liste d'args (pas de shell injection), timeout 60s, gestion OSError et TimeoutExpired, retourne `ActionResult` conforme ✓

### `routes/daemon.py`

- Endpoint `POST /daemon/sync-main` ajouté, utilise `_root(request)` comme les autres routes ✓
- `response_model=ActionResult` déclaré ✓

### Frontend

- `export const syncMain = () => client.post('/daemon/sync-main')` ajouté dans `daemon.js` ✓
- `ActionButton label="Sync Main" variant="secondary" onSuccess={fetchStatus}` ajouté dans `DaemonPage.jsx` ✓
- L'import wildcard `daemonApi` déjà en place dans la page — `daemonApi.syncMain` sera résolu sans modification supplémentaire ✓

### Sécurité

- Aucun shell=True : `subprocess.run(["git", "fetch", "origin", "main"], ...)` — pas de risque d'injection ✓
- Timeout 60s — pas de process bloquant ✓
- Aucun secret loggué ✓
- Opération fetch uniquement (read-only sur l'état de travail) — pas de modification de branche implicite ✓

### Comportement dual-mode

- Avec `AI_DEV_FACTORY_RUNTIME_ROOT` → chemins canoniques (`$RUNTIME_ROOT/runs`, `/logs`, `/worktrees`) ✓
- Sans env var → chemins projet relatifs (compatibilité locale préservée) ✓

## Problèmes détectés

### Bloquants

Aucun.

### Observations mineures (non bloquantes)

1. **Absence de tests** — Aucun test unitaire pour `sync_main()` ni pour le nouvel endpoint. Acceptable compte tenu du scope, mais un test mocké du subprocess aurait été bienvenu.

2. **`resolve_ticket_cwd()` non corrigé** — Dans `runtime_resolver.py` ligne 92, `runs_dir = project_root / "runs"` est encore hardcodé (n'utilise pas `resolve_runs_dir`). Ce n'est pas dans le scope de ce ticket, mais c'est une incohérence à noter pour un futur ticket.

3. **Scope gap ticket ↔ plan** — Le ticket original demandait retry/approve/abort/archive actions et la visualisation des logs live. Le plan approuvé a explicitement exclu ces éléments. L'implémentation est correcte par rapport au plan, mais ces fonctionnalités restent à traiter dans un ticket distinct.

4. **git fetch sans auth check** — Si les credentials SSH/HTTPS ne sont pas configurés, l'erreur sera propagée correctement via `result.stderr`, mais l'UX pourrait bénéficier d'un message plus explicatif. Non bloquant.

## Risques éventuels

- Aucun risque de régression identifié : les changements sur `_pid_path`, `_log_path`, `_current_ticket` et `--worktrees-dir` n'affectent que le résultat des chemins, pas la logique de contrôle. En l'absence de `AI_DEV_FACTORY_RUNTIME_ROOT`, le comportement est identique à avant.

## Décision

IMPLEMENTATION_APPROVED — l'implémentation est fidèle au plan approuvé, les critères d'acceptance du plan sont tous satisfaits, le code est propre, minimal, et sans régression identifiable.

## Actions demandées

Aucune action bloquante. Pour le futur :
- Ouvrir un ticket pour corriger `resolve_ticket_cwd()` (ligne 92 de `runtime_resolver.py`)
- Ouvrir un ticket pour couvrir les actions retry/approve/abort manquantes dans le dashboard

IMPLEMENTATION_APPROVED
