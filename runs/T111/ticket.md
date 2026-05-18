# T111 — T111 — SQLite runtime state store for daemon, intake, workers and board

**Source**: GitHub Issue #58

## Description

# T111 — SQLite runtime state store for daemon, intake, workers and board

## Contexte

Le runtime actuel utilise trop Git et `runs/` comme base vivante :

- `runs/.issue-intake.json`
- `runs/workers.json`
- `runs/TXXX/state.json`
- locks
- retry state
- logs/runtime artifacts
- board state

Avec les worktrees, cela crée des problèmes récurrents :

- commits d’intake parasites sur `main`
- `main` local diverge de `origin/main`
- pull `--ff-only` impossible
- dashboard qui ne voit pas les tickets tant que les artefacts ne sont pas commit/push
- state Git local différent du state worktree
- workers invisibles ou fantômes
- dirty tree qui bloque le daemon
- intake qui pollue l’historique Git

Exemple observé :

```text
T109: intake — update issue index
```

commit créé localement sur `main`, sans valeur produit/code, bloquant ensuite `git pull --ff-only origin main`.

---

## Objectif

Introduire une base SQLite locale pour stocker l’état runtime vivant.

Git/GitHub restent source de vérité pour :

- code
- branches ticket
- PR
- issues GitHub
- artefacts auditables importants

SQLite devient source de vérité locale pour :

- intake
- état runtime courant
- workers
- locks
- retry/cooldown
- board
- transitions
- erreurs runtime
- health/status

---

## Principe d’architecture

Avant :

```text
Git + runs/ = code + runtime state + audit trail
```

Après :

```text
Git/GitHub = code + issues + PR + audit artifacts
SQLite = runtime state vivant
runs/ = artefacts/audit trail exportables, pas source runtime principale
```

---

## Données à migrer vers SQLite

### 1. Issue intake

Remplacer progressivement :

```text
runs/.issue-intake.json
```

par une table :

```sql
issue_intake(
  issue_number INTEGER PRIMARY KEY,
  ticket_id TEXT NOT NULL,
  branch TEXT,
  status TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_error TEXT
)
```

Objectif : ne plus committer l’index intake sur `main`.

---

### 2. Ticket runtime state

Ajouter :

```sql
ticket_runtime(
  ticket_id TEXT PRIMARY KEY,
  issue_number INTEGER,
  branch TEXT,
  state TEXT NOT NULL,
  run_dir TEXT,
  worktree_path TEXT,
  daemon_archived INTEGER DEFAULT 0,
  pr_number INTEGER,
  pr_state TEXT,
  last_transition TEXT,
  last_error TEXT,
  updated_at TEXT NOT NULL
)
```

Le `state.json` peut encore exister comme artefact, mais le daemon/board doivent lire SQLite en priorité.

---

### 3. Workers

Remplacer progressivement :

```text
runs/workers.json
```

par :

```sql
workers(
  ticket_id TEXT PRIMARY KEY,
  pid INTEGER,
  branch TEXT,
  worktree_path TEXT,
  status TEXT NOT NULL,
  started_at TEXT,
  heartbeat_at TEXT,
  updated_at TEXT NOT NULL
)
```

---

### 4. Locks

Ajouter :

```sql
runtime_locks(
  lock_name TEXT PRIMARY KEY,
  ticket_id TEXT,
  pid INTEGER,
  acquired_at TEXT NOT NULL,
  expires_at TEXT,
  metadata_json TEXT
)
```

Objectif : éviter les locks fichiers fragiles ou orphelins.

---

### 5. Retry / cooldown

Ajouter :

```sql
retry_state(
  ticket_id TEXT PRIMARY KEY,
  failure_class TEXT,
  retry_count INTEGER DEFAULT 0,
  cooldown_until TEXT,
  stopped INTEGER DEFAULT 0,
  stop_reason TEXT,
  updated_at TEXT NOT NULL
)
```

---

### 6. Runtime events / timeline

Ajouter :

```sql
runtime_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id TEXT,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL
)
```

Le dashboard peut afficher la timeline depuis SQLite sans dépendre uniquement de `runtime.log`.

---

### 7. Project/board state minimal

