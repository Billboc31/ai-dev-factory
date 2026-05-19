---

## Test Report — T116

**Résultat : IMPLEMENTATION_FIX_REQUIRED**

### Résumé des vérifications

**Tous les critères d'acceptation fonctionnels passent :**
- Board Docker lit depuis `RUNTIME_ROOT` ✅
- `resolve_state_dir()` / `resolve_logs_dir()` dans `runtime_resolver.py` ✅
- Daemon file logging vers `RUNTIME_ROOT/logs/daemon.log` ✅
- `workers.json` / `.issue-intake.json` dans `state/` via `state_dir` ✅
- `_check_runtime_clone()` hard gate (exit code 2) ✅
- `bootstrap.sh` crée les 7 répertoires canoniques ✅
- Migration best-effort des artefacts existants ✅
- `runtime_db.py` : RUNTIME_ROOT first, git common-dir fallback ✅

**399 tests passent. 8 échouent — dont 2 sont des régressions T116 :**

### Régressions T116 (bloquantes)

1. **`test_run_once_calls_launch_for_auto_runnable_state`** (`tests/test_run_daemon.py`) — T116 a ajouté `state_dir` comme kwarg à l'appel `launch_ticket()` mais n'a pas mis à jour l'assertion du test.
2. **`test_run_once_passes_auto_flags_to_launch_ticket`** (`tests/test_daemon_checkpoint.py`) — même cause.

**Correction requise** : ajouter `state_dir=runs` dans les assertions `assert_called_once_with(...)` des deux tests. Trivial.

### Incident de contamination de branche

Pendant ce test, 4 commits "T001: checkpoint [TEST_COMPLETE]" ont été poussés sur la branche T116 par le mécanisme `checkpoint_transition` déclenché involontairement par les tests de pre-flight — dont un commit (`79d2885`) a temporairement supprimé du code T116. Les fichiers ont été restaurés depuis le commit approuvé `e50e73c` et committés dans `ba90478`. La branche est saine. Les tests de checkpoint nécessitent une isolation git pour ne pas opérer sur le vrai repository.
