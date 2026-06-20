I have all the information needed. Let me write the review.

---

# PR Review — T197: Add advisory ticket intelligence analysis before development cycle

## Résumé

L'implémentation est globalement de très bonne qualité : architecture hybride claire (extractor déterministe + subprocess AI), normalisation robuste, gestion des erreurs complète, UI advisory bien balisée, 41 tests sur 4 modules. Un seul problème bloquant est identifié.

## Vérifications effectuées

- Routes backend `services/control_api/routes/intelligence.py` (170 lignes)
- Analyzer `tools/agent_runner/ticket_intelligence_analyzer.py` (310 lignes)
- Extractor `tools/agent_runner/ticket_intelligence_extractor.py` (105 lignes)
- Schémas Pydantic `services/control_api/models/schemas.py` (lignes 440–473)
- Model catalog `tools/agent_runner/model_catalog.py`
- DB functions `tools/agent_runner/runtime_db.py` (lignes 67–96, schema `ticket_intelligence`)
- Enregistrement des routeurs dans `services/control_api/main.py`
- Client API frontend `apps/dashboard/src/api/tickets.js`
- Composant `apps/dashboard/src/components/TicketIntelligencePanel.jsx` (258 lignes)
- Intégration `apps/dashboard/src/pages/TicketDetailPage.jsx`
- Tests : `tests/test_ticket_intelligence_api.py`, `test_ticket_intelligence_db.py`, `test_ticket_intelligence_extractor.py`, `apps/dashboard/tests/TicketIntelligencePanel.test.jsx`
- Pattern existant `services/control_api/routes/tickets.py` → `project_router`

## Points validés

- **Hybrid approach** : `ticket_intelligence_extractor.extract()` est pur Python, déterministe, sans réseau. Il alimente l'AI via `{{computed_signals}}` dans le prompt. L'approche est exactement celle demandée par le ticket.
- **11 signaux déterministes** couvrent tous les exemples listés dans le ticket (risky keywords, affected domains, dependency hints, token size, scheduler/DB migration detection).
- **Normalisation AI** : `_normalize()` clamp les scores 1–10, valide `autonomous_execution_recommendation` contre un frozenset, et fallback cost via `estimate_cost()` si l'AI ne le fournit pas. Robuste.
- **Gestion d'erreur exhaustive** : timeout → failed, rc ≠ 0 → failed, JSON mal formé → failed, exception inattendue → failed. Toujours persisté en DB, jamais swallowed.
- **Table `ticket_intelligence`** : 26 colonnes, correspondance exacte avec les champs demandés par le ticket. `computed_signals_json` stocké pour debug.
- **Advisory badge** affiché en permanence : `"Advisory only — not used by scheduler yet"`.
- **Comportement scheduler inchangé** : aucune modification des tables `ticket_runtime`, `workers`, daemon loop.
- **Cost estimation** avec catalog configurable (`local-qwen` à `advanced-reasoning-model`), sans hardcoding provider-specific.
- **Schemas Pydantic** : `TicketIntelligence` (28 champs, tous Optional sauf `ticket_id` et `analysis_status`) + `TicketIntelligenceQueued`.
- **Tests** : 8 tests API, 10 tests DB, 18 tests extractor, 15 tests composant React — couverture des 4 axes demandés dans les acceptance criteria.
- **Inline prompt fallback** dans `_INLINE_PROMPT` si le fichier prompt est absent — bon pattern défensif.
- **Background daemon thread** : la réponse POST 202 est immédiate, l'analyse tourne en arrière-plan sans bloquer.

## Problèmes détectés

### [BLOQUANT] Absence du `project_router` dans intelligence.py — appels frontend 404 en setup multi-projet

**Localisation** : `services/control_api/routes/intelligence.py` et `services/control_api/main.py:200`

**Pattern existant** (exemple) : `services/control_api/routes/tickets.py`
```python
router = APIRouter(prefix="/tickets", tags=["tickets"])
project_router = APIRouter(prefix="/projects", tags=["tickets"])
# route globale : /tickets/{ticket_id}/...
# route projet   : /projects/{project_id}/tickets/{ticket_id}/...
```
Ces deux routeurs sont enregistrés dans `main.py:178–179` :
```python
app.include_router(tickets.router)
app.include_router(tickets.project_router)
```

**Ce qui est implémenté** dans `intelligence.py` : seulement `router = APIRouter(prefix="/tickets")`, enregistré ligne 200 de `main.py`. Il n'y a pas de `project_router`, et `main.py` n'inclut qu'`intelligence.router`.

**Ce que le frontend envoie** (`apps/dashboard/src/api/tickets.js:31–32`) :
```js
const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''
export const getTicketIntelligence = (id, projectId) =>
  client.get(`${_pfx(projectId)}/tickets/${id}/intelligence`)
export const analyzeTicketIntelligence = (id, projectId) =>
  client.post(`${_pfx(projectId)}/tickets/${id}/intelligence/analyze`)
```

