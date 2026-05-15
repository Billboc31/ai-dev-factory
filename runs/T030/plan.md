Le plan est écrit dans `runs/T030/plan.md`. Voici un résumé de ce qui a été planifié :

---

## Plan T030 — Vue d'ensemble

### Backend (Control API — 2 fichiers modifiés)
1. **`daemon_manager.py`** — redirige le stdout du daemon vers `runs/daemon.log` au démarrage + ajoute `get_activity()` + enrichit `get_status()` avec `last_heartbeat` et `current_ticket`
2. **`routes/daemon.py`** + **`schemas.py`** — nouveau endpoint `GET /daemon/activity?lines=N`

### Frontend (1 hook + 1 composant + 3 pages + 1 api)
3. **`usePolling.js`** (nouveau hook) — encapsule `setInterval`/`clearInterval`, appel immédiat au montage, un seul interval actif
4. **`TicketsPage`** — polling 5 s via `usePolling`, indicateur "updated X s ago"
5. **`TicketDetailPage`** — polling state 5 s + refresh conditionnel des onglets si state change
6. **`DaemonPage`** — polling réduit à 5 s, intègre `DaemonActivityFeed`
7. **`DaemonActivityFeed.jsx`** (nouveau composant) — affiche les dernières lignes de daemon.log

### Tests (5 fichiers : 2 nouveaux + 3 enrichis)
Couvrent : lifecycle polling, cleanup interval, refresh conditionnel, rendu feed, absence de zombie.

### Risque principal
Le daemon existant déjà démarré n'a pas de `daemon.log` — l'UI affichera "Aucune activité" gracieusement jusqu'au prochain démarrage.
