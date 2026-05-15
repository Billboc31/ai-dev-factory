# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


# T030 — T030 — Live daemon activity feed and auto-refresh

**Source**: GitHub Issue #30

## Description

# T030 — Live daemon activity feed and auto-refresh

## Contexte

Le système dispose maintenant :

- d’un daemon d’orchestration
- d’une Control API REST
- d’un dashboard UI React
- de tickets pilotables depuis l’UI

Mais l’UI reste principalement statique.

Les tickets ne se mettent pas à jour automatiquement et les logs/runtime nécessitent des refresh manuels.

Le prochain cap est d’obtenir une expérience “runtime vivant” permettant de suivre l’activité du daemon en quasi temps réel.

Architecture cible :

```text
Daemon runtime
↓
Control API
↓
Dashboard auto-refresh
```

## Objectif

Ajouter un système de rafraîchissement automatique et un feed d’activité daemon.

Le dashboard doit montrer les changements runtime sans nécessiter de refresh manuel.

## Inclus

### 1. Auto-refresh tickets list

`TicketsPage` doit se rafraîchir automatiquement.

Exemple :

```text
polling 5s
```

Les changements d’état doivent apparaître automatiquement :

```text
PLANNER_RUNNING
→ PLAN_REVIEW_NEEDED
→ CODER_RUNNING
→ IMPLEMENTATION_REVIEW_NEEDED
```

### 2. Auto-refresh TicketDetailPage

Quand un ticket est ouvert :

- refresh automatique de `state.json`
- refresh automatique des logs
- refresh automatique des reviews/tests/artefacts si le ticket change

### 3. Daemon activity feed

Ajouter un panneau montrant les dernières activités daemon.

Exemples :

```text
[10:41:02] daemon started
[10:41:18] T030 planner started
[10:41:44] T030 PLAN_REVIEW_NEEDED
[10:42:01] T030 coder started
```

Le feed peut être basé sur :

```text
runtime.log
ou
un nouveau daemon.log
```

### 4. Live daemon status

Le statut daemon doit être rafraîchi automatiquement.

Exemple :

```text
running
stopped
last heartbeat
current ticket
```

### 5. Polling management

Le polling doit être proprement nettoyé :

- `clearInterval`
- pas de memory leak
- pas de polling multiple accidentel

### 6. UX minimale

Ajouter :

- indicateurs loading subtils
- badges runtime plus vivants
- indication “updated X seconds ago” si simple à implémenter

Pas de design avancé requis.

### 7. Tests

Ajouter des tests pour :

- polling lifecycle
- cleanup interval
- refresh automatique
- daemon feed rendering
- changement d’état runtime

## Hors scope

- websocket
- SSE
- push realtime serveur
- auth
- multi-user
- notifications push
- mobile app
- animations avancées
- terminal intégré

## Critères d’acceptation

- les tickets se rafraîchissent automatiquement
- TicketDetailPage se met à jour automatiquement
- le statut daemon est live
- un feed daemon existe
- les changements runtime apparaissent sans refresh manuel
- aucun polling zombie
- les tests couvrent les mécanismes de polling
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
apps/dashboard/
services/control_api/
tests/
README.md
```

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All tests pass. Here's a summary of what was implemented:

---

## Files created/modified

### Backend
| File | Change |
|---|---|
| `services/control_api/models/schemas.py` | Added `last_heartbeat`, `current_ticket` to `DaemonStatus`; added `DaemonActivity` model |
| `services/control_api/services/daemon_manager.py` | Redirects daemon stdout to `runs/daemon.log`; adds `get_activity()`; enriches `get_status()` with `last_heartbeat` (from log mtime) and `current_ticket` (scanned from runs/) |
| `services/control_api/routes/daemon.py` | Added `GET /daemon/activity?lines=N` endpoint |

### Frontend
| File | Change |
|---|---|
| `apps/dashboard/src/hooks/usePolling.js` | **New** — `setInterval`/`clearInterval` hook; calls immediately on mount; restarts on key change; no zombie leaks |
| `apps/dashboard/src/api/daemon.js` | Added `getDaemonActivity(lines)` |
| `apps/dashboard/src/components/DaemonActivityFeed.jsx` | **New** — polls `GET /daemon/activity` every 5s; renders log lines with terminal-style styling |
| `apps/dashboard/src/pages/TicketsPage.jsx` | Replaced manual `useEffect` with `usePolling(5s)`; shows "Updated at HH:MM:SS" indicator |
| `apps/dashboard/src/pages/TicketDetailPage.jsx` | Polls ticket state every 5s; invalidates tab cache on state change; restarts polling on ticket navigation |
| `apps/dashboard/src/pages/DaemonPage.jsx` | Reduced polling from 30s → 5s via `usePolling`; added `DaemonActivityFeed`; displays `current_ticket` and `last_heartbeat` |

### Tests
| File | Change |
|---|---|
| `apps/dashboard/tests/usePolling.test.js` | **New** — 7 tests covering lifecycle, cleanup, key-restart, no-zombie |
| `apps/dashboard/tests/DaemonActivityFeed.test.jsx` | **New** — 4 tests covering rendering, empty state, error handling |
| `apps/dashboard/tests/DaemonPage.test.jsx` | Added `getDaemonActivity` mock to existing `beforeEach` |
| `tests/test_control_api_endpoints.py` | 3 new tests for `GET /daemon/activity` |
| `tests/test_control_api_subprocess.py` | 5 new tests for `get_activity()` and enriched `get_status()` |

**Results: 34/34 Python tests pass, 49/49 JS tests pass.**

---

## Review

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

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T030/reviews/implementation-review.md
- generated at: 2026-05-15T12:17:27Z

---

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