En setup multi-projet (le cas courant du dashboard), `projectId` est fourni → l'appel va vers `/projects/{projectId}/tickets/{id}/intelligence`. Ce chemin n'est pas enregistré → **404 systématique**. Le composant `TicketIntelligencePanel` affiche alors l'erreur réseau à la place du panel.

**Correction attendue** : ajouter dans `intelligence.py` :
```python
project_router = APIRouter(prefix="/projects", tags=["intelligence"])

@project_router.get("/{project_id}/tickets/{ticket_id}/intelligence", response_model=TicketIntelligence)
def get_intelligence_project(project_id: str, ticket_id: str, request: Request) -> TicketIntelligence:
    return get_intelligence(ticket_id, request)

@project_router.post(
    "/{project_id}/tickets/{ticket_id}/intelligence/analyze",
    response_model=TicketIntelligenceQueued,
    status_code=202,
)
def analyze_intelligence_project(project_id: str, ticket_id: str, request: Request) -> TicketIntelligenceQueued:
    return analyze_intelligence(ticket_id, request)
```

Et dans `main.py` :
```python
app.include_router(intelligence.router)
app.include_router(intelligence.project_router)  # à ajouter
```

Les tests API existants testent uniquement le path global (`/tickets/{id}/intelligence`) — il faudra ajouter un ou deux tests sur le path `/projects/{project_id}/tickets/{id}/intelligence`.

---

### [MINEUR] Status `running` peut rester bloqué en DB si le process API redémarre pendant une analyse

**Localisation** : `ticket_intelligence_analyzer.py:231` + `routes/intelligence.py:167`

Lorsque le thread background est tué (restart API), `analysis_status = "running"` reste en base. Au redémarrage suivant, un GET sur ce ticket retourne `analysis_status: "running"` mais aucun thread ne tourne. Le polling frontend reste actif indéfiniment.

Aucun mécanisme de recovery au démarrage (contrairement à ce que font `check_and_recover_db` pour d'autres états). Le composant React ne detects pas ce cas (il continue de poller si `status ∈ {queued, running}`).

Acceptable pour une feature advisory en V1, mais à noter.

---

### [MINEUR] Aucune garde contre analyses concurrentes sur le même ticket

**Localisation** : `routes/intelligence.py:142–170`

Deux POST successifs rapides sur le même ticket lancent deux threads. Le dernier à écrire en DB l'emporte (`upsert`). Pas de vérification `IF analysis_status = 'queued' OR 'running' → reject`.

Impact faible (résultat identique, léger surcoût), mais une idempotency guard simple (`if status in {"queued", "running"}: return 202 early`) serait plus propre.

---

### [MINEUR] `changes_scheduler` tokenise par espaces — rate les identifiants composites

**Localisation** : `ticket_intelligence_extractor.py:89`
```python
changes_scheduler = bool(_SCHEDULER_KEYWORDS & set(lower.split()))
```

Si le ticket contient `"run_daemon"` ou `"scheduler_config"`, `lower.split()` donne `["run_daemon", "scheduler_config"]`. `"scheduler"` n'est pas dans ce set. La ligne 43 inclut `"run_daemon"` dans `_SCHEDULER_KEYWORDS`, mais `"scheduler"` seul ne matcherait pas `"scheduler_config"`.

Correction triviale : remplacer par un check substring comme les autres signaux :
```python
changes_scheduler = any(kw in lower for kw in _SCHEDULER_KEYWORDS)
```

---

## Risques éventuels

- **Divergence SQLite/PostgreSQL** : `runtime_db.py` et `runtime_db_pg.py` ont des signatures identiques mais leurs schémas diffèrent légèrement (`project_id` présent seulement en PG). L'API ne passe pas `project_id` à `upsert_ticket_intelligence` — c'est acceptable en SQLite, mais à surveiller si le backend PG est activé en prod multi-projet.
- **Subprocess AI sans isolation de processus** : le thread background appelle `subprocess.run(exec_cmd)` dans le même process uvicorn. Un crash du subprocess ne tue pas l'API, mais des fuites de descripteurs de fichiers sur haute charge (beaucoup d'analyses simultanées) sont possibles.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **[BLOQUANT]** Ajouter `project_router` dans `intelligence.py` avec les deux routes project-scoped (`/{project_id}/tickets/{ticket_id}/intelligence` GET et POST). Enregistrer `intelligence.project_router` dans `main.py` après `intelligence.router`. Ajouter au moins un test API couvrant le path `/projects/{project_id}/tickets/{ticket_id}/intelligence`.

2. **[MINEUR — recommandé]** Corriger `changes_scheduler` pour utiliser `any(kw in lower for kw in _SCHEDULER_KEYWORDS)` à la place de l'intersection sur `lower.split()`.

3. **[MINEUR — optionnel V1]** Ajouter une idempotency guard au POST `/analyze` : si `analysis_status` est déjà `queued` ou `running`, retourner 202 sans lancer un nouveau thread.

IMPLEMENTATION_FIX_REQUIRED
