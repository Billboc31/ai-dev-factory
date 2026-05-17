# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T104/reviews/implementation-review.md
- generated at: 2026-05-15T23:42:12Z

---

La review est écrite. Voici le résumé :

---

## Résultat de la review — T104

**Décision : `IMPLEMENTATION_FIX_REQUIRED`**

### Bug bloquant identifié

Dans `run_issue_intake.py`, `commit_bootstrap` ne commite que `ticket.md` — `state.json` est écrit sur le filesystem mais jamais stagé. Quand le worktree est créé via `git worktree add`, il ne reçoit que les fichiers commités, donc `state.json` est absent du worktree.

Conséquence : à chaque cycle du daemon, `run_ticket.py --auto` lancé dans le worktree échoue immédiatement avec `"state not found"`. Le chemin worktree (le cœur du ticket) ne fonctionne jamais pour un ticket neuf.

**Correction requise** : ajouter `state.json` dans `commit_bootstrap` aux côtés de `ticket.md`.

### Autres problèmes détectés

- **Significatif** : après suppression manuelle d'un worktree, le repo principal montre le ticket à l'état `INIT` (stale), ce qui le re-queue indéfiniment.
- **Mineur** : `workers.json` stale après crash daemon (board incorrect).
- **Mineur** : `--max-workers > 1` accepté silencieusement mais non enforced.
- **Mineur** : nommage `daemon.lock` / `workers.json` diverge de la spec (`worker.lock` / `worker.pid`).

Le reste de l'implémentation est solide : la structure supervisor/worker, le backward compatibility, le dashboard, et la sécurité des suppressions de worktree sont corrects.

IMPLEMENTATION_FIX_REQUIRED
