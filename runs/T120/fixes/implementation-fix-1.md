# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T120/reviews/implementation-review.md
- generated at: 2026-05-21T07:37:58Z

---

Now I have everything I need to write the review.

---

# PR Review — T120: Dashboard Runtime Status

## Résumé

Implémentation de l'exposition des informations de retry et de la dernière erreur runtime dans l'API de contrôle et le dashboard. Quatre fichiers cibles modifiés correctement. Un fichier hors-scope modifié de manière significative.

## Vérifications effectuées

- Lecture complète du plan (`runs/T120/plan.md`) et comparaison avec l'implémentation
- Lecture de `services/control_api/models/schemas.py`
- Lecture de `services/control_api/services/artifact_reader.py`
- Lecture de `apps/dashboard/src/pages/TicketDetailPage.jsx`
- Lecture de `apps/dashboard/src/components/WorkflowTimeline.jsx`
- `git diff main --name-only` pour identifier tous les fichiers modifiés
- `git diff main -- prompts/generic/planner.md` pour analyser la modification hors-scope

## Points validés

**Backend — schemas.py**
- `RetryInfo` correctement défini (`failure_class: str | None`, `retry_count: int = 0`, `cooldown_until: str | None`) ✓
- `TicketSummary.retry_info: RetryInfo | None` ajouté ✓
- `TimelineResponse.retry_info: RetryInfo | None` et `last_error: str | None` ajoutés ✓
- Rétrocompatibilité maintenue : tous les nouveaux champs sont optionnels ✓

**Backend — artifact_reader.py**
- `_read_retry_state(run_dir)` : lit `retry-state.json`, gère l'absence du fichier, `json.JSONDecodeError`, `OSError`, `ValueError` ✓
- `_read_last_error(run_dir)` : scan inverse de `runtime.log`, retourne le dernier log contenant `"ERROR"` ✓
- `get_ticket()` enrichi avec `retry_info` ✓
- `get_ticket_timeline()` enrichi avec `retry_info` et `last_error` ✓
- `routes/tickets.py` non modifié — correct : l'enrichissement est fait dans artifact_reader.py, les routes retournent déjà les modèles complets ✓
- `list_tickets()` non modifié — correct selon le plan (performance) ✓

**Frontend — TicketDetailPage.jsx**
- `TAB_FETCHERS.overview` pointe vers `api.getTicketTimeline` ✓
- `OverviewTab` affiche `retry_count`, `failure_class`, `cooldown_until` quand `retry_info` est présent ✓
- `OverviewTab` affiche `last_error` en rouge quand présent ✓
- Fallback affiché quand ni retry_info ni last_error ✓
- Tab `overview` inclus dans le polling auto-refresh (ligne 87) ✓

**Frontend — WorkflowTimeline.jsx**
- Annotation rouge sur les steps `failed` quand `retry_info` est présent ✓
- Format `attempt N — failure_class` ou `attempt N` si pas de failure_class ✓

## Problèmes détectés

### [BLOQUANT] — Modification hors-scope : `prompts/generic/planner.md`

Le plan T120 liste exactement 4 fichiers cibles :
- `services/control_api/models/schemas.py`
- `services/control_api/services/artifact_reader.py`
- `apps/dashboard/src/pages/TicketDetailPage.jsx`
- `apps/dashboard/src/components/WorkflowTimeline.jsx`

Or `prompts/generic/planner.md` a été modifié avec +50 lignes de contenu entièrement nouveau : restructuration du prompt planner pour enforcer un format strict de sortie (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`), avec validation et exemple minimal.

Ce changement est :
- absent du plan T120
- absent des critères d'acceptation
- structurellement différent du scope (infrastructure factory, pas dashboard/API)
- potentiellement impactant sur tous les tickets futurs

### [MINEUR] — Annotation de retry sur tous les steps failed

`WorkflowTimeline.jsx` affiche l'annotation retry sur **tous** les steps en état `failed` quand `retry_info` est présent. Comme `retry_info` est un champ de niveau ticket (pas step), cela peut être légèrement trompeur si plusieurs steps sont failed simultanément. En pratique la machine d'état ne produit qu'un seul step failed à la fois — risque négligeable.

### [MINEUR] — Lecture intégrale du log en mémoire

`_read_last_error` charge l'intégralité de `runtime.log` en mémoire avant de scanner en reverse. Pour les runs longues avec de gros logs, cela pourrait être coûteux. Acceptable à l'échelle actuelle.

## Risques éventuels

La modification de `prompts/generic/planner.md` dans cette PR présente un risque indirect : si ce changement introduit une incompatibilité avec le validateur de plan actuel (ou si le validateur n'existe pas encore), tous les tickets futurs pourraient être affectés. Ce changement mérite sa propre revue dans un ticket dédié.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **Obligatoire** : Reverter `prompts/generic/planner.md` de cette PR et créer un ticket dédié pour cette amélioration du prompt planner. La modification est valide dans son contenu mais hors du périmètre T120.

2. **Optionnel** : Documenter dans un commentaire ou ticket séparé le comportement de `_read_last_error` par rapport au format exact du log (substring match sur `"ERROR"` case-sensitive) pour faciliter la maintenance future.

---

IMPLEMENTATION_FIX_REQUIRED
