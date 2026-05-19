# T109 — Test Report

**Date:** 2026-05-20  
**Branch:** ticket/T109-t109-atomic-runtime-checkpoint-and-worktree-safe-c  
**Tester:** Claude (Sonnet 4.6)

---

## Résumé

**36/40 tests passent. 4 tests échouent.**  
**2 critères d'acceptation non satisfaits sur 6.**

---

## Résultats par critère d'acceptation

### AC1 — Toutes les transitions runtime utilisent la même primitive

**PARTIEL**

`checkpoint_transition()` est utilisé :
- `run_daemon.py` : 3 points d'intégration (`_ensure_clean_working_tree`, `_commit_after_intake`, `_checkpoint_and_push_before_pr`) ✅
- `run_issue_intake.py` : `commit_bootstrap()` ✅

Non intégré :
- `services/control_api/services/subprocess_runner.py:184` — `checkpoint_ticket()` délègue encore à `run_ticket.py --commit --include-code` au lieu d'appeler `checkpoint_transition()` directement ❌

`run_ticket.py` conserve sa propre logique git (acceptable — outil CLI utilisateur, non daemon).

---

### AC2 — Plus aucun dirty tree après transition valide

**PASS**

`verify_clean_tree()` est appelé à la fin de chaque `checkpoint_transition()` (ligne 202 de `runtime_checkpoint.py`). Si l'arbre reste sale, `DirtyTreeError` avec le sentinel `DIRTY_RUNTIME_CHECKPOINT` est levée. ✅

---

### AC3 — Plus aucun commit/push oublié

**PASS**

Toutes les transitions daemon critiques passent par `checkpoint_transition()` :
- pre-flight avant lancement step ✅
- après intake issue ✅
- avant création PR (TEST_COMPLETE) ✅

---

### AC4 — Le daemon refuse proprement un runtime incohérent

**PASS**

`_ensure_clean_working_tree()` retourne `False` et loge `DIRTY_RUNTIME_CHECKPOINT` sur `CheckpointError` et `DirtyTreeError`. Le lancement du worker est bloqué. ✅

---

### AC5 — Le dashboard expose clairement les erreurs de persistence runtime

**FAIL**

Le dashboard expose un bouton "Checkpoint" (`POST /tickets/{id}/checkpoint`) qui déclenche un commit. Mais les éléments requis par le ticket sont absents :

- ❌ Artifacts non persistés — aucun endpoint ni composant
- ❌ Dernier commit runtime — non affiché
- ❌ Dernier push runtime — non affiché
- ❌ Fichiers dirty — aucun endpoint `git status` exposé côté API

L'API de contrôle ne dispose d'aucun endpoint pour interroger l'état dirty d'un ticket.

---

### AC6 — Plusieurs tickets worktree peuvent tourner sans collision Git

**PASS**

`resolve_ticket_cwd(ticket_id)` lit `runs/workers.json` et retourne le chemin worktree isolé par ticket. `checkpoint_transition()` accepte `cwd=` pour isoler chaque opération git. Isolation concurrent confirmée par `test_checkpoint_transition_concurrent_isolation`. ✅

---

## Résultats des tests

### Suite `test_runtime_checkpoint.py` — 7/7 ✅

| Test | Statut |
|------|--------|
| test_checkpoint_transition_success | PASS |
| test_checkpoint_transition_push_failure | PASS |
| test_checkpoint_transition_dirty_tree_remaining | PASS |
| test_resolve_ticket_cwd_from_workers_json | PASS |
| test_resolve_ticket_cwd_fallback_when_no_workers | PASS |
| test_checkpoint_transition_gitadd_force_for_ignored_files | PASS |
| test_checkpoint_transition_concurrent_isolation | PASS |

### Suite `test_daemon_checkpoint.py` — 15/19 ❌ (4 échecs)

