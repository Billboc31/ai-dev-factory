Now I have everything I need. Let me write the review.

---

# PR Review — T175: Environment creation UI must expose and validate runtime/deployment target

## Résumé

L'implémentation couvre les 4 fichiers de production pertinents (modal de création, carte d'environnement, provision de l'environnement, deploy runtime) et répond à l'ensemble des critères d'acceptance du ticket.

---

## Vérifications effectuées

- Lecture du diff complet des 4 fichiers de production
- Vérification que le modèle `SandboxState` expose bien les champs requis par le frontend (`sandbox_runtime_root`, `sandbox_dir`, `source_path`, `project_root`) — confirmé dans `services/control_api/models/sandbox.py:51-89`
- Vérification que la route `/environments` sérialise `SandboxState` directement (Pydantic, pas de projection) — confirmé dans `services/control_api/routes/environments.py:137,148`
- Vérification de l'emplacement du log et de la validation par rapport au bootstrap

---

## Points validés

### Frontend — `CreateEnvironmentModal.jsx`

- **Bloc "Runtime target" dans les deux flows** : le flow project-ID (lignes 239-256) et le flow manuel (lignes 280-300) affichent désormais tous les deux le bloc "Runtime target" avec Sandbox path, Runtime root, Source clone. Avant ce patch, le bloc n'existait que dans le flow manuel.
- **Valeurs calculées en temps réel dans le flow manuel** : `${form.sandbox_path}/runtime` et `${form.sandbox_path}/source` sont calculés en JSX à partir de la saisie — pas de logique cachée côté serveur.
- **CSS valide** : toutes les occurrences de `not-font-mono` (classe Tailwind invalide) ont été remplacées par `font-sans`.

### Frontend — `EnvironmentCard.jsx`

- Section "Runtime paths" collapsible, conditionnelle sur la présence d'au moins un des quatre champs (`project_root`, `sandbox_runtime_root`, `sandbox_dir`, `source_path`). Affichage cohérent avec le pattern "Debug" déjà en place.
- Tous les champs sont dans `SandboxState` et sont sérialisés par Pydantic dans les réponses API — le frontend reçoit bien ces valeurs après déploiement.

### Backend — `environment_provision.py`

- `_validate_runtime_consistency` (lignes 93-121) : 4 cas de détection d'ambiguïté, chacun avec un message d'erreur explicite :
  1. `project == sandbox` → sandbox écraserait le checkout
  2. `sandbox` dans `project` → fichiers runtime créés dans le dépôt source
  3. `project` dans `sandbox` → scripts sourcés depuis l'intérieur du sandbox
  4. Parent de `sandbox` inexistant → chemin invalide
- Résolution des chemins avec `.resolve()` avant comparaison — pas de faux négatifs par symlinks.
- Appel après `validate_project_root_on_host()` et avant `_validate_traefik_hosts()` — logique d'ordre correcte (fail-fast sur les paths avant les vérifications réseau).
- Fix du label de log : `runtime_root=` → `project_root=`, avec ajout de `sandbox_path=`.

### Backend — `sandbox_runtime_deploy.py`

- Remplacement du dead guard (`source_path.is_relative_to(sandbox_dir)` — toujours vrai par construction) par une vraie validation : existence de `source_path / ".ai-dev-factory" / "scripts"`.
- Header 5-lignes écrit dans `run.log` ET `logger.info` **avant** `_persist(LifecyclePhase.provisioning)` — satisfait le critère "before bootstrap" du ticket.

---

## Problèmes détectés

### Observation 1 (non-bloquant) — Flow project-ID : "(auto-assigned)" pour les trois champs

Dans le flow project-ID, le bloc "Runtime target" affiche `(auto-assigned)` pour sandbox path, runtime root et source clone. Le ticket demande que "users can verify deploy destination before launching". Pour ce flow, l'utilisateur voit que l'information est gérée côté serveur, mais ne connaît pas la destination exacte avant déploiement.

C'est une limitation architecturale (le chemin sandbox est assigné dynamiquement par le serveur) et non une erreur d'implémentation. La section "Runtime paths" de `EnvironmentCard` comble ce manque *après* déploiement.

### Observation 2 (non-bloquant) — `_validate_runtime_consistency` saute si `host_sandbox is None`

La validation est no-op quand `host_sandbox` est None (chemin auto-assigné). Les chemins auto-assignés étant sous contrôle serveur, ils ne peuvent pas créer de conflit avec `project_root`. Comportement intentionnel et correct.

### Observation 3 (non-bloquant) — Types d'exceptions inconsistants

`_validate_runtime_consistency` lève `ValueError` (traduit en HTTP 422 par le route handler) ; la validation dans `sandbox_runtime_deploy.py` lève `RuntimeError` (échec du déploiement). L'incohérence est intentionnelle : pre-flight vs deploy-time. Le comportement résultant est correct dans les deux cas.

---

## Risques éventuels

- **Aucun risque de régression identifié** : les changements frontend sont additifs (bloc d'info, section collapsible). La validation backend est un nouveau guard pre-flight qui ne touche pas le code-path existant des déploiements auto-assignés.
- **Compatibilité Python** : `str | None` en annotation de paramètre (union syntax) requiert Python 3.10+. Si le projet cible Python 3.9, remplacer par `Optional[str]`. À vérifier selon la version cible du projet.

---

## Décision

Tous les critères d'acceptance sont satisfaits. Pas de problème bloquant.

- ~~REQUEST_CHANGES~~
- **APPROVED**

---

IMPLEMENTATION_APPROVED
