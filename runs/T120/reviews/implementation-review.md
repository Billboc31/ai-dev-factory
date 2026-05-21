---

# PR Review — T120: Dashboard Runtime Status (attempt 2)

## Résumé

Seconde review après application du correctif `IMPLEMENTATION_FIX_REQUIRED`. Le revert de `prompts/generic/planner.md` est confirmé : **0 ligne de diff vs main**. Les 4 fichiers cibles sont corrects et conformes au plan.

## Vérifications effectuées

- `git diff main HEAD -- prompts/generic/planner.md` → 0 lignes (revert complet) ✓
- `git diff main HEAD --name-only` → seuls les 4 fichiers cibles + artefacts `runs/T120/` modifiés ✓
- Lecture complète des 4 fichiers de production modifiés
- Comparaison avec le plan `runs/T120/plan.md` et les critères d'acceptation

## Points validés

**Correctif**
- `prompts/generic/planner.md` identique à `main` — revert confirmé ✓

**Backend — schemas.py**
- `RetryInfo` avec `failure_class`, `retry_count`, `cooldown_until` ✓
- `TicketSummary.retry_info: RetryInfo | None` ✓
- `TimelineResponse.retry_info` et `last_error: str | None` ✓
- Rétrocompatibilité : tous les champs optionnels ✓

**Backend — artifact_reader.py**
- `_read_retry_state(run_dir)` : lit `retry-state.json`, gère absence + erreurs JSON/OS/ValueError ✓
- `_read_last_error(run_dir)` : scan inverse de `runtime.log`, retourne le dernier log contenant `"ERROR"` ✓
- `get_ticket()` et `get_ticket_timeline()` enrichis correctement ✓
- Enrichissement dans la couche service (pas dans les routes) — fonctionnellement équivalent, architecture plus propre ✓

**Frontend — TicketDetailPage.jsx**
- `TAB_FETCHERS.overview` → `api.getTicketTimeline(id)` ✓
- `OverviewTab` : rendu retry_count, failure_class, cooldown_until, last_error ✓
- Tab `overview` inclus dans le polling auto-refresh (ligne 87) ✓

**Frontend — WorkflowTimeline.jsx**
- Annotation inline `attempt N — failure_class` sur steps `failed` ✓

## Critères d'acceptation — tous couverts

| Critère | Statut |
|---|---|
| `GET /api/tickets/{id}` inclut `retry_info` | ✓ |
| `GET /api/tickets/{id}/timeline` inclut `retry_info` et `last_error` | ✓ |
| Dashboard overview tab : retry count, failure class, cooldown | ✓ |
| Dashboard overview tab : last error | ✓ |
| WorkflowTimeline annote les steps failed | ✓ |
| Contrat API inchangé (champs nullable) | ✓ |
| Aucune nouvelle route top-level | ✓ |

## Observations mineures (non bloquantes)

- Match `"ERROR"` case-sensitive non borné dans `_read_last_error` — suffisant au format log actuel
- Log chargé en mémoire avant scan inverse — acceptable à l'échelle actuelle
- Annotation retry sur tous les steps failed (ticket-level) — en pratique un seul step failed simultanément

## Problèmes bloquants

Aucun. Le correctif demandé lors de la première review a été appliqué correctement.

---

IMPLEMENTATION_APPROVED
