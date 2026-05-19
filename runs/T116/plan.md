Plan écrit dans `runs/T116/plan.md`. Voici un résumé :

---

**8 étapes identifiées, toutes bornées et locales :**

1. **`board_service.py:69`** — remplacer le path hardcodé par une résolution via `AI_DEV_FACTORY_RUNTIME_ROOT` (bug principal : board cassé en Docker)
2. **`runtime_db.py`** — supprimer le fallback `git common dir` qui peut créer des DB locales dans les worktrees
3. **`run_daemon.py`** — introduire `state_dir` distinct de `runs_dir` ; migrer `workers.json` et `.issue-intake.json` vers `state/`
4. **`run_daemon.py`** — ajouter file logging vers `RUNTIME_ROOT/logs/daemon.log`
5. **`board_service.py`** — lire workers/intake depuis `state/` quand env var est set
6. **`runtime_resolver.py`** — ajouter `resolve_state_dir()` et `resolve_logs_dir()` par cohérence
7. **`deploy/bootstrap.sh`** — migration best-effort des artefacts existants (copie, sans supprimer)
8. **Docs** — `runtime-layout.md` et `decisions-log.md` à jour

**Risque principal :** le fallback local est conservé pour dev sans Docker — les environnements sans `AI_DEV_FACTORY_RUNTIME_ROOT` gardent le comportement actuel.

**Hors scope :** containerisation daemon, multi-runtime orchestration, suppression physique des anciennes DB.
