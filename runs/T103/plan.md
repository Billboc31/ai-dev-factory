Le plan est écrit dans `runs/T103/plan.md`. Voici le résumé des 4 bugs et des corrections planifiées :

---

## Plan T103 — Résumé

### Bug 1 — PR avant push (run_daemon.py:539–567)
`_checkpoint_and_push_before_pr()` saute le push quand `run_ticket --commit` retourne rc==1 (rien à committer). Si des commits locaux existent mais ne sont pas encore poussés, la PR est créée sans eux. **Correction** : toujours pousser, indépendamment du rc du commit.

### Bug 2 — Mauvaise branche (run_daemon.py:618)
`launch_ticket()` ne vérifie pas la branche courante avant d'opérer. `_ensure_clean_working_tree()` peut appeler `run_ticket --commit` sur la mauvaise branche. **Correction** : ajouter une fonction `_get_current_branch()` dans run_daemon.py (modèle : run_ticket.py:390) et un guard dans `launch_ticket()` après `_acquire_lock()`.

### Bug 3 — Classification dirty tree
`_CODE_SCOPE_PREFIXES` inclut déjà `services/`, `apps/`, `tests/`, `tools/`, `.gitignore`. Le constat est que les listes dans run_daemon.py et run_ticket.py semblent cohérentes. **Action** : vérification visuelle lors de l'implémentation, correction si écart trouvé.

### Bug 4 — Fichiers runtime dans git
- `apps/dashboard/node_modules/` : **6878 fichiers trackés** → `git rm -r --cached apps/dashboard/node_modules/`
- `runs/.issue-intake.json` : tracké → ajouter au `.gitignore` + `git rm --cached`
- Seul fichier `.gitignore` est modifié.

**2 fichiers modifiés** (`run_daemon.py`, `.gitignore`) + 2 opérations `git rm --cached`.
