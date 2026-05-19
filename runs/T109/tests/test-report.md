---

## Rapport de test — T109

**36/40 tests passent. Verdict : REFUSÉ.**

---

### Critères d'acceptation

| Critère | Statut |
|---------|--------|
| AC1 — Primitive unifiée pour toutes les transitions | **PARTIEL** |
| AC2 — Plus aucun dirty tree après transition valide | PASS |
| AC3 — Plus aucun commit/push oublié | PASS |
| AC4 — Daemon refuse proprement un runtime incohérent | PASS |
| AC5 — Dashboard expose les erreurs de persistence runtime | **FAIL** |
| AC6 — Isolation multi-worktree sans collision Git | PASS |

---

### 4 tests échouent (bloquant)

Tous dans `test_daemon_checkpoint.py`, méthodes vérifiant `_ensure_clean_working_tree()` :

**Cause commune : mocking obsolète.** Les tests patchent `run_daemon.subprocess.run` et cherchent des flags `--commit` / `--push` dans les args subprocess. Ces assertions correspondent à l'ancien design (délégation vers `run_ticket.py --commit`). L'implémentation actuelle appelle `checkpoint_transition()` directement, qui produit des commandes git différentes (`git add -f`, `git commit`, `git push`).

- `test_ensure_clean_working_tree_workflow_artifacts_trigger_checkpoint` — cherche `"--commit" in cmd` → reçoit `['git', 'status', '--porcelain']`
- `test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint` — même erreur
- `test_ensure_clean_working_tree_nothing_to_commit_proceeds` — mock `returncode=1` → `git add` échoue → `CheckpointError` → retourne `False` au lieu de `True`
- `test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds` — cherche `"--push" in subprocess_calls` → introuvable

**Fix requis :** remplacer `patch("run_daemon.subprocess.run")` par `patch("run_daemon.checkpoint_transition")` dans ces 4 tests.

---

### AC5 non implémenté

Le dashboard dispose d'un bouton "Checkpoint" mais n'affiche pas : artifacts non persistés, dernier commit runtime, dernier push runtime, fichiers dirty. Aucun endpoint API n'expose l'état git d'un ticket.

### AC1 incomplet

`services/control_api/services/subprocess_runner.py:184` — `checkpoint_ticket()` appelle encore `run_ticket.py --commit --include-code`, contournant la primitive.

---

Le rapport complet est dans `runs/T109/test-report.md`.
