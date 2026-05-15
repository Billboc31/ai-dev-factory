Le plan est écrit dans `runs/T103/plan.md`. Voici le résumé des 6 corrections planifiées, intégrant les 3 points de la review :

---

## Plan T103 v2 — Résumé

### Bug 1 — PR avant push (`_checkpoint_and_push_before_pr`, ligne 539–567)
Push systématique que le commit retourne rc=0 ou rc=1 (rien à committer). Les commits locaux précédents doivent toujours être poussés.

### Bug 2 — Mauvaise branche (`launch_ticket`, ligne 618+)
Ajouter `_get_current_branch()` dans `run_daemon.py` et un guard explicite après `_acquire_lock()` : si `current_branch != expected_branch`, skip sécurisé avec log. Pas de checkout automatique.

### Bug 3 — Classification scope dirty tree
Vérification visuelle de `_CODE_SCOPE_PREFIXES` vs `COMMIT_SCOPE`. La différence `runs/` est intentionnelle. Correction seulement si écart constaté.

### Bug 4 — Fichiers runtime dans Git
Le `.gitignore` est déjà correct. Seule action : `git rm -r --cached apps/dashboard/node_modules/`. `runs/.issue-intake.json` reste tracké (registre anti-réingestion — **ne pas ignorer**).

### Nouveau — Checkpoint/push avant `PLAN_REVIEW_NEEDED`
Dans `run_once()`, avant de logger "human gate skipping", appeler `_checkpoint_and_push_before_pr()` pour `PLAN_REVIEW_NEEDED` afin que les artefacts planner soient visibles sur GitHub.

### Nouveau — Sync branche distante avant exécution agent
Nouvelle fonction `_sync_ticket_branch()` dans `launch_ticket()` : `git pull --ff-only origin <branch>`. Abort sécurisé si divergence ; skip silencieux si la branche n'est pas encore sur le remote.

**2 fichiers modifiés** : `run_daemon.py` (tout le code) + `.gitignore` (aucun changement — déjà correct). 1 opération git : `git rm -r --cached apps/dashboard/node_modules/`.
