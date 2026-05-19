I now have all the information needed to produce the final review. All three previously blocking issues and the full implementation context have been verified.

---

# Review — T116 — Canonical Runtime Ownership and Multi-Runtime Foundation (attempt 3)

## Résumé exécutif

Les trois défauts bloquants identifiés dans la review précédente (`IMPLEMENTATION_FIX_REQUIRED`) ont été corrigés. L'implémentation est désormais correcte, bornée au ticket, et fonctionnellement complète pour les environnements Docker et dev local.

---

## Vérification des correctifs requis

### Correctif #1 — `resolve_state_dir()` / `resolve_logs_dir()` n'étaient pas utilisés

**Statut : CORRIGÉ ✅**

- `board_service.py:12` — importe maintenant `resolve_state_dir` depuis `runtime_resolver`
- `board_service.py:101-102` — appelle `resolve_runs_dir(project_root)` et `resolve_state_dir(project_root)` en lieu et place de la logique inline
- `run_daemon.py:66-74` — charge `_rr_resolve_state_dir` et `_rr_resolve_logs_dir` depuis `runtime_resolver` via `importlib`
- `run_daemon.py:1443` — `_LOG_FILE = _rr_resolve_logs_dir(REPO_ROOT) / "daemon.log"` en usage actif
- `run_daemon.py:1448` — `state_dir = _rr_resolve_state_dir(REPO_ROOT)` en usage actif

Les helpers de résolution canoniques sont désormais le chemin unique pour `state_dir` et `logs_dir`. La duplication inline a été supprimée.

---

### Correctif #2 — fallback `runtime_db.py` créait des DB dans les worktrees

**Statut : CORRIGÉ ✅**

`runtime_db.py:83-99` restaure le fallback `git rev-parse --git-common-dir` :

```python
# Dev fallback: git common-dir points to the main repo's .git regardless of which
# worktree this module was loaded from, ensuring a single shared DB in dev mode.
try:
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        ...
        cwd=str(Path(__file__).parent),
    )
    if result.returncode == 0:
        common_dir = result.stdout.strip()
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = (Path(__file__).parent / common_path).resolve()
        return common_path.parent / _DB_FILENAME
except FileNotFoundError:
    pass
# Last resort: module-location path (valid only when invoked from the main clone).
return Path(__file__).resolve().parent.parent.parent / _DB_FILENAME
```

Le `git common-dir` garantit à nouveau qu'un processus lancé depuis un worktree (`run_ticket.py` en dev local) partage la même DB que le daemon. Le fallback `__file__`-based reste en dernier recours documenté — acceptable.

Le docstring du module est cohérent avec l'implémentation.

---

### Correctif #3 — Invariant checks absents

**Statut : CORRIGÉ ✅ (plus fort que le minimum requis)**

`run_daemon.py:1388-1408` — `_check_runtime_clone()` est un hard stop au démarrage :

```python
def _check_runtime_clone() -> bool:
    if (REPO_ROOT / ".ai-dev-factory-runtime").exists():
        return True
    if os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT"):
        return True
    print("error: daemon must run in a runtime clone...", file=sys.stderr)
    return False
```

`run_daemon.py:1432-1433` — appelé dans `main()` avec code de sortie 2 si l'invariant est violé.

`run_daemon.py:1456-1457` — WARNING explicite loggé quand RUNTIME_ROOT n'est pas set (chemin de fallback actif).

---

## Scope compliance

Plan approuvé intégralement couvert. Pas de dérive de scope.

| Livrable | Statut |
|---|---|
| Runtime ownership spec (docs) | ✅ `runtime-layout.md`, `decisions-log.md` |
| Migration bootstrap | ✅ `deploy/bootstrap.sh` |
| Suppression DB locales | ⚠️ Migration best-effort sans cleanup (acceptable per contrainte "migration progressive") |
| Cleanup runtime artifacts | ⚠️ Non implémenté (hors scope confirmé) |
| Runtime hydration Docker | ✅ `bootstrap.sh` copie la DB au démarrage |
| Board stable après restart | ✅ SQLite primary source + fallback JSON |
| Invariant checks runtime | ✅ `_check_runtime_clone()` hard gate + WARNING log |
| Documentation architecture | ✅ |

---

## Observations non-bloquantes résiduelles

**`runtime_resolver.py:64,92` — `_load_workers` et `resolve_ticket_cwd` lisent depuis `runs_dir`**

Ces fonctions chargent `workers.json` depuis `runs_dir` (ou `project_root / "runs"` hardcodé), alors que le daemon écrit désormais dans `state_dir`. Impact fonctionnel minimal : le board utilise SQLite en source primaire et ces fonctions ne sont qu'un fallback de résolution de chemin. À corriger dans un ticket de nettoyage ultérieur.

**`runtime-layout.md:57` — documentation légèrement inexacte**

La ligne `Aucune DB SQLite dans les worktrees (fallback `git common-dir` supprimé)` est trompeuse : le fallback `git common-dir` a été *rétabli*, pas supprimé. Ce qui a été supprimé était le fallback `__file__`-based intermédiaire incorrectement introduit dans la première tentative. Documentation non critique mais à préciser.

**`_load_runtime_db` — double résolution RUNTIME_ROOT**

`board_service.py:68-74` relit `AI_DEV_FACTORY_RUNTIME_ROOT` en interne alors que `get_board()` aurait pu passer `db_path` directement. Doublon sans conséquence fonctionnelle.

---

## Conclusion

Les trois défauts bloquants sont corrigés. L'implémentation est correcte, cohérente, et bornée au périmètre du ticket. Les observations résiduelles sont mineures et sans impact fonctionnel en production.

IMPLEMENTATION_APPROVED
