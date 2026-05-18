# PR Review — T111 SQLite Runtime State Store

## Résumé

T111 introduit un module SQLite (`runtime_db.py`) pour remplacer l'état runtime Git. L'objectif principal — éliminer les commits parasites d'intake sur `main` — est atteint. L'infrastructure SQLite est en place et fonctionnelle. Cependant, deux lacunes méritent correction avant merge : le board service ne lit pas l'état ticket depuis `ticket_runtime` (table populée mais jamais consommée), et la fonction `_commit_after_intake` reste en code mort sans justification.

---

## Vérifications effectuées

- Lecture complète de `tools/agent_runner/runtime_db.py` (272 lignes)
- Lecture complète de `tests/test_runtime_db.py` (182 lignes)
- Lecture des points d'intégration du daemon (`run_daemon.py` lignes 50-61, 205-254, 988-1007, 1097-1169, 1239-1265)
- Lecture des modifications intake (`run_issue_intake.py` lignes 25-30, 152-161, 233)
- Lecture de l'intégration board (`services/control_api/services/board_service.py` lignes 67-176)
- Vérification `.gitignore` (entrées `.runtime/`, `*.sqlite*`, `runs/.issue-intake.json`, `runs/workers.json`)
- Vérification tests d'intégration daemon (`tests/test_daemon_issue_polling.py` lignes 371-396)
- Vérification que `_commit_after_intake` n'est plus appelé (une seule occurrence : la définition à la ligne 444)

---

## Points validés

- **Objectif core atteint** : `_commit_after_intake` n'est plus appelé dans `poll_github_issues`. `main` ne diverge plus pour cause d'intake. Critère d'acceptation principal rempli.
- **Module SQLite correct** : stdlib uniquement, WAL mode activé, `CREATE TABLE IF NOT EXISTS` idempotent, `ON CONFLICT ... DO UPDATE` pour les upserts, `sqlite3.Row` factory pour accès dict-like.
- **Résolution DB worktree-aware** : `get_db_path()` utilise `git rev-parse --git-common-dir` — tous les worktrees partagent le même `.runtime/ai-dev-factory.sqlite`. Approche architecturalement correcte.
- **Stratégie dual-write** : JSON local (gitignored) comme copie de travail daemon + SQLite comme source secondaire pour le board. Compatibilité backward préservée.
- **gitignore correct** : `.runtime/`, `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`, `runs/.issue-intake.json`, `runs/workers.json` correctement ignorés.
- **Tests runtime_db** : 15 tests couvrant init, CRUD complet pour les 4 tables, idempotence, persistance après reconnexion.
- **Nettoyage workers fantômes** : `_cleanup_stale_workers` nettoie à la fois `workers.json` et SQLite au démarrage du daemon.
- **Board workers depuis SQLite** : `get_board()` lit les workers depuis SQLite en priorité (fallback JSON). ✅
- **Board issue index depuis SQLite** : backlog lit `issue_intake` depuis SQLite en priorité (fallback JSON). ✅
- **Test d'intégration daemon** : `test_poll_github_issues_does_not_commit_after_intake_on_success` vérifie explicitement que `_commit_after_intake` n'est pas appelé.

---

## Problèmes détectés

### Bloquant — Acceptance criterion non rempli

**B1 — Board ne lit pas `ticket_runtime` pour l'état kanban**

`board_service.py` lignes 136-162 : le board lit toujours les `state.json` depuis le filesystem pour le placement kanban (colonnes INIT/PLAN_APPROVED/etc.). La table `ticket_runtime` est correctement populée par le daemon (lignes 1251-1265 de `run_daemon.py`) mais jamais lue par le board service pour déterminer l'état d'un ticket.

Le critère d'acceptation stipule : *"le board voit les tickets depuis SQLite"*. Actuellement, seuls les workers et l'issue index sont lus depuis SQLite. L'état des tickets eux-mêmes (placement dans les colonnes kanban) reste dépendant des `state.json` filesystem.

**Impact** : pour un ticket dont le `state.json` est dans un worktree sans worker actif (ex. : en attente de review humaine), le board peut ne pas voir le bon état si le fichier n'est pas accessible depuis le répertoire principal.

**Correction attendue** : dans `get_board()`, si SQLite est disponible et que `ticket_runtime` contient un enregistrement pour un ticket, utiliser son champ `state` comme source primaire au lieu de lire `state_data` depuis `state.json`.

