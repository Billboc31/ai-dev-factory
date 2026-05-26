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


# T151 — T151 — Deployment environments dashboard

**Source**: GitHub Issue #149

## Description

Goal: replace the current sandbox-oriented deployment UI with a full deployment environments dashboard supporting branches, persistent environments and deployment lifecycle management.

Context:
The current sandbox UI is still highly technical and runtime-oriented:
- ticket-centric
- manual runtime paths
- sandbox-focused terminology
- limited deployment targeting

As the runtime/deployer stack matures, the product now needs a real environments and deployments experience.

Target examples:
- main
- develop
- integration
- preview
- sandbox
- feature branch deployments
- PR deployments

Scope:
- introduce a dedicated Environments / Deployments page in the dashboard
- support deploying arbitrary refs:
  - branches
  - tags
  - PR refs
  - commits
- support named environments:
  - main
  - develop
  - integration
  - preview
  - sandbox
  - custom
- support deployment modes:
  - Deploy & Test
  - Persistent Environment
- display:
  - deployment status
  - lifecycle state
  - URLs
  - health state
  - branch/ref
  - runtime logs
  - deployment timestamps
- allow:
  - deploy
  - redeploy
  - stop
  - delete
  - refresh
  - open URLs
- support concurrent environments for the same project
- keep environment/deployment concepts generic and project-agnostic
- integrate with isolated runtime roots, supervisor/daemon lifecycle and proxy URLs

Potential future directions:
- environment templates
- automatic preview deployments per PR
- deployment history
- environment snapshots
- environment pinning
- deployment rollback

Tests:
- deploy branch environment
- deploy persistent environment
- concurrent environment deployments
- environment deletion cleanup
- branch/ref display correctness
- environment lifecycle transitions
- dashboard action idempotency

Out of scope:
- Kubernetes
- production rollout orchestration
- cloud deployment
- GitHub Actions integration
- authentication/permissions
- distributed deployment scheduling

Acceptance:
- dashboard exposes a full Environments / Deployments page
- users can deploy arbitrary refs and branches
- users can manage persistent environments from the UI
- multiple environments can coexist simultaneously
- environments expose URLs and lifecycle state clearly
- deployment actions are idempotent
- implementation remains generic and project-agnostic

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Everything looks correct. Here's a summary of what was implemented:

---

## Implementation complete

**Files modified:**

- `services/control_api/models/sandbox.py` — Added 3 enums (`EnvironmentType`, `EnvironmentMode`, `RefType`) and 7 optional fields to `SandboxState` (all `None` by default for backward-compatibility)
- `services/control_api/services/sandbox_manager.py` — Extended `create()` with optional env kwargs; `start()` now stamps `deployed_at`; `stop()` now stamps `stopped_at`
- `services/control_api/main.py` — Imports and registers the new environments router
- `apps/dashboard/src/App.jsx` — Added `EnvironmentsPage` import, `/environments` route, and "Environments" nav link

**Files created:**

- `services/control_api/routes/environments.py` — 8 REST endpoints (`POST`, `GET`, `GET/{id}`, `POST/{id}/redeploy`, `POST/{id}/stop`, `DELETE/{id}`, `POST/{id}/refresh`, `GET/{id}/logs`), all delegating to `SandboxManager`
- `apps/dashboard/src/api/environments.js` — 8 axios client functions mirroring the routes
- `apps/dashboard/src/pages/EnvironmentsPage.jsx` — Polling grid page with "New Environment" button
- `apps/dashboard/src/components/EnvironmentCard.jsx` — Card with status/type badges, URL links, timestamps, action buttons, and inline log viewer
- `apps/dashboard/src/components/CreateEnvironmentModal.jsx` — Form for env_name, ref, ref_type, env_type, deployment_mode, project_root
- `tests/test_environment_routes.py` — 7 tests, all green

**Test results:** 7/7 new tests pass; 38/38 existing sandbox tests pass (no regressions).

---

## Review

Now I have all the information needed to write the review.

---

