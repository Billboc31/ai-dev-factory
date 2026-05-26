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
