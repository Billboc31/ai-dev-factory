La review est écrite dans `runs/T111/reviews/review-attempt-1.md`.

**Verdict : IMPLEMENTATION_FIX_REQUIRED**

---

**Ce qui fonctionne bien** :

- L'objectif core est atteint — `_commit_after_intake` n'est plus jamais appelé, `main` ne diverge plus à cause de l'intake
- Le module SQLite est propre : stdlib uniquement, WAL mode, upserts idempotents, résolution worktree-aware via `git rev-parse --git-common-dir`
- gitignore correctement mis à jour (`.runtime/`, `*.sqlite*`, `runs/.issue-intake.json`, `runs/workers.json`)
- Board lit workers et issue index depuis SQLite ✅
- 15 tests unitaires `runtime_db` complets

---

**Problème bloquant — B1** :

Le board service (`board_service.py:136-162`) lit toujours les `state.json` depuis le filesystem pour le placement kanban. La table `ticket_runtime` est correctement populée par le daemon mais jamais consommée par le board pour déterminer l'état des tickets. Le critère d'acceptation *"le board voit les tickets depuis SQLite"* n'est que partiellement rempli.

---

**Problèmes qualité** :

- `_commit_after_intake` existe en dead code ligne 444 — à supprimer
- `_rdb_get_db_path()` (subprocess) et `_rdb_init()` appelés à répétition par cycle de daemon — à cacher au démarrage
- `except Exception: pass` silencieux dans tous les blocs SQLite — ajouter au moins un log de dégradation

IMPLEMENTATION_FIX_REQUIRED