| Test | Statut |
|------|--------|
| test_launch_ticket_passes_auto_commit_flag | PASS |
| test_launch_ticket_passes_auto_push_flag | PASS |
| test_launch_ticket_passes_auto_include_code_flag | PASS |
| test_launch_ticket_no_auto_flags_by_default | PASS |
| test_run_once_passes_auto_flags_to_launch_ticket | PASS |
| test_classify_dirty_files_clean_tree | PASS |
| test_classify_dirty_files_runs_files_are_workflow_artifacts | PASS |
| test_classify_dirty_files_code_scope_files_are_not_unknown | PASS |
| test_classify_dirty_files_non_scope_files_are_unknown | PASS |
| test_classify_dirty_files_mixed | PASS |
| test_classify_dirty_files_handles_rename_arrow | PASS |
| test_classify_dirty_files_returns_empty_on_git_failure | PASS |
| test_ensure_clean_working_tree_returns_true_when_clean | PASS |
| test_ensure_clean_working_tree_unknown_files_aborts | PASS |
| **test_ensure_clean_working_tree_workflow_artifacts_trigger_checkpoint** | **FAIL** |
| **test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint** | **FAIL** |
| test_ensure_clean_working_tree_code_scope_files_do_not_block_when_no_unknown | PASS |
| test_ensure_clean_working_tree_checkpoint_failure_aborts | PASS |
| **test_ensure_clean_working_tree_nothing_to_commit_proceeds** | **FAIL** |
| **test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds** | **FAIL** |
| test_ensure_clean_working_tree_no_push_when_auto_push_false | PASS |
| test_launch_ticket_aborts_when_unknown_dirty_files | PASS |
| test_launch_ticket_proceeds_after_auto_checkpoint | PASS |

### Suite `test_intake_checkpoint.py` — 10/10 ✅

Tous les tests passent.

---

## Analyse des 4 échecs (bloquants)

Les 4 tests échouent pour la même raison : **mocking obsolète**.

Les tests patchent `run_daemon.subprocess.run` et vérifient la présence de `--commit` ou `--push` dans les arguments subprocess. Ces assertions correspondent à l'ancien design où `_ensure_clean_working_tree()` déléguait à `run_ticket.py --commit`. L'implémentation actuelle appelle `checkpoint_transition()` directement, qui génère ses propres commandes git (`git add -f`, `git commit`, `git push`).

**Détail des échecs :**

1. `test_ensure_clean_working_tree_workflow_artifacts_trigger_checkpoint`  
   Attend `"--commit" in subprocess_call_args` → reçoit `['git', 'status', '--porcelain']` (appel interne de `verify_clean_tree`).

2. `test_ensure_clean_working_tree_code_scope_files_trigger_checkpoint`  
   Même problème.

3. `test_ensure_clean_working_tree_nothing_to_commit_proceeds`  
   Attend `result is True` quand `subprocess.run` retourne `returncode=1`. Mais `returncode=1` sur `git add -f` → `CheckpointError` → `_ensure_clean_working_tree` retourne `False`.

4. `test_ensure_clean_working_tree_pushes_when_auto_push_and_commit_succeeds`  
   Cherche `"--push" in subprocess_call_args` → introuvable car l'implémentation appelle `checkpoint_transition(push=True)` qui exécute `git push` directement.

**Correction requise :** remplacer `patch("run_daemon.subprocess.run")` par `patch("run_daemon.checkpoint_transition")` et asserter sur les arguments de `checkpoint_transition`.

---

## Anomalies additionnelles

### dashboard `checkpoint_ticket()` bypass la primitive

`services/control_api/services/subprocess_runner.py:184` :
```python
[sys.executable, str(_RUN_TICKET), ticket_id, "--commit", "--include-code"]
```

L'action checkpoint déclenchée depuis le dashboard passe par `run_ticket.py`, pas par `checkpoint_transition()`. Cela contredit AC1 pour ce chemin. Non bloquant fonctionnellement, mais incohérent avec le principe d'unification.

---

## Verdict

| Critère | Statut |
|---------|--------|
| AC1 — Primitive unifiée pour toutes les transitions | PARTIEL |
| AC2 — Plus aucun dirty tree après transition valide | PASS |
| AC3 — Plus aucun commit/push oublié | PASS |
| AC4 — Daemon refuse proprement un runtime incohérent | PASS |
| AC5 — Dashboard expose les erreurs de persistence | FAIL |
| AC6 — Isolation multi-worktree sans collision Git | PASS |

**Résultat global : REFUSÉ**

Blocages critiques :
1. **4 tests échouent** — mocking obsolète dans `test_daemon_checkpoint.py`, les 4 tests vérifiant le comportement de `_ensure_clean_working_tree()` avec `checkpoint_transition()`.
2. **AC5 non implémenté** — le dashboard n'expose pas les artifacts non persistés, le dernier commit/push runtime, ni les fichiers dirty.
3. **AC1 incomplet** — `checkpoint_ticket()` dans `subprocess_runner.py` contourne encore la primitive.
