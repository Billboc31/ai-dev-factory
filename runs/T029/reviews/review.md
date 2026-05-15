# PR Review — T029 Minimal Dashboard UI

## Résumé

Implémentation d'une interface web React + Vite pour piloter le runtime via la Control API. La structure générale est propre, l'architecture est respectée (UI → Control API uniquement), et les tests couvrent les cas principaux. Deux lacunes bloquantes identifiées par rapport aux critères d'acceptation du ticket.

## Vérifications effectuées

- Architecture : séparation UI / Control API / runtime
- Conformité ticket : toutes les sections du ticket (§1 à §8) comparées à l'implémentation
- Critères d'acceptation : vérification case par case
- Qualité du code : composants, API layer, gestion erreurs
- Couverture de tests : 35 tests, 3 fichiers composants + 1 fichier API
- Sécurité : absence de secrets, validation des entrées côté API, appels subprocess

## Points validés

**Architecture**
- `apps/dashboard/` est un module isolé ✓
- Toute communication passe par `/api` proxié vers la Control API ✓
- Aucun accès direct à `state.json`, Git, ou aux scripts runtime ✓
- CORS activé côté Control API ✓

**Pages et composants**
- `TicketsPage` : tableau avec ID, état (colorisé), branche, last update ✓
- `TicketDetailPage` : tabs overview/logs/plan/review/tests avec chargement lazy ✓
- `DaemonPage` : status avec indicateur visuel, PID, boutons Start/Stop/Restart ✓
- `ErrorBanner` : affichage d'erreurs dismissable avec `role="alert"` ✓
- `ActionButton` : feedback loading/success/error centralisé ✓

**Actions workflow**
- Run Next, Approve Plan, Request Plan Fix, Approve Implementation, Request Implementation Fix ✓
- `run-next` retourne 202 (async), les autres retournent 200 synchrone ✓
- Boutons Git : Commit, Push, Checkpoint ✓
- `onSuccess={refreshTicket}` permet de rafraîchir l'état après action ✓

**Tests**
- 17 tests API (`api.test.js`) : toutes les fonctions tickets + daemon ✓
- 5 tests `TicketsPage` : rendering, data, empty state, erreur, navigation ✓
- 7 tests `TicketDetailPage` : state, boutons, erreurs, actions ✓
- 6 tests `DaemonPage` : status running/stopped, boutons, erreur ✓

**Sécurité**
- Validation ticket ID avec regex `^T\d{3,}$` dans `artifact_reader.py` ✓
- Subprocess appelé avec liste d'arguments (pas `shell=True`) ✓
- Pas de secrets hardcodés ✓

**Qualité code**
- Composants courts et lisibles ✓
- Nommage explicite ✓
- Gestion erreurs explicite (try/catch dans ActionButton, ErrorBanner dans les pages) ✓
- Pas de dépendances inutiles ✓

## Problèmes détectés

### [BLOQUANT] Onglet artefacts manquant dans TicketDetailPage

Le ticket exige explicitement :

> Vue détail ticket — Afficher : artefacts disponibles

Critère d'acceptation :

> les artefacts principaux sont visibles

La fonction `getTicketArtifacts(id)` existe dans `src/api/tickets.js` et l'endpoint `GET /tickets/{id}/artifacts` est implémenté dans le Control API. Mais `TicketDetailPage.jsx` n'expose pas d'onglet `artifacts`. L'array `TAB_FETCHERS` ne contient que `['overview', 'logs', 'plan', 'review', 'tests']`.

**Correction attendue** : ajouter un onglet `artifacts` qui appelle `getTicketArtifacts(id)` et affiche la liste des fichiers retournés (JSON → liste de noms de fichiers).

### [BLOQUANT] Colonne "dernier log" absente de TicketsPage

Le ticket spécifie pour le tableau des tickets :

> Informations minimales : ticket id, état courant, branche, dernier update, **dernier log**

La table implémentée n'a que 4 colonnes : ID, State, Branch, Last Update. La colonne "dernier log" est absente.

**Correction attendue** : ajouter une colonne affichant la dernière ligne du log du ticket. Cela peut se faire en chargeant `getTicketLogs(id)` pour chaque ticket et en affichant la dernière ligne, ou en exposant un champ `last_log_line` dans `TicketSummary` (option préférable pour éviter N+1 requêtes).

## Risques éventuels

**[Mineur] Cache des onglets périmé après action workflow**

`TicketDetailPage` met en cache le contenu des onglets dans `tabContent`. Après une action workflow réussie, `refreshTicket()` recharge uniquement l'état principal (`getTicket(id)`). Les onglets logs, plan, review et tests conservent leur contenu périmé jusqu'à ce que l'utilisateur change d'onglet.

Ce comportement n'est pas bloquant (le ticket ne demande pas de live streaming), mais peut induire en erreur. Une solution simple : vider `tabContent` dans `refreshTicket`.

**[Mineur] Daemon : uptime affiché comme timestamp, pas comme durée**

Le ticket demande "uptime si disponible". L'implémentation affiche `started_at` formaté en `toLocaleString()`, soit un timestamp de démarrage. Ce n'est pas une uptime (durée écoulée). Acceptable pour un MVP mais pas strictement conforme.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **[Obligatoire]** Ajouter un onglet `artifacts` dans `TicketDetailPage` qui appelle `getTicketArtifacts(id)` et affiche la liste des fichiers — le critère d'acceptation "artefacts principaux visibles" n'est pas satisfait.

2. **[Obligatoire]** Ajouter la colonne "dernier log" dans `TicketsPage` — information requise par le ticket dans les informations minimales de la liste. Privilégier un champ `last_log_line` dans `TicketSummary` plutôt que N+1 appels depuis le frontend.

3. **[Recommandé]** Réinitialiser `tabContent` lors de `refreshTicket` pour éviter d'afficher des données périmées après une action workflow.
