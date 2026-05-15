All 34 Python tests pass. Here is the full structured review.

---

# PR Review — T030: Live daemon activity feed and auto-refresh (attempt 2)

## Résumé

Cette tentative corrige les deux problèmes bloquants identifiés lors de la review précédente. L'implémentation est complète, correctement scopée, et couvre tous les critères d'acceptation du ticket. Les 52 tests frontend et 34 tests Python passent.

---

## Corrections des points bloquants précédents

### [RÉSOLU] 1. Logs tab ne se rafraîchissait pas en continu

**Fichier** : `TicketDetailPage.jsx:52-56`

Le branchement `else if` dans `fetchTicket` traite maintenant les deux cas distincts correctement :
- Si l'état change → `setTabContent({})` (tout vider)
- Si l'état ne change pas ET qu'on est sur l'onglet logs → `delete n.logs` (invalider uniquement les logs)

```js
if (prevStateRef.current !== null && prevStateRef.current !== newTicket.state) {
  setTabContent({})
} else if (activeTabRef.current === 'logs') {
  setTabContent(prev => { const n = { ...prev }; delete n.logs; return n })
}
```

Le pattern `activeTabRef` — mis à jour synchronement par `useEffect` — est correct : il évite les closures périmées sans redémarrer le polling. La logique correspond exactement à la distinction du ticket ("logs : refresh sans condition" vs "reviews/tests/artifacts : si le ticket change").

### [RÉSOLU] 2. Absence de test pour le changement d'état runtime

**Fichier** : `TicketDetailPage.test.jsx`

Trois tests couvrent maintenant ce comportement :
- `invalidates tab content when ticket state changes` ✓
- `preserves tab content when ticket state is unchanged` ✓
- `re-fetches logs on each poll when logs tab is active` ✓

L'approche — mocker `usePolling` pour capturer le callback et le déclencher explicitement via `simulatePoll()` dans `act()` — est propre et explicite.

---

## Points validés

**Hook `usePolling`** — appel immédiat, `clearInterval` sur unmount, `savedCallback` via ref évite les restarts inutiles, paramètre `key` pour redémarrer sur navigation. 7 tests couvrent tous les cas de bord (zombie, null delay, key change, callback identity).

**TicketsPage** — polling 5s, badge coloré par état, indicateur "Updated at HH:MM:SS" conforme au ticket.

**DaemonPage** — statut live (running/stopped, PID, uptime, current_ticket, last_heartbeat), boutons start/stop/restart, feed d'activité intégré.

**DaemonActivityFeed** — composant isolé avec son propre polling 5s, gestion erreur, "Aucune activité" sur liste vide.

**Backend** — `get_activity()` lit `daemon.log` avec tail correct, `_last_heartbeat()` via mtime fichier, `_current_ticket()` scan borné par regex `^T\d{3,}$`, endpoint `GET /daemon/activity?lines=N` avec validation `ge=1, le=500`. Schemas Pydantic à jour.

**Gestion des erreurs** — OSError, JSONDecodeError, `errors="replace"` pour l'encodage, ErrorBanner frontend.

**Scope** — aucune dérive. Pas de WebSocket, SSE, auth.

---

## Observations non bloquantes (inchangées)

- `tabContent` dans le dependency array du useEffect (ligne 82) — le guard `if (tabContent[tab] !== undefined) return` prévient la boucle infinie mais le pattern reste fragile. Acceptable pour la portée du ticket.
- `key={i}` dans DaemonActivityFeed — acceptable pour une liste append-only sans réordonnement.
- "Aucune activité" en français dans une UI majoritairement anglophone — mineur.

---

## Résultat des tests

- Frontend : **52 tests, 0 échec** (`usePolling`, `DaemonActivityFeed`, `DaemonPage`, `TicketDetailPage`, `TicketDetail`, `TicketList`)
- Python : **34 tests, 0 échec** (endpoints + subprocess_runner)

---

## Décision

Les deux corrections bloquantes sont correctement implémentées et couvertes par des tests. Tous les critères d'acceptation du ticket sont remplis.

IMPLEMENTATION_APPROVED
