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


# T197 — Add advisory ticket intelligence analysis before development cycle

**Source**: GitHub Issue #251

## Description

# Add advisory ticket intelligence analysis before development cycle

## Context

AI Dev Factory now has a real database and can persist structured metadata per ticket.

Before a ticket enters the normal development cycle, we want to run an analysis agent that classifies the ticket and stores useful decision data.

This step must not influence scheduling or execution yet. For now, it only enriches each ticket with analysis metadata and displays it on the ticket detail page.

This is intended to prepare future scheduling, model routing, cost control, dependency handling, and parallel execution decisions.

## Goal

Add a new pre-development analysis step that evaluates each ticket and stores advisory intelligence metadata.

The analysis should include:

- estimated difficulty
- risk level
- implementation complexity
- expected AI model needed
- explanation of model choice
- estimated cost range
- recommended queue order
- dependency hints
- whether human plan review is required
- whether human code review is required
- whether the ticket looks safe for autonomous execution

## Important design requirement: hybrid analysis

The analyzer must use AI for reasoning, classification, and recommendation, but it should not rely only on AI.

Some deterministic or semi-deterministic parts should be computed in code, likely Python, because AI is not the best tool for every signal.

Examples of non-AI / Python-computed signals:

- ticket text length
- number of explicit requirements
- number of acceptance criteria
- presence of risky keywords such as `database`, `migration`, `scheduler`, `auth`, `security`, `deployment`, `multi-project`, `worker`, `daemon`
- detected affected domains: backend, frontend, database, infra, orchestration, UI, tests
- dependency references like `depends on`, `after T001`, `requires`, `blocked by`
- number of linked issues or ticket IDs mentioned
- estimated token size
- rough file-impact estimate from keywords or repository search
- whether the ticket changes scheduler/runtime behavior
- whether it likely needs DB migration

The AI should then consume these computed signals plus the ticket content and produce the final advisory classification.

Suggested flow:

```text
Ticket created / refreshed
↓
Python deterministic feature extractor
↓
AI Ticket Intelligence Analyzer
↓
JSON validation / normalization
↓
Persist analysis in DB
↓
Display on ticket page
```

## Non-goals

Do not change the current ticket execution behavior yet.

This ticket must not:

- block ticket execution
- reorder the queue automatically
- enforce dependencies
- change worker scheduling
- prevent agents from starting
- implement parallel execution rules
- automatically choose the model for execution

Those behaviors will be handled in later tickets.

## New concept

Introduce a new agent step:

```text
Ticket Intelligence Analyzer
```

It runs before the normal development cycle:

```text
Ticket created
↓
Ticket Intelligence Analyzer
↓
Planning
↓
Coding
↓
Review
↓
Testing
↓
Deployment
```

For now, the analyzer is informational only.

## Data to store

For each ticket, persist an analysis record in the database.

Suggested fields:

```text
ticket_id
analysis_status
difficulty_score
difficulty_label
risk_score
risk_label
complexity_factors
computed_signals_json
recommended_model
recommended_model_reason
estimated_input_tokens
estimated_output_tokens
estimated_cost_min
estimated_cost_max
cost_currency
cost_estimate_status
queue_rank
queue_reason
dependency_hints
parallel_safe_candidate
requires_human_plan_review
human_plan_review_reason
requires_human_code_review
human_code_review_reason
autonomous_execution_recommendation
analysis_summary
created_at
updated_at
```

## Difficulty scoring

The analyzer should compute a difficulty score from 1 to 10.

Example labels:

```text
1-2  trivial
3-4  simple
5-6  medium
7-8  complex
9-10 critical
```

The score should consider both deterministic signals and AI reasoning:

- number of files likely impacted
- database changes
- architecture changes
- frontend/backend scope
- tests required
- deployment impact
- security impact
- scheduler/runtime impact
- dependency on previous tickets
- ambiguity of requirements
- risk of breaking existing behavior

## Risk scoring

The analyzer should compute a risk score from 1 to 10.

Risk factors include:

- changes to scheduler / worker orchestration
- changes to project isolation
- changes to database schema
- changes to deployment/runtime
- security/auth concerns
- changes that affect multiple projects
- stale-branch or dependency-sensitive work
- unclear acceptance criteria

## Model recommendation

The analyzer should recommend the most appropriate AI model for the ticket.

Example output:

```text
recommended_model: advanced-reasoning-model
recommended_model_reason: Requires architecture reasoning, dependency analysis, and careful backend implementation planning.
```

The model choice should consider:

- ticket complexity
- amount of reasoning needed
- need for code generation
- need for review accuracy
- expected token usage
- acceptable cost
- risk level
- whether a local model may be sufficient

