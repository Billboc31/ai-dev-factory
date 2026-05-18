Le plan est écrit dans `runs/T106/plan.md`. Voici un résumé :

---

## Plan T106 — Project issue tree agent and dependency map

**8 étapes, 6 nouveaux fichiers, 4 fichiers modifiés.**

### Ce qui sera construit

1. **`tools/agent_runner/run_issue_mapper.py`** — Agent standalone qui :
   - Fetch toutes les issues ouvertes GitHub (`gh issue list --state open --json number,title,body`)
   - Parse les corps d'issues pour détecter les dépendances explicites (`depends on #X`, `blocked by #X`, `blocks #X`, `requires #X`)
   - Détecte les cycles dans le graphe
   - Croise avec les états locaux (`runs/*/state.json`) pour classifier : `done`, `running`, `waiting_human`, `runnable`, `blocked_dependency`, `blocked_retry`, `not_ingested`
   - Calcule `parallelizable_groups` et `next_recommended`
   - Écrit `runs/.project-map.json` et `runs/.project-map-activity.json` (atomic, max 50 entrées)

2. **Daemon** (`run_daemon.py`) — Deux nouveaux flags :
   - `--poll-project-map` : exécute le mapper à chaque cycle
   - `--use-project-map` : remplace le FIFO par le `next_recommended` de la map (avec fallback FIFO si map absente)

3. **API** — Route `GET /project-map` et `GET /project-map/activity` (nouveau router + service + schemas Pydantic)

4. **Dashboard** — Deux nouvelles pages React :
   - **Project Map** : arbre des tickets, groupes parallélisables, tickets bloqués, ambiguïtés (listes structurées, pas de lib graph pour V1)
   - **Issue Mapper Activity** : historique des scans, suggestions d'ordre d'exécution

### Hors scope V1
Création auto d'issues, librairie graph (D3), inférence IA des dépendances, sync retour GitHub, visualisation cross-repo.
