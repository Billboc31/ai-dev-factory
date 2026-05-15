Le plan est écrit dans `runs/T102/plan.md`. Voici un résumé :

---

## Plan T102 — 7 étapes, 7 fichiers

### Périmètre

**2 fichiers créés** : `board_service.py` (API), `BoardPage.jsx` (UI)  
**5 fichiers modifiés** : `run_daemon.py`, `schemas.py`, `routes/daemon.py`, `api/daemon.js`, `App.jsx`

### Étapes

1. **Git sync** — Nouvelle fonction `_sync_main_before_intake()` dans `run_daemon.py` : vérifie `git status --porcelain`, puis `git checkout main`, puis `git pull origin main`. Si l'une échoue → abort intake pour ce cycle.

2. **Politique de capacité** — `_count_active_tickets(runs_dir)` compte les tickets non archivés. Avant intake : si `active >= max_active_tickets (1)` → toutes les issues candidates sont loguées `skipped-for-capacity`. Sinon : tri par numéro ascendant, intake de la première uniquement. Nouveau flag CLI `--max-active-tickets`.

3. **Modèles Board** — `BoardItem`, `BoardColumn`, `BoardResponse` dans `schemas.py`.

4. **Service board** — `board_service.py` projette `runs/*/state.json` + `daemon.lock` + `retry-state.json` + `gh issue list` en 7 colonnes : `done → pr_ready → waiting_human → blocked → running → queued → backlog`. Priorité de classification stricte. Backlog = issues non ingérées (`gh` failure → colonne vide, pas d'erreur 500).

5. **Endpoint** — `GET /daemon/board` dans `routes/daemon.py` (le router est déjà inclus dans `main.py`).

6. **API frontend** — `getBoardData()` dans `api/daemon.js`.

7. **Page + nav** — `BoardPage.jsx` (kanban 7 colonnes, poll 10s) + route `/board` + lien nav dans `App.jsx`.

### Hors scope

Labels de priorité (`ai-priority-high`, etc.), `allow_parallel_waiting_human`, DB queue, tout changement à `run_ticket.py`.
