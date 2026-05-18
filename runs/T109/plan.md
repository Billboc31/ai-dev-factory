Plan écrit dans `runs/T109/plan.md`. Voici un résumé :

## Plan T109 — Résumé

**Nouveau fichier :** `tools/agent_runner/runtime_checkpoint.py` avec :
- `resolve_ticket_cwd(ticket_id)` — lit `workers.json`, fallback repo root
- `collect_runtime_artifacts(ticket_id, cwd)` — liste les fichiers sous `runs/TXXX/`
- `checkpoint_transition(ticket_id, message, push, include_code, cwd)` — add → commit → push → verify, raise `CheckpointError`/`DirtyTreeError` en cas d'échec
- `verify_clean_tree(ticket_id, cwd)` — `git status --porcelain` → raise si dirty

**3 migrations :**
- `run_ticket.py:114` — ajouter `cwd=` à `run_command()` ; `push_branch():317` — dirty tree bloquant au lieu de warning
- `run_daemon.py:403,611` — remplacer `_commit_after_intake()` et `_checkpoint_and_push_before_pr()` (supprimer le workaround subprocess→subprocess), ajouter classification `DIRTY_RUNTIME_CHECKPOINT`
- `run_issue_intake.py:125-141` — remplacer les 3 appels git ad-hoc

**Tests :** 7 cas dans `tests/test_runtime_checkpoint.py` (success, push failure, dirty tree, cwd resolution ×2, git add -f, isolation concurrente).

**Risque principal :** double-commit si l'ancien `_checkpoint_and_push_before_pr()` n'est pas complètement supprimé lors de la migration.
