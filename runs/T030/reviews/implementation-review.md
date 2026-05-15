---

# PR Review — T030: Live daemon activity feed and auto-refresh

## Résumé

L'implémentation couvre l'essentiel du ticket : hook `usePolling` propre, polling sur les trois pages principales, feed d'activité daemon, statut live, et nettoyage correct des intervals. La structure est sobre et correctement scopée.

Deux problèmes bloquants sont identifiés : un gap fonctionnel sur le refresh des logs et un manque de couverture de test explicitement requis par le ticket.

---

## Vérifications effectuées

- `usePolling.js` et ses 7 tests
- `TicketsPage.jsx`, `TicketDetailPage.jsx`, `DaemonPage.jsx`
- `DaemonActivityFeed.jsx`
- `daemon_manager.py` (fonctions `get_activity`, `_last_heartbeat`, `_current_ticket`, `start`)
- `routes/daemon.py` et `schemas.py`
- Tests `usePolling.test.js` et `DaemonActivityFeed.test.jsx`

---

## Points validés

**Hook `usePolling`** — appel immédiat sur mount, `clearInterval` sur unmount, pattern `savedCallback` via ref correct, paramètre `key` pour redémarrer le polling sur navigation. Testé exhaustivement (7 cas).

**TicketsPage** — polling 5s, badge d'état coloré, timestamp "Updated at HH:MM:SS".

**DaemonPage / DaemonActivityFeed** — statut live complet (running/stopped, PID, uptime, current_ticket, last_heartbeat), feed basé sur `daemon.log`, endpoint `GET /daemon/activity?lines=N` avec validation `ge=1, le=500`.

**Gestion des erreurs** — `OSError`, `json.JSONDecodeError`, `errors="replace"` pour l'encodage, `ErrorBanner` frontend.

**Scope** — aucune dérive. Pas de WebSocket, SSE, auth — conforme au hors-scope.

---

## Problèmes détectés

### [BLOQUANT] 1. Logs tab ne se rafraîchit pas en continu

**Fichier** : `TicketDetailPage.jsx:49-51`

Le tab content (y compris les logs) n'est invalidé que lorsque `ticket.state` change :

```js
if (prevStateRef.current !== null && prevStateRef.current !== newTicket.state) {
  setTabContent({})
}
```

Pendant une phase `CODER_RUNNING` prolongée, l'état reste identique pendant plusieurs minutes tandis que les logs s'accumulent. L'utilisateur sur l'onglet "logs" ne verra aucune mise à jour — exactement le cas d'usage central du ticket.

Le ticket distingue clairement :
- **Logs** : "refresh automatique des logs" — sans condition de changement d'état
- **Reviews/tests/artefacts** : "refresh automatique [...] si le ticket change" — conditionnel

**Correction** : re-fetcher le tab "logs" à chaque cycle de polling lorsqu'il est actif, indépendamment des changements d'état.

### [BLOQUANT] 2. Absence de test pour le changement d'état runtime

Le ticket exige explicitement :
> "Ajouter des tests pour : [...] changement d'état runtime"

La logique `prevStateRef` + invalidation de `tabContent` dans `TicketDetailPage` est la partie la plus complexe de l'implémentation et n'a aucune couverture. Aucun test ne vérifie que `tabContent` est vidé quand l'état change ni qu'il est préservé quand il ne change pas.

**Correction** : ajouter `TicketDetailPage.test.jsx` couvrant ce comportement.

---

## Risques éventuels (non bloquants)

- `tabContent` dans le dependency array du `useEffect` (ligne 77) — le guard évite la boucle infinie mais le pattern est fragile
- `key={i}` comme React key dans `DaemonActivityFeed` — acceptable pour une liste non réordonnée
- Scan linéaire de `runs/` dans `_current_ticket` — acceptable à l'échelle actuelle
- "Aucune activité" (français) incohérent avec le reste de l'UI en anglais

---

## Décision

REQUEST_CHANGES — deux corrections bloquantes avant approbation.

## Actions demandées

1. **Refresh continu des logs** : dissocier le tab "logs" de l'invalidation par changement d'état dans `TicketDetailPage`. Re-fetcher les logs à chaque cycle de polling quand l'onglet est actif.
2. **Test changement d'état runtime** : ajouter un test couvrant l'invalidation de `tabContent` sur changement d'état et la préservation sur état stable.

IMPLEMENTATION_FIX_REQUIRED
