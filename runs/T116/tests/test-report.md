# Test Report — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation

## Résumé exécutif

**Résultat : TEST_FAIL (2 régressions introduites par T116)**

L'implémentation T116 est fonctionnellement correcte pour les cas principaux. Les vérifications comportementales passent. Cependant, 2 tests qui passaient sur `main` échouent désormais sur T116 — les assertions de test n'ont pas été mises à jour pour refléter le nouveau paramètre `state_dir` ajouté aux appels `launch_ticket` / `run_once`.

Un incident de contamination de branche est également documenté ci-dessous.

---

## Critères d'acceptation

| Critère | Statut | Détails |
|---|---|---|
| Board Docker lit depuis `RUNTIME_ROOT` | ✅ PASS | `board_service.py:70-74` résout `db_path` via `AI_DEV_FACTORY_RUNTIME_ROOT` |
| `resolve_state_dir()` et `resolve_logs_dir()` dans `runtime_resolver.py` | ✅ PASS | lignes 28-41 — avec fallback légacy |
| Daemon file logging vers `RUNTIME_ROOT/logs/daemon.log` | ✅ PASS | `_LOG_FILE` initialisé ligne 1443 quand RUNTIME_ROOT est set |
| `workers.json` / `.issue-intake.json` dans `state/` | ✅ PASS | `state_dir` résolu via `_rr_resolve_state_dir` dans `main()` ligne 1448 |
| Invariant `_check_runtime_clone()` hard gate | ✅ PASS | test dédié passant — exit code 2 sans sentinel ni RUNTIME_ROOT |
| `deploy/bootstrap.sh` crée la structure runtime | ✅ PASS | vérification manuelle : 8 répertoires créés correctement |
| Migration best-effort des artefacts existants | ✅ PASS | DB, workers.json, .issue-intake.json copiés sans suppression |
| `runtime_db.py` — RUNTIME_ROOT first, puis git common-dir | ✅ PASS | DB path = `/tmp/test/.runtime/ai-dev-factory.sqlite` avec RUNTIME_ROOT set |
| Worktrees ne stockent aucun état persistant | ✅ PASS (dans la limite du scope) | le fallback `git common-dir` empêche DB worktree-locale |
| Documentation `runtime-layout.md` et `decisions-log.md` | ✅ PASS | présents et cohérents avec l'implémentation |

---

## Tests automatisés

### Résultats

```
tests/test_runtime_db.py          15/15 PASS
tests/test_runtime_resolver.py    10/10 PASS
tests/test_run_daemon.py          32/34 — 2 FAIL
tests/test_daemon_checkpoint.py   14/19 — 5 FAIL (dont 1 nouveau)
tests/test_daemon_issue_polling.py 21/22 — 1 FAIL (pré-existant)
autres fichiers de tests          327/327 PASS
```

Total : **399 pass, 8 fail** (5 exclus pour dépendances manquantes : pydantic/fastapi)

### Régressions T116 (nouvelles — bloquantes)

**1. `test_run_once_calls_launch_for_auto_runnable_state`**

T116 a ajouté `state_dir` comme paramètre kwarg à l'appel `launch_ticket()` dans `run_once()`. L'assertion du test n'inclut pas ce paramètre.

```python
# Attendu par le test (pré-T116)
launch_ticket('T001', ..., worktrees_dir=None, auto_commit=False, auto_push=False, auto_include_code=False)
# Appel réel (post-T116)
launch_ticket('T001', ..., worktrees_dir=None, auto_commit=False, auto_push=False, auto_include_code=False, state_dir=<path>)
```

**2. `test_run_once_passes_auto_flags_to_launch_ticket`**

Même cause dans `test_daemon_checkpoint.py`.

### Échecs pré-existants sur `main` (non bloquants pour T116)

Ces 6 tests échouent identiquement sur `main` avant T116 :

| Test | Cause |
|---|---|
| `test_main_returns_2_when_runs_dir_missing` | `AI_DEV_FACTORY_RUNTIME_ROOT` set dans l'env écrase `args.runs_dir` |
| `test_ensure_clean_working_tree_workflow_artifacts_trigger_checkpoint` | `checkpoint_transition()` appelle de vrais git ops ; mock de `subprocess.run` non intercepté depuis `runtime_checkpoint.py` |
| `test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint` | idem |
| `test_ensure_clean_working_tree_nothing_to_commit_proceeds` | idem |
| `test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds` | idem |
| `test_main_poll_issues_flag_calls_poll_before_run_once` | `AI_DEV_FACTORY_RUNTIME_ROOT` écrase `runs_dir` utilisé dans l'assertion |