# PR Review — T151: Deployment Environments Dashboard

## Résumé

L'implémentation introduit un dashboard Environments complet reposant sur `SandboxManager` comme backend unique. L'architecture est conforme au plan approuvé : pas de nouveau moteur d'orchestration, les environnements sont des sandboxes enrichies de métadonnées. L'ensemble des critères d'acceptance fonctionnels est couvert. Un bug React bloquant est présent dans `LogsModal`.

## Vérifications effectuées

- Lecture complète de tous les fichiers produits : `routes/environments.py`, `models/sandbox.py`, `services/sandbox_manager.py`, `EnvironmentsPage.jsx`, `EnvironmentCard.jsx`, `CreateEnvironmentModal.jsx`, `api/environments.js`, `App.jsx`
- Vérification des 7 tests dans `tests/test_environment_routes.py`
- Comparaison plan approuvé ↔ implémentation livrée
- Vérification des critères d'acceptance du ticket

## Points validés

**Backend**
- Les 3 enums (`EnvironmentType`, `EnvironmentMode`, `RefType`) et les 7 champs optionnels de `SandboxState` sont correctement définis avec `None` comme défaut — rétrocompatibilité préservée.
- `SandboxManager.create()` accepte les kwargs d'environnement et les persiste dans `SandboxState`.
- `start()` stampe `deployed_at`, `stop()` stampe `stopped_at` — conformes au plan.
- `GET /environments` filtre correctement par `env_name is not None`.
- `DELETE /environments/{id}` retourne 204 et délègue à `destroy()`.
- Idempotence : `stop()` sur un environnement déjà stoppé ne produit pas de 5xx.
- `POST /environments` appelle `create()` puis `start()` atomiquement, avec `ticket_id=env_name` pour compatibilité avec le constructeur existant.

**Frontend**
- Route `/environments` correctement déclarée dans `App.jsx`.
- Lien nav "Environments" présent.
- `EnvironmentsPage` : polling 5s via `usePolling`, état vide affiché, modale de création fonctionnelle.
- `CreateEnvironmentModal` : formulaire complet avec tous les champs requis, logique d'envoi correcte (`ref_type=null` si `ref` vide).
- `EnvironmentCard` : badges colorés par statut/type, URLs cliquables, timestamps, boutons d'action avec état `busy` individuel.

**Tests**
- Les 7 tests couvrent exactement les 7 critères d'acceptance du plan.
- Tests d'intégration via `TestClient`, sans HTTP réel — isolation correcte.
- `subprocess.run` mocké pour éviter les appels docker réels.

## Problèmes détectés

### [BLOQUANT] `LogsModal` — `useState` utilisé comme `useEffect` (EnvironmentCard.jsx:53)

```javascript
// Actuel — incorrect
useState(() => {
  api.getEnvironmentLogs(envId)
    .then(r => setLogs(r.data.logs || '(no logs)'))
    ...
})

// Attendu
useEffect(() => {
  api.getEnvironmentLogs(envId)
    .then(r => setLogs(r.data.logs || '(no logs)'))
    ...
}, [envId])
```

`useState` avec un callback lazy est censé être **pur** (calcul de valeur initiale uniquement). Utiliser une lazy initializer pour déclencher un effet de bord (appel API) viole le contrat React. En React 18 StrictMode (activé par défaut en développement), les initialiseurs lazy s'exécutent **deux fois**, produisant deux appels API à chaque ouverture de la modale. En mode concurrent React 18 production, le comportement est indéfini car React peut invoquer la fonction de composant plusieurs fois avant de commiter. La valeur de retour du `useState()` est également discardée, créant une variable d'état fantôme.

**Correction requise** : remplacer `useState(() => {...})` par `useEffect(() => {...}, [envId])` et ajouter `useEffect` à l'import `react`.

### [MINEUR] Démarrage silencieux dans `POST /environments` (environments.py:53–57)

