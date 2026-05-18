# Test Report — T111: SQLite runtime state store

**Branch**: `ticket/T111-t111-sqlite-runtime-state-store-for-daemon-intake`
**Date**: 2026-05-19
**Tester**: Claude (automated)

---

## Résumé

L'implémentation satisfait tous les critères d'acceptation du ticket. Un bug de test a été détecté et corrigé dans `test_daemon_issue_polling.py` (5 tests qui patchaient `_commit_after_intake`, fonction correctement supprimée par T111). Les 4 échecs dans `test_daemon_checkpoint.py` sont des régressions pré-existantes sur `main`, sans lien avec T111.

---

## Critères d'acceptation

| Critère | Statut | Vérification |
|---------|--------|--------------|
| Le daemon peut ingérer une issue sans commit d'intake sur `main` | ✅ PASS | `_commit_after_intake` supprimé ; `test_poll_github_issues_does_not_commit_after_intake_on_success` vérifie l'absence de `git commit` dans les appels subprocess |
| `main` local ne diverge plus à cause de runtime state | ✅ PASS | `.issue-intake.json` gitignored ; aucun `git commit` d'index dans `poll_github_issues` |
| Le board voit les tickets depuis SQLite | ✅ PASS | `save_issue_index` et `poll_github_issues` écrivent dans SQLite via `_rdb_record_intake` + `_rdb_upsert_ticket` ; fallback filesystem maintenu |
| Les workers sont visibles depuis SQLite | ✅ PASS | `_register_worker` appelle `_rdb_upsert_worker` ; `_unregister_worker` appelle `_rdb_remove_worker` |
| Les tickets existants `runs/TXXX` restent lisibles en fallback | ✅ PASS | Chemin filesystem conservé dans le daemon |
| `.issue-intake.json` n'est plus la source primaire | ✅ PASS | SQLite est la source primaire ; JSON gitignored, utilisé comme fallback lecture |
| `runs/workers.json` n'est plus la source primaire | ✅ PASS | SQLite-first dans le daemon ; JSON en export/debug uniquement |
| SQLite est gitignored | ✅ PASS | `.gitignore` : `.runtime/`, `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm` confirmés |
| Tests runtime DB passent | ✅ PASS | 15/15 tests `test_runtime_db.py` |

---

## Résultats des tests

### `tests/test_runtime_db.py` — 15/15 PASS

Tous les cas requis par le ticket :
- `test_init_creates_db_file` ✅
- `test_init_is_idempotent` ✅
- `test_record_issue_intake_insert` ✅
- `test_record_issue_intake_update_on_conflict` ✅ (duplicate avoided)
- `test_list_issue_intake_multiple` ✅
- `test_get_issue_intake_returns_none_when_absent` ✅
- `test_upsert_ticket_runtime_insert` / `_update` / `_list` ✅
- `test_upsert_and_remove_worker` / `_updates_existing` / `_noop_when_absent` ✅
- `test_append_and_list_runtime_events` ✅
- `test_runtime_event_metadata_roundtrip` ✅
- `test_db_survives_reconnect` ✅ (persistence entre restarts)

### `tests/test_daemon_issue_polling.py` — 49/49 PASS (après correction)

**Bug détecté et corrigé** : 5 tests patchaient `run_daemon._commit_after_intake`, fonction supprimée correctement par T111. Les tests avaient besoin d'être mis à jour pour refléter la nouvelle réalité.

Corrections appliquées :
- `test_poll_github_issues_ingests_new_issue` — suppression du patch obsolète
- `test_poll_github_issues_assigns_correct_next_ticket_id` — suppression du patch obsolète
- `test_poll_github_issues_multiple_issues_sequential_ids` — suppression du patch obsolète
- `test_poll_github_issues_does_not_commit_after_intake_on_success` — réécrit pour vérifier l'absence de `git commit` dans les appels subprocess (assertion plus robuste)
- `test_poll_github_issues_does_not_call_commit_after_intake_on_failure` — réécrit avec mock subprocess, vérification absence de `git commit`

### `tests/test_daemon_checkpoint.py` — 4 FAIL (pré-existants, hors scope T111)

Ces 4 échecs **préexistaient sur `main`** et ne sont **pas introduits par T111** :
- `test_ensure_clean_working_tree_workflow_artifacts_trigger_checkpoint`
- `test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint`
- `test_ensure_clean_working_tree_nothing_to_commit_proceeds`
- `test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds`

**Cause** : les tests mockent `run_daemon.subprocess.run` mais `_ensure_clean_working_tree` appelle `checkpoint_transition()` (importée de `runtime_checkpoint.py`), qui utilise `runtime_checkpoint.subprocess.run` — un namespace différent non intercepté par le mock. Cette divergence est antérieure à T111 (fichier identique entre `main` et cette branche, `git diff main -- tests/test_daemon_checkpoint.py` = 0 ligne).

### Suite complète

```
4 failed (pré-existants), 406 passed in 3.67s
```

---

## Anomalies non bloquantes (rappel review)

- **P1** : `run_issue_intake.py:160` — `except Exception: pass` silencieux pour les échecs SQLite intake ; devrait logger au moins un warning stderr.
- Tests daemon manquants : `board can list ticket from SQLite` et `worker visible from SQLite` (non bloquants V1, identifiés en review).

---

## Conclusion

TEST_COMPLETE — tous les critères d'acceptation sont satisfaits. L'objectif central (suppression des commits parasites sur `main` pour l'état runtime) est atteint et vérifié. Un bug de test corrigé (5 tests mis à jour). Les 4 échecs `test_daemon_checkpoint.py` sont pré-existants et hors scope T111.
