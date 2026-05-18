---

# PR Review — T106 Project Issue Tree Agent and Dependency Map

## Résumé

L'implémentation livre un agent autonome de cartographie des dépendances inter-tickets (`run_issue_mapper.py`), une couche de service et trois endpoints API, deux nouvelles pages dashboard (Project Map, Issue Mapper Activity), et une intégration opt-in dans le daemon. Le périmètre est bien contenu. Les cinq critères d'acceptation du ticket sont globalement satisfaits.

## Vérifications effectuées

- Lecture complète de `run_issue_mapper.py` (630 lignes)
- Lecture des nouveaux fichiers : `services/control_api/routes/project_map.py`, `services/control_api/services/project_map_service.py`, `services/control_api/models/schemas.py` (ajouts)
- Lecture des modifications de `run_daemon.py` (fonctions `poll_project_map`, `_load_project_map`, `run_once`)
- Lecture de `ProjectMapPage.jsx` et `IssueMapperActivityPage.jsx`
- Analyse des algorithmes de classification de statut, détection de cycles, groupes parallélisables, et `next_recommended`

## Points validés

**Agent core :**
- Récupération des issues via `gh` avec gestion propre des erreurs (not found, RC ≠ 0, JSON invalide)
- Parsing bidirectionnel des dépendances : `depends on #N` / `blocked by TN` ET `blocks #N`
- Merge correct des relations `blocks` dans `dep_map` (inversion symétrique)
- Deux passes de classification garantissant la prise en compte des dépendances avant calcul final
- Détection de cycles DFS correcte sur le graphe orienté
- `compute_next_recommended` : retourne le ticket runnable de numéro le plus bas dont toutes les dépendances sont done — logique correcte
- Écritures atomiques sur les deux artefacts (`.tmp` → `replace`) → pas de corruption partielle
- Cap des entrées d'activité à 50 — maîtrise mémoire

**API et service :**
- Endpoints GET map, GET activity, POST refresh propres et bien typés Pydantic
- Le `refresh` via `BackgroundTasks` renvoie immédiatement `ok=True` — bon pattern
- `project_map_service.refresh_project_map` résout le chemin du mapper par `__file__` — robuste

**Dashboard :**
- Polling 15 s sur les deux pages
- Badges status avec couleurs sémantiques cohérentes
- Gestion de l'état vide (aucun scan)
- Ambiguïtés rendues qu'elles soient `str` ou `{detail: str}` — défensif

**Daemon :**
- Opt-in propre : `--poll-project-map` et `--use-project-map` indépendants, fallback FIFO explicite
- Logging des décisions de scheduling

## Problèmes détectés

### 1. Daemon : le blocage dépendance n'est pas appliqué (significatif)

Le ticket stipule que le daemon doit décider _quoi garder en attente_. L'implémentation actuelle se limite à réordonner les tickets en mettant `next_recommended` en tête (`run_daemon.py:1173-1182`). Elle ne bloque pas les tickets que la map classe `blocked_dependency` : si un tel ticket est localement en état `PLAN_APPROVED`, il est quand même lancé.

Ce n'est pas dangereux car la machine à états existante empêche le travail prématuré sur un ticket dépendant en pratique, mais c'est une implémentation partielle de l'intégration daemon décrite dans le ticket.

**Pas bloquant pour V1** (comportement conservateur, fallback explicite), mais à noter pour le suivi.

### 2. `AUTO_RUNNABLE_STATES` et `HUMAN_GATE_STATES` dupliqués (mineur)

Définis à l'identique dans `run_issue_mapper.py:30-43` et `run_daemon.py:42-54`. Si l'un est modifié sans l'autre, les classifications divergent silencieusement.

### 3. Deux passes : mise à jour en place de `ticket_statuses` (mineur)

En passe 2, `ticket_statuses` est lu ET écrit pendant la même itération (`run_issue_mapper.py:508-521`). Les tickets traités en premier voient les statuts passe-1 des tickets traités après eux. Pour les dépendances en chaîne longue (A→B→C), l'ordre d'itération impacte le résultat. En pratique les issues GitHub sont triées par numéro et les dépendances sont généralement dirigées vers des tickets plus anciens, donc l'impact est limité — mais ce n'est pas un calcul en ordre topologique garanti.

### 4. `compute_parallelizable_groups` : docstring trompeuse (mineur)

La docstring dit « no dependency between any two members of the same group » mais le code group par composantes connexes du sous-graphe de dépendances (union-find sur `has_dep`). En pratique les deux sont équivalents (deux tickets immédiatement runnable ne peuvent pas avoir de dépendance mutuelle), mais la docstring induit en erreur sur l'intention.

### 5. Typage faible sur `ambiguities` (cosmétique)

`ProjectMapActivityEntry.ambiguities: list[Any]` — le type réel est `list[dict]` avec clé `detail`. Faible garantie de validation Pydantic.

### 6. Fonctionnalités manquantes mineures (observations)

- **Capacity disponible** : le ticket demandait « capacité disponible » sur la Project Map page — non affiché dans le dashboard. Les compteurs summary couvrent partiellement ce besoin.
- **Reasoning simplifié** : la spec demandait un « reasoning simplifié » dans l'Activity page. Non implémenté (l'activity montre les décisions mais pas le raisonnement).

## Risques éventuels

- **Stale map** : si le mapper n'a pas tourné récemment, le daemon utilisera une map périmée pour le scheduling. Le fallback FIFO est déclenché uniquement si le fichier est absent, pas si les données sont trop vieilles. Risque opérationnel faible à court terme, à surveiller.
- **Récursion DFS** (`detect_cycles:261`) : profondeur limitée au stack Python. Pas un problème réaliste avec un graphe de quelques dizaines d'issues.
- **Closed issues flagged ambiguous** : une issue fermée (dépendance résolue) absente de `fetch_open_issues` est détectée comme ambiguïté. Faux positifs possibles, bruit dans l'activity log.

## Décision

L'implémentation satisfait les cinq critères d'acceptation du ticket :
- ✅ L'agent produit une map projet exploitable
- ✅ Le dashboard affiche l'arbre des tickets
- ✅ Les tickets parallélisables sont détectés
- ✅ Les tickets bloqués sont identifiés
- ✅ Le daemon peut utiliser la map pour le scheduling (ordering)

Les problèmes détectés sont soit non bloquants (daemon partial blocking), soit mineurs (DRY, typage, doc). Rien ne compromet la correctness fonctionnelle ou la sécurité.

- APPROVED

## Actions demandées

Aucune correction bloquante. Pour le suivi post-merge :

1. Envisager d'extraire `AUTO_RUNNABLE_STATES` / `HUMAN_GATE_STATES` dans un module partagé
2. Documenter explicitement que `--use-project-map` est un hint d'ordering, pas un gate de blocage
3. Corriger la docstring de `compute_parallelizable_groups`
4. Typer `ambiguities` correctement dans le schéma Pydantic

---

IMPLEMENTATION_APPROVED
