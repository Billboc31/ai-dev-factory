Now I have everything needed. Writing the review.

---

# PR Review — T150: Local DNS and Reverse Proxy for Sandbox Environments

## Résumé

Implémentation d'une couche de reverse proxy Traefik pour les sandbox environments. 3 nouveaux fichiers, 5 fichiers modifiés. Le périmètre est conforme au ticket et au plan approuvé.

## Vérifications effectuées

- Lecture complète de `proxy_manager.py`, `traefik.yml`, `docker-compose.yml`
- Lecture des modifications `sandbox_manager.py` (start/destroy), `sandbox.py`, `SandboxPanel.jsx`, `SandboxRunsTable.jsx`
- Lecture de la suite de tests `tests/test_proxy_manager.py` (12 tests)
- Comparaison plan vs implémentation fichier par fichier

## Points validés

**Architecture et scope**
- Implémentation conforme au plan approuvé : tous les fichiers prévus sont présents
- `ProxyManager` correctement isolé dans un service dédié, sans couplage inutile
- Routing générique et project-agnostic : noms de fichiers route basés sur `sandbox_id` uniquement
- Rétrocompatibilité maintenue : `urls: dict[str, str] = {}` avec valeur par défaut vide, fallback sur `PortsTable` dans les deux composants UI

**Lifecycle**
- `register()` appelé dans `start()` uniquement en cas de succès Docker Compose (ligne 184 sandbox_manager.py)
- `unregister()` appelé dans `destroy()` avant undeploy (ligne 349), ordre correct
- Écriture atomique : temp file + rename empêche Traefik de lire un fichier incomplet

**Qualité de code**
- `ProxyManager` : 92 lignes, fonctions courtes, nommage explicite
- Logs informatifs sans bruit : `logger.info("proxy route registered: ...")`, `logger.info("proxy route unregistered: ...")`
- Pas de dépendance externe ajoutée : Traefik via Docker, `proxy_manager.py` utilise uniquement `pathlib` et `logging`
- `_dashboard.yml` seedé à l'init mais jamais écrasé si existant (test couvert)

**Tests**
- 12 tests unitaires couvrant : création, suppression, idempotence, sandbox concurrents, fichier manquant, unicité des hostnames, seed du dashboard
- Tests avec `tmp_path` pytest, aucune dépendance Docker/Traefik requise

**Sécurité**
- Aucun secret hardcodé
- `sandbox_id` est un `uuid.uuid4().hex` (hex lowercase uniquement) : pas de risque de path traversal dans le nom de fichier route
- `insecure: true` sur le dashboard Traefik : acceptable pour un outil local uniquement
- Liens ouverts avec `rel="noopener noreferrer"` dans les deux composants UI

**Dashboard**
- `SandboxPanel.jsx` : `UrlsTable` avec liens cliquables, fallback sur `PortsTable`
- `SandboxRunsTable.jsx` : colonne renommée "Access", affichage URL ou ports selon disponibilité

## Problèmes détectés

**Observation 1 (non-bloquant) — Routes persistantes sur `stop()`**
`stop()` ne fait pas appel à `unregister()`. Les routes Traefik restent actives quand un sandbox est stoppé. Un utilisateur cliquant sur l'URL d'un sandbox stoppé obtiendra une erreur 502 (Traefik ne trouve aucun service en écoute) au lieu d'une 404. Le dashboard affiche toujours les URLs comme cliquables.

C'est un choix de design explicite dans le plan (unregister uniquement dans `destroy()`), cohérent avec l'acceptance criterion "persistent environments remain reachable after worker exit". Le comportement est prévisible pour quelqu'un qui connaît l'architecture. Non-bloquant.

**Observation 2 (non-bloquant) — Chemin du fichier de tests**
Le plan spécifie `services/control_api/tests/test_proxy_manager.py`, le fichier est placé à `tests/test_proxy_manager.py`. Aucun impact fonctionnel, les tests fonctionnent via `sys.path.insert`.

**Observation 3 (non-bloquant) — Affichage Access dans SandboxRunsTable**
La colonne "Access" affiche uniquement le nom du service ("web", "api") comme texte du lien, pas l'URL complète. `SandboxPanel.jsx` affiche l'URL complète. Légère incohérence UI, non-bloquante.

## Risques éventuels

- **HTTPS non implémenté** : explicitement déféré dans le plan. Les browsers modernes considèrent `.localhost` comme contexte sécurisé, acceptable.
- **`host.docker.internal`** : fonctionne nativement sur macOS/Windows, nécessite l'`extra_hosts` pour Linux (ajouté dans docker-compose.yml). Couvert.
- **Pas de dnsmasq/resolver système** : le plan s'appuie sur la résolution native `*.localhost` des browsers modernes. Safari peut poser problème (résolution non garantie sans `/etc/resolver`). Risque documenté et accepté dans le plan.

## Décision

- APPROVED

Implémentation propre, bornée au scope du ticket, conforme au plan, bien testée. Les observations sont mineures et ne justifient pas de correction avant merge.

## Actions demandées

Aucune correction requise. Les observations peuvent être adressées dans de futurs tickets si nécessaire :
- T150-follow-up : Comportement URL sur sandbox stoppé (vider `urls` dans state ou appeler `unregister` sur `stop()`)
- T150-follow-up : Support Safari via `/etc/resolver` si besoin identifié

IMPLEMENTATION_APPROVED
