All done. Here is the test report summary:

---

## TEST_COMPLETE — T111

### Résultats

| Suite | Résultat |
|-------|----------|
| `test_runtime_db.py` | **15/15 pass** |
| `test_daemon_issue_polling.py` | **49/49 pass** (après correction de 5 tests) |
| `test_daemon_checkpoint.py` | 4 fails — **pré-existants sur `main`**, hors scope T111 |

### Critères d'acceptation

Tous les 9 critères sont satisfaits :
- Daemon ingère une issue sans commit sur `main` ✅
- `main` local ne diverge plus à cause du runtime state ✅
- Board voit les tickets depuis SQLite ✅
- Workers visibles depuis SQLite ✅
- Tickets `runs/TXXX` lisibles en fallback ✅
- `.issue-intake.json` n'est plus source primaire ✅
- `runs/workers.json` n'est plus source primaire ✅
- SQLite gitignored ✅
- Tests runtime DB passent ✅

### Bug corrigé dans les tests

5 tests dans `test_daemon_issue_polling.py` patchaient `run_daemon._commit_after_intake` — fonction correctement supprimée par T111. Mis à jour pour vérifier l'absence de `git commit` via le mock subprocess (assertion plus robuste et alignée sur la réalité du code).