---

### Qualité — Non bloquant mais nécessite correction avant merge

**Q1 — Dead code `_commit_after_intake` (run_daemon.py:444)**

La fonction existe mais n'est jamais appelée. Sa présence est source de confusion : un lecteur peut croire que l'ancien comportement est encore actif quelque part, ou être tenté de la réintroduire. Elle doit être supprimée. Son histoire est préservée dans git.

**Q2 — `_rdb_get_db_path()` appelé à répétition par subprocess**

La résolution du chemin DB (`git rev-parse --git-common-dir`) est appelée via subprocess à chaque `_register_worker`, `_unregister_worker`, `save_issue_index`, et à chaque cycle de `run_once`. Cela représente plusieurs appels subprocess par tick de daemon pour une valeur qui ne change pas.

**Correction** : cacher `db_path` à l'initialisation du daemon (une fois au démarrage) et le passer en argument ou le stocker dans une variable module-level.

**Q3 — `_rdb_init` appelé à répétition**

`init_runtime_db` est appelé à chaque `save_issue_index`, chaque `_register_worker`, et à chaque cycle dans `run_once`. L'opération est idempotente mais inefficace.

**Correction** : appeler `init_runtime_db` une seule fois au démarrage du daemon.

**Q4 — Exceptions SQLite swallowées silencieusement sans log**

Pattern `except Exception: pass` utilisé dans tous les points d'écriture SQLite (daemon et intake). L'intention "non-fatal" est documentée mais les échecs silencieux rendent le debugging difficile en production.

**Correction** : remplacer `pass` par `_log(f"SQLite write failed: {exc}")` (ou équivalent) pour tracer les dégradations.

**Q5 — `.gitignore` avec entrées dupliquées**

`runs/daemon.log` apparaît 4 fois, `runs/*/runtime.log` apparaît 3 fois. Pas de bug fonctionnel mais c'est du bruit.

---

## Risques éventuels

**R1 — SQL injection surface dans `upsert_ticket_runtime`**

`runtime_db.py` lignes 158-174 : le `set_clause` et la liste de colonnes INSERT sont construits par f-string depuis les clés de `**fields`. Tous les appelants sont internes et contrôlés, donc le risque réel est faible aujourd'hui. Mais si l'API est exposée à des données externes (ex. : métadonnées issues GitHub injected in ticket_id), cela devient une surface d'injection. À surveiller.

**R2 — Tables manquantes vs ticket**

Le ticket définit 7 tables (`issue_intake`, `ticket_runtime`, `workers`, `runtime_events`, `runtime_locks`, `retry_state`, `runtime_metadata`). Seules 4 sont implémentées. Les 3 tables manquantes (`runtime_locks`, `retry_state`, `runtime_metadata`) ne font pas partie des critères d'acceptation et sont acceptables en V1 — mais les mécanismes de locks et retry continuent à utiliser des fichiers, maintenant gitignorés mais non migrés vers SQLite.

---

## Décision

- REQUEST_CHANGES

**B1 est bloquant** : le critère d'acceptation "le board voit les tickets depuis SQLite" n'est pas pleinement rempli. La table `ticket_runtime` est populée mais jamais consommée par le board. Les issues Q1 à Q4 sont de qualité mais devraient être traitées dans ce même ticket pour éviter de les laisser s'accumuler.

---

## Actions demandées

1. **[Bloquant]** Dans `board_service.py`, `get_board()` : lire l'état ticket depuis `ticket_runtime` SQLite quand disponible, plutôt que (ou en complément de) `state.json`. Au minimum, si `rdb` est disponible, utiliser `rdb.list_ticket_runtime(db_path)` pour construire `ticket_dirs` et déterminer l'état kanban.
2. **[Qualité]** Supprimer la fonction `_commit_after_intake` (run_daemon.py:444-457). Elle est morte, sa suppression est propre.
3. **[Qualité]** Cacher `db_path = _rdb_get_db_path()` une fois au démarrage du daemon (`main()`) et le transmettre plutôt que de le recalculer via subprocess à chaque opération.
4. **[Qualité]** Appeler `_rdb_init(db_path)` une seule fois au démarrage, pas dans chaque helper.
5. **[Qualité]** Remplacer les `except Exception: pass` dans les blocs SQLite par un `_log(...)` minimal pour tracer les dégradations.

IMPLEMENTATION_FIX_REQUIRED