The implementation should keep the model catalog configurable.

Example model catalog:

```text
local-qwen
cheap-fast-model
balanced-code-model
advanced-reasoning-model
```

No hardcoded provider-specific logic should be required at this stage.

## Cost estimation

The analyzer should estimate cost using:

```text
estimated input tokens
estimated output tokens
selected model pricing
```

If pricing is unknown, store:

```text
cost_estimate_status: unknown
```

The cost estimate can be approximate.

Example:

```text
estimated_cost_min: 0.05
estimated_cost_max: 0.35
cost_currency: USD
```

## Queue rank recommendation

The analyzer should propose a queue rank for the ticket.

This is only advisory for now.

It should consider:

- explicit dependencies
- detected dependency hints
- ticket difficulty
- foundational tickets first
- architecture/setup tickets before feature tickets
- blocking tickets before dependent tickets
- low-risk independent tickets may be good early candidates

Example:

```text
queue_rank: 20
queue_reason: Backend foundation should run before CRUD API and frontend integration tickets.
```

## Human review recommendation

The analyzer should decide whether the ticket likely needs human plan review.

Examples requiring human plan review:

- architecture decision
- dependency or scheduler changes
- database schema change
- security/auth change
- deployment change
- multi-project orchestration
- high cost/risk ticket
- ambiguous requirements

Example:

```text
requires_human_plan_review: true
human_plan_review_reason: The ticket changes scheduler behavior and may affect all project runs.
```

## UI requirements

On the ticket detail page, display a new section:

```text
Ticket Intelligence
```

It should show:

- difficulty label and score
- risk label and score
- recommended model
- estimated cost range
- queue rank recommendation
- human plan review recommendation
- human code review recommendation
- autonomous execution recommendation
- analysis summary
- last analysis date

The UI should clearly indicate that this analysis is advisory only.

Example badge:

```text
Advisory only — not used by scheduler yet
```

## API requirements

Expose the analysis through the existing ticket API.

Suggested endpoints:

```text
GET /api/tickets/:ticketId/intelligence
POST /api/tickets/:ticketId/intelligence/analyze
```

The POST endpoint should run or re-run the analyzer for a ticket.

## Database requirements

Add a table for ticket intelligence analysis.

Suggested table:

```text
ticket_intelligence
```

It should be linked to the existing ticket record.

Only one current analysis per ticket is required for now.

Historical analysis versions are optional and can be added later.

## Agent prompt

Create a prompt for the Ticket Intelligence Analyzer.

The prompt should instruct the agent to return structured JSON with fields like:

```json
{
  "difficulty_score": 6,
  "difficulty_label": "medium",
  "risk_score": 5,
  "risk_label": "moderate",
  "complexity_factors": ["backend", "database", "UI"],
  "recommended_model": "advanced-reasoning-model",
  "recommended_model_reason": "Requires architecture reasoning, dependency analysis, and careful backend implementation planning.",
  "estimated_input_tokens": 12000,
  "estimated_output_tokens": 6000,
  "estimated_cost_min": 0.05,
  "estimated_cost_max": 0.35,
  "cost_currency": "USD",
  "cost_estimate_status": "estimated",
  "queue_rank": 20,
  "queue_reason": "Backend foundation should run before CRUD API and frontend integration tickets.",
  "dependency_hints": ["T001"],
  "requires_human_plan_review": true,
  "human_plan_review_reason": "The ticket changes scheduler behavior and may affect all project runs.",
  "requires_human_code_review": false,
  "parallel_safe_candidate": false,
  "autonomous_execution_recommendation": "plan_review_required",
  "analysis_summary": "This ticket is medium difficulty and moderate risk because it touches backend persistence and UI display but does not yet affect scheduling."
}
```

## Acceptance criteria

- A ticket can be analyzed before entering the dev cycle.
- Analysis results are stored in the database.
- Re-running the analysis updates the stored result.
- The ticket detail page displays the analysis.
- The analysis includes difficulty, risk, model recommendation, cost estimate, queue rank, dependency hints, and human review recommendation.
- The analyzer uses a hybrid approach: deterministic feature extraction in code plus AI-based classification/recommendation.
- Computed deterministic signals are persisted or visible enough for debugging.
- The current scheduler behavior is unchanged.
- No ticket is blocked, reordered, or auto-routed based on this analysis yet.
- The UI clearly states that the analysis is advisory only.
- Tests cover database persistence, API response, analyzer normalization, and UI rendering.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

38 Python tests + 17 frontend tests all pass. The implementation is complete.

---

## Review

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

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T197/reviews/implementation-review.md
- generated at: 2026-06-20T06:46:23Z

---

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