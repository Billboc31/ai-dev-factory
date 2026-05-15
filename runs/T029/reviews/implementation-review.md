I now have everything I need to write the review.

---

# PR Review — T029 — Minimal dashboard UI for runtime orchestration

## Résumé

L'implémentation livre un dashboard React/Vite complet dans `apps/dashboard/`, intégré à la Control API via proxy Vite. Toutes les fonctionnalités requises par le ticket sont présentes. Le périmètre est respecté, l'architecture est correcte, et aucune logique workflow ou Git n'est dupliquée côté UI.

## Vérifications effectuées

- Lecture complète de tous les fichiers source : `App.jsx`, `TicketsPage.jsx`, `TicketDetailPage.jsx`, `DaemonPage.jsx`, `ActionButton.jsx`, `ErrorBanner.jsx`, `api/tickets.js`, `api/daemon.js`
- Lecture du backend modifié : `services/control_api/routes/tickets.py`, `services/control_api/services/artifact_reader.py`, `services/control_api/models/schemas.py`
- Lecture des fichiers de tests : `api.test.js`, `TicketList.test.jsx`, `TicketDetail.test.jsx`, `DaemonPage.test.jsx`
- Vérification de `vite.config.js` (proxy) et `package.json` (dépendances)

## Points validés

**Architecture — frontière UI/API strictement respectée**
- Toutes les actions UI passent par `client.get/post('/api/...')` (Vite proxy → Control API)
- Aucun accès direct à `state.json`, aux appels Git, aux scripts runtime
- La Control API est le seul point d'entrée depuis le frontend

**Fonctionnalités — tous les critères d'acceptation couverts**
- `TicketsPage` : liste avec ID, état (badge coloré), branche, dernier update, dernier log
- `TicketDetailPage` : 6 onglets (overview/state.json, logs, plan, review, tests, artifacts), tous les boutons workflow et git/runtime
- `DaemonPage` : statut (running/stopped), PID, uptime calculé, boutons Start/Stop/Restart + polling 30s
- `ErrorBanner` : affiché sur chaque page en cas d'erreur API, avec dismiss
- `ActionButton` : loading state, feedback succès/erreur inline par bouton

**Backend — changements minimaux et corrects**
- `artifact_reader.py` : `_last_log_line()` lit la dernière ligne non-vide du log — lecture seule, borné au fichier
- `get_ticket_state()` : renvoie `state.json` brut sans l'exposer directement au client
- `routes/tickets.py` : nouvel endpoint `GET /{ticket_id}/state` — pattern cohérent avec les autres endpoints existants
- `schemas.py` : ajout de `last_log: str | None` sur `TicketSummary` — rétrocompatible

**Tests — couverture des cas requis**
- Rendering principal : ✅ (les trois pages)
- Appels API : ✅ (api.test.js, 15 tests sur la couche axios)
- Gestion erreurs API : ✅ (ErrorBanner sur toutes les pages)
- Boutons d'action : ✅ (approvePlan, runNextStep, startDaemon testés avec clicks)

**Qualité code**
- Composants courts et lisibles, nommage explicite
- Pas d'abstraction prématurée — `ActionButton` est le seul composant partagé et c'est justifié
- `renderContent` gère string/objet/null proprement
- Cache tabs (`tabContent`) correctement invalidé sur changement d'id et après actions
- `useCallback` + `clearInterval` corrects dans DaemonPage

## Problèmes détectés

**Non bloquants — observations uniquement**

**1. Dead code dans `run_next` (`routes/tickets.py` lignes 125–133)**

```python
from fastapi.background import BackgroundTasks   # importé mais jamais utilisé
result_holder: list[ActionResult] = []           # créé mais jamais lu
def _bg() -> None:
    result_holder.append(...)                    # résultat ignoré
```

L'approche `threading.Thread` fonctionne, mais l'import `BackgroundTasks` et la liste `result_holder` sont des artefacts de refactoring. Ils n'affectent pas le comportement mais dégradent la lisibilité. À nettoyer.

**2. `stateBadgeClass` : correspondance par sous-chaîne (`TicketsPage.jsx` ligne 16)**

```js
const match = Object.entries(STATE_COLORS).find(([k]) => state?.includes(k))
```

Un état futur comme `PLAN_APPROVED_MEMORY` correspondrait à `PLAN_APPROVED` et recevrait sa couleur bleue. Avec les états actuellement définis dans le projet, aucun conflit n'existe. Pas bloquant pour la cible minimale de T029, mais fragile à terme.

**3. Couverture api.test.js incomplète**

Les fonctions `getTicketState`, `getTicketPlan`, `getTicketReview`, `getTicketTests`, `getTicketArtifacts` ne sont pas testées unitairement dans `api.test.js`. Elles sont implicitement exercées via `TicketDetail.test.jsx`, mais la couche API n'est pas vérifiée isolément pour ces endpoints. Acceptable pour un ticket "minimal", mais à noter.

## Risques éventuels

**Aucun risque bloquant identifié.**

- `_last_log_line` lit le fichier entier en mémoire pour extraire la dernière ligne. Pour des logs de développement (< quelques MB), c'est négligeable.
- Le résultat de `ActionButton` ne s'auto-efface pas, ce qui est un choix UX discutable mais non dangereux et explicitement dans la zone "hors scope" (design avancé).
- Le workflow existant n'est pas affecté : les changements backend sont additifs et rétrocompatibles.

## Décision

L'implémentation est complète, correcte, et respecte toutes les contraintes d'architecture et de scope du ticket T029. Les trois observations signalées sont non bloquantes — elles relèvent d'un nettoyage de code (dead code) et d'améliorations futures.

- APPROVED

## Actions demandées

Aucune action bloquante requise avant merge.

Recommandations optionnelles pour un ticket ultérieur :
1. Supprimer le dead code dans `run_next` (import `BackgroundTasks` + `result_holder`)
2. Remplacer `state?.includes(k)` par une correspondance exacte dans `stateBadgeClass`
3. Compléter `api.test.js` avec les tests des endpoints de lecture de tabs

IMPLEMENTATION_APPROVED