---

## Vérifications comportementales manuelles

```bash
# bootstrap.sh — création des répertoires canoniques
$ AI_DEV_FACTORY_RUNTIME_ROOT=/tmp/t116_test bash deploy/bootstrap.sh
runtime root ready: /tmp/t116_test
$ ls /tmp/t116_test/
.runtime  clones  logs  registry  runs  state  worktrees
```

```python
# runtime_db — RUNTIME_ROOT first
os.environ['AI_DEV_FACTORY_RUNTIME_ROOT'] = '/tmp/t116_test'
db = runtime_db.get_db_path()
# → /tmp/t116_test/.runtime/ai-dev-factory.sqlite  ✅

# runtime_db — dev fallback (git common-dir)
del os.environ['AI_DEV_FACTORY_RUNTIME_ROOT']
db = runtime_db.get_db_path()
# → /Users/.../clones/ai-dev-factory/.runtime/ai-dev-factory.sqlite  ✅ (pas de chemin worktree)
```

```python
# runtime_resolver — tous les resolvers via RUNTIME_ROOT
rr.resolve_runs_dir(root)   # → /tmp/t116_test/runs   ✅
rr.resolve_state_dir(root)  # → /tmp/t116_test/state  ✅
rr.resolve_logs_dir(root)   # → /tmp/t116_test/logs   ✅
```

---

## Incident : contamination de branche pendant les tests

**Résumé** : 4 commits "T001: checkpoint [TEST_COMPLETE]" ont été poussés sur la branche T116 pendant cette session de test, dont un (`79d2885`) a temporairement supprimé `resolve_state_dir`, `resolve_logs_dir` et les références `state_dir` de l'implémentation T116.

**Cause** : Pour comparer T116 vs main, j'ai exécuté `git checkout main -- <fichiers>` laissant les fichiers sources à leur version main dans le working tree. Ensuite, `test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds` a déclenché `checkpoint_transition(..., include_code=True, push=True)` qui a commité et poussé les versions main des fichiers sources via `COMMIT_SCOPE`.

**Résolution** : Les fichiers corrects ont été restaurés depuis `e50e73c` (commit "implementation approved") et committés dans `ba90478`. L'implémentation T116 est désormais correcte sur HEAD.

**Recommandation** : Les tests `test_ensure_clean_working_tree_*` doivent isoler les opérations git (mock `checkpoint_transition` directement, pas `subprocess.run`) pour éviter toute exécution de git sur le repository réel. Ce problème pré-existait avant T116 et mérite un ticket de correction.

---

## Observations non-bloquantes

Ces points ont été soulevés dans la review d'implémentation et confirmés :

1. **`runtime-layout.md:57`** — documentation mentionne "fallback git common-dir supprimé" alors qu'il a été rétabli (pas supprimé). Mineur, à corriger ultérieurement.
2. **`resolve_ticket_cwd` (`runtime_resolver.py:92`)** — lit `workers.json` depuis `project_root/runs` hardcodé, pas depuis `state_dir`. Fonctionnellement sans impact (fallback non-critique).
3. **`_load_runtime_db` doublon RUNTIME_ROOT** — `board_service.py:68-74` relit `AI_DEV_FACTORY_RUNTIME_ROOT` en interne. Sans impact fonctionnel.

---

## Conclusion

**Résultat : TEST_FAIL**

**Corrections requises avant merge :**

1. Mettre à jour `test_run_once_calls_launch_for_auto_runnable_state` dans `tests/test_run_daemon.py` pour inclure `state_dir=runs` dans l'assertion `mock_launch.assert_called_once_with(...)`.
2. Mettre à jour `test_run_once_passes_auto_flags_to_launch_ticket` dans `tests/test_daemon_checkpoint.py` de la même façon.

Ces deux corrections sont triviales (ajout d'un kwarg dans l'assertion). L'implémentation fonctionnelle est correcte.
