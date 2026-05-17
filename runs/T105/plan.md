Le plan est écrit dans `runs/T105/plan.md`. Voici un résumé de ce qui est prévu :

---

## Plan T105 — Deux problèmes, six étapes

### Problème 1 : IHM cwd incorrect (bug bloquant)

Toutes les actions dashboard (`approve-plan`, `checkpoint`, `push`…) passent `cwd=project_root` (branche `main`) à `run_ticket.py`. Si le ticket tourne dans un worktree, `run_ticket.py` détecte le mismatch de branche et refuse.

**Fix** : 3 fichiers :
1. **`subprocess_runner.py`** — ajouter `resolve_ticket_cwd(ticket_id, project_root, worktrees_dir)` qui retourne le chemin du worktree si il existe, sinon `project_root`. Passer ce cwd à tous les appels `subprocess.run`.
2. **`main.py`** — ajouter `--worktrees-dir` CLI + stocker dans `app.state.worktrees_dir`
3. **`routes/tickets.py`** — propager `worktrees_dir` depuis `app.state` vers toutes les fonctions `subprocess_runner.*`

### Problème 2 : Pas de merge automatique

**Fix** : dans `run_daemon.py`, ajouter `auto_merge_pr()` avec garde-fous (PR OPEN, non conflictuelle, `pr_number` présent) qui appelle `gh pr merge <number> --squash --delete-branch`. Appelé dans `handle_test_complete()` après `create_or_update_pr()`.

### Tests
- `tests/test_ihm_worktree_cwd.py` (nouveau) : reproduit et vérifie le fix du bug cwd
- `tests/test_daemon_pr_lifecycle.py` : 5 cas pour `auto_merge_pr()` (succès, déjà mergé, conflicting, PR fermée, gh absent)
