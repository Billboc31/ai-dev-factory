# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T159/reviews/implementation-review.md
- generated at: 2026-05-29T09:15:49Z

---

---

## PR Review — T159: Harden runtime SQLite architecture and degraded-mode recovery

---

## Résumé

L'implémentation couvre la majorité des objectifs du ticket : hardening SQLite (WAL, busy_timeout, synchronous=NORMAL), integrity check au démarrage, quarantaine automatique des DB corrompues, singleton guard daemon, et fallback filesystem dans le board service. Les API backend exposent correctement un flag `degraded`. Cependant, le critère d'acceptation le plus visible — l'affichage d'un avertissement dégradé dans l'UI — est absent.

---

## Vérifications effectuées

- Diff complet branche vs main sur tous les fichiers hors `runs/`
- Lecture de `runtime_db.py`, `run_daemon.py`, `board_service.py`, `runtime_dashboard.py`, `schemas.py`, `test_runtime_db.py`
- Vérification de la logique `get_db_path()` (global path, worktree safety)
- Vérification des composants frontend (aucun changement)
- Vérification de la logique `_try_load_runtime_db` dans le health endpoint
- Vérification des tests

---

## Points validés

**SQLite hardening pragmas** (`runtime_db.py:116-118`)
- `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `PRAGMA synchronous=NORMAL` appliqués dans `init_runtime_db()` et `_connect()`. Cohérent et complet.

**Integrity check + quarantaine** (`runtime_db.py:119-185`)
- `check_and_recover_db()` sérialisée via `fcntl.LOCK_EX` sur un `.recovery.lock`
- Flux correct : check → quarantine (rename avec timestamp ISO) → tentative `.recover` CLI → recreate vide
- `check_and_recover_db()` appelée avant `init_runtime_db()` dans `_ensure_db()` du daemon

**Singleton guard daemon** (`run_daemon.py:136-166`)
- `_acquire_daemon_singleton()` via `fcntl.LOCK_EX | LOCK_NB` — retourne `False` immédiatement si verrouillé
- File handle tenu ouvert pour la durée de vie du processus (`_SINGLETON_LOCK_FH`)
- Appelé tôt dans `main()` avant tout accès SQLite

**Global DB path** (`runtime_db.py:73-102`)
- `get_db_path()` utilise `AI_DEV_FACTORY_RUNTIME_ROOT` en priorité (Docker/runtime)
- Fallback dev via `git rev-parse --git-common-dir` — tous les worktrees partagent donc la même DB

**Filesystem fallback** (`board_service.py:127-240`)
- Les trois requêtes SQLite du board (workers, ticket states, issue index) sont maintenant enveloppées dans des `try/except` avec fallback vers les registres JSON existants
- Flag `degraded` propagé dans `BoardResponse`

**Tests** (`test_runtime_db.py:166-253`)
- 4 nouveaux tests couvrant : DB saine, DB corrompue + quarantaine, sérialisation concurrente (4 threads), vérification des pragmas

---

## Problèmes détectés

### BLOQUANT — Frontend : aucun affichage de l'avertissement dégradé

**Critère d'acceptation du ticket** :
> Users receive explicit degraded-mode warnings
> Runtime UI should display: "SQLite runtime database unavailable / Showing filesystem-derived runtime state"

L'API backend expose désormais `degraded: bool` dans `BoardResponse` et `sqlite_degraded: bool` dans `RuntimeHealth`, mais **aucun composant frontend ne consomme ces champs**. `RuntimeHealthPanel.jsx` affiche `supervisor_status`, `active_jobs`, `stale_pid_files`, `stale_locks` — et rien d'autre. La page Board ne montre aucune bannière de dégradation.

L'utilisateur ne voit jamais l'avertissement. Ce critère d'acceptation n'est pas satisfait.

**Correction attendue** : dans `RuntimeHealthPanel.jsx`, afficher une bannière conditionnelle si `health.sqlite_degraded === true`. Dans la page Board (ou le composant qui affiche les colonnes), afficher un avertissement si `board.degraded === true`.

---

### MINEUR — `_try_load_runtime_db` ne sonde pas réellement la DB dans le health endpoint

`get_runtime_health()` appelle `_try_load_runtime_db()` pour détecter la dégradation. Mais cette fonction ne fait que charger le module Python et vérifier si le fichier DB existe — elle ne tente aucune requête SQLite. Pour une DB corrompue (mais existante), elle retourne `(mod, db_path, False)` — soit `sqlite_degraded=False` dans la réponse health.

L'endpoint `/health` rapporterait donc `sqlite_degraded: false` même si la DB est corrompue. Le board service, lui, détecte bien la corruption (lors des requêtes réelles), mais la route health est trompeuse.

**Correction suggérée** : dans `_try_load_runtime_db`, tenter une requête minimale (`SELECT 1`) pour valider l'accès réel à la DB, et retourner `degraded=True` en cas d'échec.

---

### MINEUR — Code dupliqué entre `_load_runtime_db` et `_try_load_runtime_db`

Les deux fonctions (`board_service.py:67-82` et `board_service.py:85-103`) partagent un bloc identique de 8 lignes (chargement du module, spec, exec_module, get_db_path). La seule différence est la valeur de retour (2-tuple vs 3-tuple avec `degraded`). `_load_runtime_db` n'est plus utilisée dans `get_board()` (remplacée par `_try_load_runtime_db`), ce qui rend cette duplication inutile.

**Correction suggérée** : supprimer `_load_runtime_db` ou faire en sorte que `_load_runtime_db` délègue à `_try_load_runtime_db`.

---

### MINEUR — Pas de nettoyage des DB legacy dans les worktrees

Le ticket demande explicitement :
> Audit and remove accidental DB creation in `worktrees/*/.runtime/` and `clones/*/.runtime/`

Aucun script ni nettoyage automatique n'est implémenté. Les DB existantes dans des emplacements locaux ne sont pas migrées.

---

### OBSERVATION — `print()` au lieu de logging structuré dans `runtime_db.py`

Les messages de recovery utilisent `print(f"...", flush=True)` (`runtime_db.py:152-184`). Cohérent avec le reste du module, mais si le projet évolue vers du logging structuré, ces messages ne seront pas capturés.

---

### OBSERVATION — Pas de rotation des fichiers quarantaine

Les fichiers `.corrupt.<timestamp>` ne sont jamais purgés. Sur un système avec corruptions fréquentes, cela peut consommer de l'espace disque. Acceptable pour l'instant mais à documenter.

---

## Risques éventuels

- **Faux sentiment de sécurité** : le health endpoint peut reporter `sqlite_degraded: false` pendant que la DB est en réalité inaccessible, ce qui pourrait induire en erreur un monitoring automatisé.
- **Worktrees legacy** : sans nettoyage des DB locales existantes, certains worktrees peuvent continuer à pointer vers une DB locale stale pendant quelque temps (mitigé par le fait que `get_db_path()` résout désormais via `git-common-dir`).

---

## Décision

REQUEST_CHANGES

---

## Actions demandées

1. **[BLOQUANT]** Implémenter l'affichage dégradé dans le frontend :
   - `RuntimeHealthPanel.jsx` : bannière si `health.sqlite_degraded === true` ("SQLite runtime database unavailable")
   - Page Board ou composant colonnes : bannière si `board.degraded === true` ("Showing filesystem-derived runtime state")

2. **[MINEUR]** Corriger `_try_load_runtime_db` pour sonder réellement la DB (ex. `SELECT 1`) avant de retourner `degraded=False`.

3. **[MINEUR]** Supprimer ou refactoriser `_load_runtime_db` pour éliminer la duplication avec `_try_load_runtime_db`.

---

IMPLEMENTATION_FIX_REQUIRED
