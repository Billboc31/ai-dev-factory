# PR Review — T120: Dashboard Runtime Status (attempt 2)

## Résumé

Seconde review après application du correctif `IMPLEMENTATION_FIX_REQUIRED`. La modification hors-scope de `prompts/generic/planner.md` a été revertée (0 ligne de diff vs main confirmé). L'implémentation des 4 fichiers cibles est correcte, complète et conforme au plan.

## Vérifications effectuées

- `git diff main HEAD -- prompts/generic/planner.md` → 0 lignes (identique à main) ✓
- `git diff main HEAD --name-only` → seuls les 4 fichiers cibles + artefacts `runs/T120/` modifiés ✓
- Lecture complète de `services/control_api/models/schemas.py`
- Lecture complète de `services/control_api/services/artifact_reader.py`
- Lecture complète de `apps/dashboard/src/pages/TicketDetailPage.jsx`
- Lecture complète de `apps/dashboard/src/components/WorkflowTimeline.jsx`
- Lecture du plan `runs/T120/plan.md` et comparaison avec l'implémentation

## Points validés

**Correctif appliqué**
- `prompts/generic/planner.md` identique à `main` — revert complet confirmé ✓
- Commit `a62d19f` présent dans l'historique ✓

**Backend — schemas.py**
- `RetryInfo` : `failure_class: str | None`, `retry_count: int = 0`, `cooldown_until: str | None` ✓
- `TicketSummary.retry_info: RetryInfo | None` ✓
- `TimelineResponse.retry_info: RetryInfo | None` et `last_error: str | None` ✓
- Rétrocompatibilité : tous les champs optionnels, contrat API existant inchangé ✓

**Backend — artifact_reader.py**
- `_read_retry_state(run_dir)` : lit `retry-state.json`, retourne `None` si absent, gère `json.JSONDecodeError`, `OSError`, `ValueError` ✓
- `_read_last_error(run_dir)` : scan inverse de `runtime.log`, retourne le dernier log contenant `"ERROR"`, retourne `None` si absent ✓
- `get_ticket()` : enrichi avec `retry_info=_read_retry_state(run_dir)` ✓
- `get_ticket_timeline()` : enrichi avec `retry_info` et `last_error` ✓
- Enrichissement dans la couche service plutôt que dans les routes — architecture plus propre, fonctionnellement équivalent au plan ✓
- `routes/tickets.py` non modifié — correct, les routes retournent les modèles enrichis via les fonctions service ✓

**Frontend — TicketDetailPage.jsx**
- `TAB_FETCHERS.overview` → `api.getTicketTimeline(id)` ✓
- `OverviewTab` : rendu de `retry_count`, `failure_class`, `cooldown_until` quand `retry_info` présent ✓
- `OverviewTab` : rendu de `last_error` dans encadré rouge quand présent ✓
- Fallback "No retry or error information available." quand les deux sont absents ✓
- Tab `overview` inclus dans le polling auto-refresh (ligne 87) ✓
- Comportement cohérent avec les tabs `timeline` et `logs` pour le clear on state change ✓

**Frontend — WorkflowTimeline.jsx**
- Annotation inline sur les steps `failed` quand `retry_info` présent ✓
- Format : `attempt N` ou `attempt N — failure_class` ✓
- Style : rouge, monospace, taille xs, positionné avant le nom d'agent ✓

## Critères d'acceptation — couverture complète

| Critère | Statut |
|---------|--------|
| `GET /api/tickets/{id}` inclut `retry_info` si `retry-state.json` existe | ✓ |
| `GET /api/tickets/{id}/timeline` inclut `retry_info` et `last_error` | ✓ |
| Dashboard overview tab : retry_count, failure_class, cooldown_until | ✓ |
| Dashboard overview tab : last error message | ✓ |
| WorkflowTimeline annote les steps failed avec attempt et failure_class | ✓ |
| Contrat API existant inchangé (nouveaux champs nullable/optional) | ✓ |
| Aucune nouvelle route top-level | ✓ |

## Observations mineures (non bloquantes)

- **Match `"ERROR"` case-sensitive non borné** : `_read_last_error` retourne toute ligne contenant le substring `"ERROR"`. Suffisant au format log actuel.
- **Log chargé en mémoire** : `_read_last_error` charge l'intégralité de `runtime.log` avant scan inverse. Acceptable à l'échelle actuelle.
- **Annotation retry sur tous les steps failed** : `retry_info` est ticket-level. En pratique un seul step failed simultanément — risque visuel négligeable.

## Problèmes détectés

Aucun problème bloquant. Le correctif demandé lors de la première review a été appliqué correctement.

## Décision

L'implémentation est conforme au ticket, au plan et aux critères d'acceptation. Scope respecté. Qualité de code satisfaisante. Pas de problème de sécurité.

IMPLEMENTATION_APPROVED