Si `mgr.start()` lève une exception, la réponse retourne 201 avec `status=stopped` et sans `deployed_at`. Le client voit une création réussie mais un environnement non démarré, sans indication d'erreur. L'erreur est loguée côté serveur mais invisible côté client. Ce comportement est fonctionnellement acceptable (le polling détectera l'état stoppé) mais peut surprendre l'utilisateur.

### [MINEUR] Pas de validation d'unicité sur `env_name`

Il est possible de créer deux environnements avec le même `env_name`. Ils auront des `id` différents et coexisteront dans `GET /environments`. Puisque `env_name` est affiché comme label principal de la carte, les doublons peuvent être confondants. Aucun critère d'acceptance n'exige explicitement l'unicité, mais la validation serait souhaitable.

### [INFORMATIF] `subprocess.Popen` non mocké dans les tests

`_start_sandbox_supervisor` utilise `subprocess.Popen` (non `subprocess.run`). Seul `subprocess.run` est mocké dans les tests. En pratique, `Popen` tente de lancer un vrai uvicorn et échoue avec `OSError` (catchée → retourne `None`). Les tests passent car `deployed_at` est stampe après le résultat de `compose up` mocké. Il s'agit d'un pattern préexistant dans les tests sandbox, pas d'une régression T151.

## Risques éventuels

- La réutilisation de `ticket_id=body.env_name` dans `SandboxManager.create()` (ligne 45) est intentionnelle pour compatibilité mais crée une redondance : `state.ticket_id == state.env_name` systématiquement. Pas bloquant, mais une future évolution pourrait clarifier ce champ.
- Aucun risque de sécurité identifié : pas de secrets exposés, pas de commande injectée, les entrées passent par des modèles Pydantic validés.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **Obligatoire** — `apps/dashboard/src/components/EnvironmentCard.jsx` ligne 53 : remplacer `useState(() => { ... })` par `useEffect(() => { ... }, [envId])` et ajouter `useEffect` à l'import depuis `'react'`.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T151/reviews/implementation-review.md
- generated at: 2026-05-26T11:16:34Z

---

Now I have all the information needed to write the review.

---

# PR Review — T151: Deployment Environments Dashboard

## Résumé

L'implémentation introduit un dashboard Environments complet reposant sur `SandboxManager` comme backend unique. L'architecture est conforme au plan approuvé : pas de nouveau moteur d'orchestration, les environnements sont des sandboxes enrichies de métadonnées. L'ensemble des critères d'acceptance fonctionnels est couvert. Un bug React bloquant est présent dans `LogsModal`.

## Vérifications effectuées

- Lecture complète de tous les fichiers produits : `routes/environments.py`, `models/sandbox.py`, `services/sandbox_manager.py`, `EnvironmentsPage.jsx`, `EnvironmentCard.jsx`, `CreateEnvironmentModal.jsx`, `api/environments.js`, `App.jsx`
- Vérification des 7 tests dans `tests/test_environment_routes.py`
- Comparaison plan approuvé ↔ implémentation livrée
- Vérification des critères d'acceptance du ticket

## Points validés

**Backend**
- Les 3 enums (`EnvironmentType`, `EnvironmentMode`, `RefType`) et les 7 champs optionnels de `SandboxState` sont correctement définis avec `None` comme défaut — rétrocompatibilité préservée.
- `SandboxManager.create()` accepte les kwargs d'environnement et les persiste dans `SandboxState`.
- `start()` stampe `deployed_at`, `stop()` stampe `stopped_at` — conformes au plan.
- `GET /environments` filtre correctement par `env_name is not None`.
- `DELETE /environments/{id}` retourne 204 et délègue à `destroy()`.
- Idempotence : `stop()` sur un environnement déjà stoppé ne produit pas de 5xx.
- `POST /environments` appelle `create()` puis `start()` atomiquement, avec `ticket_id=env_name` pour compatibilité avec le constructeur existant.

**Frontend**
- Route `/environments` correctement déclarée dans `App.jsx`.
- Lien nav "Environments" présent.
- `EnvironmentsPage` : polling 5s via `usePolling`, état vide affiché, modale de création fonctionnelle.
- `CreateEnvironmentModal` : formulaire complet avec tous les champs requis, logique d'envoi correcte (`ref_type=null` si `ref` vide).
- `EnvironmentCard` : badges colorés par statut/type, URLs cliquables, timestamps, boutons d'action avec état `busy` individuel.

**Tests**
- Les 7 tests couvrent exactement les 7 critères d'acceptance du plan.
- Tests d'intégration via `TestClient`, sans HTTP réel — isolation correcte.
- `subprocess.run` mocké pour éviter les appels docker réels.

## Problèmes détectés

### [BLOQUANT] `LogsModal` — `useState` utilisé comme `useEffect` (EnvironmentCard.jsx:53)

```javascript
// Actuel — incorrect
useState(() => {
  api.getEnvironmentLogs(envId)
    .then(r => setLogs(r.data.logs || '(no logs)'))
    ...
})

// Attendu
useEffect(() => {
  api.getEnvironmentLogs(envId)
    .then(r => setLogs(r.data.logs || '(no logs)'))
    ...
}, [envId])
```

`useState` avec un callback lazy est censé être **pur** (calcul de valeur initiale uniquement). Utiliser une lazy initializer pour déclencher un effet de bord (appel API) viole le contrat React. En React 18 StrictMode (activé par défaut en développement), les initialiseurs lazy s'exécutent **deux fois**, produisant deux appels API à chaque ouverture de la modale. En mode concurrent React 18 production, le comportement est indéfini car React peut invoquer la fonction de composant plusieurs fois avant de commiter. La valeur de retour du `useState()` est également discardée, créant une variable d'état fantôme.

**Correction requise** : remplacer `useState(() => {...})` par `useEffect(() => {...}, [envId])` et ajouter `useEffect` à l'import `react`.

### [MINEUR] Démarrage silencieux dans `POST /environments` (environments.py:53–57)

Si `mgr.start()` lève une exception, la réponse retourne 201 avec `status=stopped` et sans `deployed_at`. Le client voit une création réussie mais un environnement non démarré, sans indication d'erreur. L'erreur est loguée côté serveur mais invisible côté client. Ce comportement est fonctionnellement acceptable (le polling détectera l'état stoppé) mais peut surprendre l'utilisateur.

### [MINEUR] Pas de validation d'unicité sur `env_name`

Il est possible de créer deux environnements avec le même `env_name`. Ils auront des `id` différents et coexisteront dans `GET /environments`. Puisque `env_name` est affiché comme label principal de la carte, les doublons peuvent être confondants. Aucun critère d'acceptance n'exige explicitement l'unicité, mais la validation serait souhaitable.

### [INFORMATIF] `subprocess.Popen` non mocké dans les tests

`_start_sandbox_supervisor` utilise `subprocess.Popen` (non `subprocess.run`). Seul `subprocess.run` est mocké dans les tests. En pratique, `Popen` tente de lancer un vrai uvicorn et échoue avec `OSError` (catchée → retourne `None`). Les tests passent car `deployed_at` est stampe après le résultat de `compose up` mocké. Il s'agit d'un pattern préexistant dans les tests sandbox, pas d'une régression T151.

## Risques éventuels

- La réutilisation de `ticket_id=body.env_name` dans `SandboxManager.create()` (ligne 45) est intentionnelle pour compatibilité mais crée une redondance : `state.ticket_id == state.env_name` systématiquement. Pas bloquant, mais une future évolution pourrait clarifier ce champ.
- Aucun risque de sécurité identifié : pas de secrets exposés, pas de commande injectée, les entrées passent par des modèles Pydantic validés.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **Obligatoire** — `apps/dashboard/src/components/EnvironmentCard.jsx` ligne 53 : remplacer `useState(() => { ... })` par `useEffect(() => { ... }, [envId])` et ajouter `useEffect` à l'import depuis `'react'`.

---

IMPLEMENTATION_FIX_REQUIRED