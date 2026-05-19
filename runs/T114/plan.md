Le plan est écrit dans `runs/T114/plan.md`. Voici un résumé :

---

## Plan T114 — Résumé

**Nature du ticket** : principalement documentation + un garde-fou code. Aucune migration de données.

### Ce qui est dans le scope

**3 fichiers docs à créer :**
- `docs/ai/architecture.md` — vue d'ensemble : séparation humain/runtime, runtime root, multi-projets
- `docs/ai/runtime-layout.md` — arborescence filesystem complète, écart actuel vs cible documenté
- `docs/ai/workflow-invariants.md` — invariants formels, règles Git/worktree, points d'enforcement code

**Code :**
- `run_daemon.py` : ajout de `_check_runtime_clone()` appelée au début de `main()`. Deux mécanismes : sentinel file `.ai-dev-factory-runtime` à la racine du clone, ou env var `AI_DEV_FACTORY_RUNTIME_ROOT`. Sans l'un ni l'autre → exit code 2 avec message explicite.

**Autres :**
- `.gitignore` : pattern pour le sentinel
- `decisions-log.md` : entrée T114

### Risque principal

L'architecture cible (`~/runtime/…`) diverge des chemins actuels (SQLite dans `.runtime/`, logs dans `runs/`). Le plan documente cet écart explicitement avec la note "migration future" — la migration effective est hors scope de T114.
