I have all the information needed. Let me write the review.

---

# PR Review — T151: Deployment Environments Dashboard (retry)

## Résumé

La review précédente a identifié un bug bloquant React (`useState` utilisé à la place de `useEffect` dans `LogsModal`). Le fix a été appliqué correctement. La revue complète de tous les artefacts confirme que l'implémentation est conforme au plan approuvé et satisfait l'ensemble des critères d'acceptance du ticket.

## Vérifications effectuées

- Lecture complète de l'état courant de tous les fichiers implémentés : `routes/environments.py`, `models/sandbox.py`, `services/sandbox_manager.py`, `api/environments.js`, `EnvironmentsPage.jsx`, `EnvironmentCard.jsx`, `CreateEnvironmentModal.jsx`, `App.jsx`
- Vérification du fix appliqué sur le bug bloquant précédent
- Vérification des 7 tests dans `tests/test_environment_routes.py`
- Comparaison plan approuvé ↔ implémentation courante
- Vérification des critères d'acceptance du ticket

## Validation du fix précédent

**`EnvironmentCard.jsx` — ligne 1 et 53** ✅

```javascript
// Avant (incorrect)
useState(() => {
  api.getEnvironmentLogs(envId).then(...)
})

// Après (correct)
import { useState, useEffect } from 'react'  // useEffect ajouté au import (ligne 1)
...
useEffect(() => {
  api.getEnvironmentLogs(envId).then(...)
}, [envId])  // dépendance correcte (ligne 53–58)
```

Le fix est minimal, ciblé et correct : `useEffect` est ajouté à l'import React ligne 1, et le callback avec effet de bord API est maintenant dans un `useEffect` avec `[envId]` comme dépendance. La sémantique React est respectée.

## Points validés

**Backend**
- Les 3 enums (`EnvironmentType`, `EnvironmentMode`, `RefType`) et les 7 champs optionnels de `SandboxState` sont définis avec `None` comme défaut — rétrocompatibilité garantie pour les états sandbox existants.
- `SandboxManager.create()` accepte tous les kwargs d'environnement et les persiste dans `SandboxState`.
- `start()` stampe `deployed_at` uniquement en cas de succès compose (ligne 204). `stop()` stampe `stopped_at` systématiquement (ligne 223).
- `GET /environments` filtre `s.env_name is not None` — correct, les sandboxes créées sans env_name restent invisibles dans cette vue.
- `DELETE /environments/{id}` délègue à `mgr.destroy()` et retourne 204 — conforme.
- Toutes les routes propagent correctement `SandboxNotFoundError` → HTTP 404.
- `environments.router` enregistré dans `main.py` avec commentaire T151.

**Frontend**
- `App.jsx` : import, route `/environments`, NavLink "Environments" tous présents et correctement positionnés dans la nav.
- `EnvironmentsPage` : polling 5s via `usePolling`, état vide, `ErrorBanner`, grille de `EnvironmentCard`, modale de création.
- `CreateEnvironmentModal` : formulaire complet (env_name, project_root, ref, ref_type, env_type, deployment_mode), `ref_type=null` quand `ref` vide, radio buttons pour deployment_mode, état `busy` sur submit.
- `EnvironmentCard` : badges colorés par statut/type/mode, URLs cliquables en `target="_blank"`, timestamps, boutons d'action avec état `busy` individuel, `onAction()` déclenche refresh après chaque action, `LogsModal` correct.
- `api/environments.js` : 8 fonctions axios couvrant tous les endpoints, `baseURL: '/api'` cohérent avec les autres modules API.

**Tests**
- Les 7 tests couvrent exactement les 7 critères d'acceptance du plan.
- Isolation correcte via `TestClient` et `tmp_path`.
- `subprocess.run` mocké dans `sandbox_manager.py` pour les appels docker compose.
- Le test `test_environment_deletion_cleanup` fonctionne correctement : le `client.get(/{env_id})` hors du contexte patch retourne 404 car le répertoire d'état a été supprimé par `destroy()`.

## Observations non bloquantes conservées

### [MINEUR] Démarrage silencieux dans `POST /environments`

Si `mgr.start()` lève une exception (lignes 53–56), la réponse retourne 201 avec `status=stopped` sans `deployed_at`. L'erreur est loguée côté serveur. Le polling UI détectera l'état stoppé. Aucun critère d'acceptance n'exige que cette erreur soit exposée côté client.

### [MINEUR] Absence de validation d'unicité sur `env_name`

Deux environnements peuvent coexister avec le même `env_name`. Le ticket ne l'interdit pas explicitement et le support des environnements concurrents est un critère d'acceptance. Non bloquant.

### [INFORMATIF] `subprocess.Popen` non mocké dans les tests

Pattern préexistant dans la suite sandbox, pas une régression T151. L'OSError levée par le Popen est catchée dans `_start_sandbox_supervisor` (ligne 331) qui retourne `None` — les tests passent car `deployed_at` est stampe après le résultat de `compose up` mocké.

## Risques éventuels

- Aucun risque de sécurité identifié : pas de secrets exposés, pas d'injection de commande possible (les entrées passent par des modèles Pydantic validés), `subprocess` appelé avec des listes d'arguments, pas des chaînes shell.
- La redondance `ticket_id == env_name` reste non bloquante et notée pour clarification future.

## Décision

Tous les critères d'acceptance du ticket sont satisfaits. Le bug bloquant React a été corrigé correctement et de façon minimale. L'architecture respecte le plan approuvé (pas de nouveau moteur d'orchestration, enrichissement de `SandboxManager`). Les 7 tests couvrent les 7 cas de test requis. L'implémentation est approuvée.

---

IMPLEMENTATION_APPROVED