Ajouter éventuellement :

```sql
runtime_metadata(
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
)
```

Pour stocker :

- dernier scan daemon
- version runtime
- dernier pull main
- health global
- préférences dashboard légères

---

## Travail demandé

### 1. Créer un module SQLite runtime

Créer :

```text
tools/agent_runner/runtime_db.py
```

Fonctions minimales :

```python
init_runtime_db(db_path)
record_issue_intake(...)
get_issue_intake(issue_number)
upsert_ticket_runtime(...)
get_ticket_runtime(ticket_id)
list_ticket_runtime()
upsert_worker(...)
remove_worker(ticket_id)
list_workers()
append_runtime_event(...)
```

---

### 2. Ajouter une migration/init automatique

Au démarrage du daemon/control-api :

```text
si DB absente → créer schéma
si DB présente → vérifier schéma version
```

Chemin par défaut proposé :

```text
.runtime/ai-dev-factory.sqlite
```

À gitignore :

```gitignore
.runtime/
*.sqlite
*.sqlite-wal
*.sqlite-shm
```

---

### 3. Modifier issue intake

Le daemon doit :

- vérifier l’intake dans SQLite
- ne plus dépendre uniquement de `.issue-intake.json`
- ne plus committer l’index intake sur `main`
- créer branche/worktree comme avant
- enregistrer le résultat dans SQLite

Pendant transition, `.issue-intake.json` peut rester en fallback lecture seule.

---

### 4. Modifier board/control-api

Le dashboard doit pouvoir lire :

- tickets runtime depuis SQLite
- workers depuis SQLite
- événements runtime depuis SQLite

Fallback temporaire autorisé :

```text
SQLite absent → lire runs/ legacy
```

---

### 5. Modifier workers registry

Le daemon doit écrire les workers dans SQLite.

`runs/workers.json` peut rester temporairement en export/debug, mais ne doit plus être la source primaire.

---

### 6. Modifier retry/cooldown

Migrer `retry-state.json` vers SQLite progressivement.

Fallback legacy accepté en V1.

---

### 7. Éviter tout commit runtime parasite sur main

Supprimer ou désactiver les commits automatiques de :

- `.issue-intake.json`
- `workers.json`
- locks
- retry state
- state runtime purement local

Les commits Git doivent rester réservés aux artefacts ticket auditables et aux modifications code.

---

## Contraintes

- Migration progressive, ne pas tout casser d’un coup
- Compatible tickets existants dans `runs/TXXX`
- Compatible worktrees existants
- Pas de dépendance externe autre que SQLite stdlib Python
- SQLite doit rester local et gitignored
- GitHub issues restent la source de vérité des demandes produit
- Git reste source de vérité code/PR

---

## Tests

Ajouter :

```text
tests/test_runtime_db.py
```

Cas minimum :

- init DB
- insert/update issue intake
- duplicate intake avoided
- ticket runtime upsert/list
- worker register/unregister
- runtime events append/list
- DB survives process restart

Ajouter aussi des tests daemon :

- intake issue uses SQLite instead of `.issue-intake.json`
- no commit on main for intake index
- board can list ticket from SQLite
- worker visible from SQLite

---

## Critères d’acceptation

- le daemon peut ingérer une issue sans créer de commit d’intake sur `main`
- `main` local ne diverge plus à cause de runtime state
- le board voit les tickets depuis SQLite
- les workers sont visibles depuis SQLite
- les tickets existants `runs/TXXX` restent lisibles en fallback
- `.issue-intake.json` n’est plus la source primaire
- `runs/workers.json` n’est plus la source primaire
- SQLite est gitignored
- tests runtime DB passent

---

## Hors scope V1

- multi-projets complet
- synchronisation cloud de la DB
- migration historique exhaustive de tous les anciens runs
- UI avancée d’administration DB
- suppression totale de `runs/`

---

## Pourquoi maintenant

T104/T105/T109 ont stabilisé les worktrees et checkpoints, mais ont aussi révélé que Git ne doit pas porter l’état vivant du daemon.

T111 doit stabiliser la base runtime avant de reprendre :

- T107 guardian
- T108 multi-project onboarding
- T110 UX/dashboard
