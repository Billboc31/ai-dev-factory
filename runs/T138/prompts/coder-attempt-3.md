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


# T138 — T138 — Generic AI sandbox auto-fix loop

**Source**: GitHub Issue #124

## Description

# Objective

Add a generic AI-driven sandbox auto-fix loop able to analyze sandbox deployment failures, modify operational artifacts, rerun validation, and converge toward a successful runtime state.

The implementation must remain generic and must NOT contain ai-dev-factory-specific deployment assumptions.

## Context

T134 introduced sandbox deploy validation.

T137 introduces:
- isolated sandbox ports
- sandbox env files
- compose project isolation
- sandbox lifecycle management
- historical sandbox runs

The next step is an automated correction loop:

sandbox validation fails
→ logs captured
→ AI analyzes failure
→ AI modifies scripts/config
→ sandbox reruns
→ repeat until success or retry limit

## Included

### Generic auto-fix orchestration

- Add a sandbox auto-fix orchestrator.
- Retry loop must be bounded with configurable max retries.
- Each iteration must:
  - capture sandbox state
  - capture logs
  - capture operational scripts
  - call the configured AI runtime
  - apply modifications
  - rerun sandbox validation

### Generic project support

The loop must NOT assume:
- ai-dev-factory project structure
- api/web services
- fixed ports
- docker-only projects
- specific frameworks

The loop must rely on:
- deploy.yml
- sandbox state
- generated operational scripts
- runtime logs
- component definitions
- deploy metadata

### AI fix payload

Provide the AI runtime with:
- deploy profile
- sandbox state
- logs
- failing step
- operational scripts
- relevant runtime metadata

### Safe file modification

- Restrict modifications to allowed operational files.
- Track changed files per iteration.
- Persist iteration history.
- Never modify unrelated runtime state.

### Sandbox rerun

- After fixes are applied:
  - rerun validation
  - capture new logs/state
  - compare iterations

### Dashboard UI

Add auto-fix visibility:
- current iteration
- max retries
- iteration status
- changed files
- logs per iteration
- final outcome

### Failure handling

Handle safely:
- invalid AI output
- malformed patches
- repeated failures
- infinite retry risks
- sandbox crashes
- supervisor disconnects

### Tests

Add tests for:
- successful convergence after fix
- retry limit reached
- malformed AI output
- patch application failure
- generic deploy.yml handling
- iteration history persistence

## Excluded

- automatic merge to main
- production deployment
- cloud deployment
- tester-agent business tests
- self-modifying core runtime outside allowed sandbox artifacts

## Acceptance criteria

- sandbox failures can trigger a generic AI correction loop
- the loop works without ai-dev-factory-specific assumptions
- retries are bounded and observable
- iteration history is persisted and visible
- sandbox reruns after fixes
- malformed AI output is safely rejected
- the system never enters infinite retry loops
- successful fixes result in sandbox success state
- failed retries result in clean terminal failed state

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 25 tests pass. Here's a summary of what was implemented:

## Files created

- **`services/supervisor/auto_fix_loop.py`** — The full loop orchestrator: `apply_patches`, `run_scripts_validation`, `run_auto_fix_loop`, session persistence (`make_session`, `persist_session`, `load_session`, `list_sessions`)
- **`tests/test_auto_fix_loop.py`** — 9 new tests covering all required cases

## Files modified

- **`services/supervisor/auto_fix_proposer.py`** — Fixed `_is_allowed_path`: removed the `normalized == _ALLOWED_PREFIX` branch
- **`services/control_api/models/auto_fix.py`** — Added `AutoFixIteration`, `AutoFixSession`, `SessionStatus`, `IterationStatus`
- **`services/supervisor/main.py`** — Removed `exec_cmd` default, added `AutoFixLoopStartRequest` model + `_run_loop_bg` + 3 loop endpoints (`POST /auto-fix/{id}/loop/start`, `GET /auto-fix/{id}/loop/{session_id}`, `GET /auto-fix/{id}/loops`)
- **`services/control_api/services/auto_fix_runner.py`** — Added `start_auto_fix_loop`, `get_auto_fix_session`, `list_auto_fix_sessions`
- **`services/control_api/routes/auto_fix.py`** — Removed `exec_cmd` default, added 3 loop routes, extracted `_raise_on_supervisor_error` helper
- **`apps/dashboard/src/api/autoFix.js`** — Added `startAutoFixLoop`, `getAutoFixSession`, `listAutoFixSessions`; removed dangerous default
- **`apps/dashboard/src/components/AutoFixPanel.jsx`** — Added loop start form, session list table, session detail panel with per-iteration history
- **`tests/test_auto_fix_routes.py`** — Updated to pass `exec_cmd` explicitly

## Acceptance criteria now met

| Criterion | Status |
|---|---|
| sandbox reruns after fixes | ✅ `run_scripts_validation` in-place |
| retries bounded and observable | ✅ `max_retries`, `current_iteration` persisted |
| iteration history persisted and visible | ✅ session + iterations in `auto-fix-sessions/` |
| system never enters infinite retry loops | ✅ loop exits after `max_retries` |
| successful fixes → sandbox success state | ✅ `session.status = "success"` |
| failed retries → clean terminal state | ✅ `session.status = "failed"` |

---

## Review

Now I have everything I need to write the complete review.

---

# PR Review — T138: Generic AI Sandbox Auto-Fix Loop

## Résumé

L'implémentation couvre l'essentiel des exigences du ticket : orchestrateur de loop borné, collecte de contexte, invocation IA via subprocess, validation de patches par whitelist, persistance d'historique par itération, UI dashboard avec polling, tests couvrant les scénarios obligatoires.

Un **problème bloquant** est détecté : la liste de scripts requis est hardcodée, en contradiction directe avec l'exigence de généricité du ticket.

---

## Vérifications effectuées

- Lecture complète de `services/supervisor/auto_fix_loop.py` (318 lignes)
- Lecture complète de `services/supervisor/auto_fix_proposer.py` (252 lignes)
- Lecture de l'intégration supervisor `main.py` (lignes 1049–1299)
- Lecture de `tests/test_auto_fix_loop.py` (276 lignes, 9 tests)
- Lecture de `tests/test_auto_fix_proposer.py` (162 lignes, 8 tests)
- Vérification des fichiers diff (`git diff --name-only main...HEAD`)

---

## Points validés

**Loop bornée et observable** : `for attempt in range(1, max_retries + 1)` avec `default=3`, configurable 1–10 depuis le dashboard. Exhaustion explicitement traitée (lignes 304–311). Conforme.

**Payload AI générique** : Le prompt construit dans `_build_prompt()` ne référence aucun framework, port ou service. Les scripts sont inclus par lecture directe du répertoire, sans hypothèse sur leurs noms. L'invocation via `subprocess.run(shlex.split(exec_cmd) + ["--print"])` est conforme au pattern `_invoke_llm` existant.

**Modification de fichiers sécurisée** : `_is_allowed_path()` combine check `..` + `startswith(_ALLOWED_PREFIX + "/")`. Rejet des chemins absolus, relatifs hors-scope, traversals. Les tests couvrent 6 bad paths paramétrés (test 7). Conforme.

**Persistance d'historique** : Session + itérations écrites après chaque itération. Layout `{runtime_root}/auto-fix-sessions/{project_id}/{session_id}/state.json` + `iter-{n}/run.log`. Chargement et listage fonctionnels. Conforme.

**Dashboard UI** : `AutoFixPanel.jsx` couvre proposals et loop sessions, avec polling 4s, tables, vues détail par itération (fichiers modifiés, reasoning, logs, steps). Conforme.

**Tests** : 20 tests au total. Convergence, retry limit, malformed AI output, patch application failure, persistance — tous couverts. Conforme.

**Gestion d'erreurs par phase** : Chaque phase de la loop (collect\_context, call\_ai, validate, apply\_patches, run\_validation) a un `try/except` isolé qui ferme l'itération avec `status="error"` et continue la loop. Conforme.

---

## Problèmes détectés

### [BLOQUANT] `_REQUIRED_SCRIPTS` hardcodée — violation directe de la généricité

**Fichier** : `services/supervisor/auto_fix_loop.py`, ligne 36

```python
_REQUIRED_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]
```

La validation post-patch (lignes 141–186) itère sur cette liste fixe et retourne `False, "required script missing: ..."` si l'un des quatre scripts est absent.

**Problème** : Le ticket est explicite :
> *The loop must NOT assume: ai-dev-factory project structure, specific frameworks*

Ces quatre noms de scripts (`bootstrap.sh`, `build.sh`, `start.sh`, `healthcheck.sh`) sont le modèle opérationnel d'ai-dev-factory. Tout projet générique n'ayant pas exactement ces quatre scripts verra la validation échouer dès la première itération avec "required script missing", sans jamais tenter de fix — la loop devient inutilisable hors du contexte ai-dev-factory.

**Correction attendue** : La liste des scripts à valider doit être dérivée du contexte du projet. Options acceptables :
- Lire les scripts présents dans `.ai-dev-factory/scripts/` et les exécuter tous (sorted) — comportement totalement générique.
- Ou lire une clé `validation_scripts` dans `deploy.yml` — plus flexible.
- Ou passer la liste via paramètre à `run_scripts_validation()`.

La liste ne doit pas être hardcodée dans le module.

---

### [MINEUR] Statut de proposal incohérent sur patches mixtes

**Fichier** : `services/supervisor/main.py`, ligne 1103–1104

```python
any_invalid = any(not p["valid"] for p in validated)
proposal["status"] = "rejected" if any_invalid else "ready"
```

Si l'IA propose 3 patches dont 2 valides et 1 hors-scope, la proposal entière est marquée `"rejected"`. Les patches valides ne sont jamais signalés comme exploitables. L'utilisateur voit son proposal "rejeté" sans distinguer les patches OK des patches KO.

**Impact** : UX dégradée, mais les patches valides restent visibles dans le détail. Non bloquant.

**Correction suggérée** : Utiliser `"ready_with_warnings"` si `any_valid and any_invalid`, `"rejected"` si tous invalides, `"ready"` si tous valides.

---

### [MINEUR] Paramètre `project_root` inutilisé dans `validate_patches`

**Fichier** : `services/supervisor/auto_fix_proposer.py`, ligne 179

```python
def validate_patches(patches: list[dict], project_root: Path) -> list[dict]:  # noqa: ARG001
```

`project_root` est accepté mais ignoré (noqa ARG001). Soit ce paramètre a une utilité future non implémentée (vérifier l'existence du fichier cible ?), soit il doit être retiré de la signature.

---

### [MINEUR] Sessions "running" orphelines sur redémarrage supervisor

Les loops tournent dans des threads `daemon=True`. Un redémarrage du supervisor laisse les sessions avec `status="running"` sans mécanisme de reprise ou de timeout. L'UI affichera ces sessions indéfiniment en état pending. Acceptable pour un contexte dev, mais mérite une note.

---

### [MINEUR] Aucune validation de `max_retries` à l'API

Le champ `max_retries: int = 3` dans `AutoFixLoopStartRequest` n'a pas de contrainte `Field(ge=1, le=50)`. Un appelant peut passer `max_retries=10000` et initier une loop très longue. Trivial à corriger avec une validation Pydantic.

---

## Risques éventuels

- **Exécution arbitraire de scripts** : La loop exécute en l'état les scripts dans `.ai-dev-factory/scripts/` après modification par l'IA. Si le modèle IA est compromis, il peut écrire n'importe quel contenu dans ces scripts. Ce risque est by design (c'est le but du système) et acceptable en sandbox dev, mais mérite une documentation explicite.
- **Timeout AI de 300s** : Le thread background peut rester bloqué 5 minutes sans signal visible côté UI (juste "pending" indéfiniment). Acceptable pour un usage dev.

---

## Décision

L'implémentation est solide dans sa structure, ses mécanismes de sécurité et sa couverture de tests. Cependant, la violation directe de l'exigence de généricité (`_REQUIRED_SCRIPTS` hardcodé) est bloquante : un utilisateur hors du contexte ai-dev-factory ne peut pas utiliser cette loop telle quelle, ce qui contredit l'objectif central du ticket.

## Actions demandées

1. **[BLOQUANT]** Supprimer `_REQUIRED_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]`. Remplacer par une logique générique qui exécute tous les scripts présents dans le répertoire scripts (sorted), ou lit la liste depuis `deploy.yml`.
2. **[MINEUR]** Corriger le statut de proposal pour distinguer `ready` / `ready_with_warnings` / `rejected`.
3. **[MINEUR]** Ajouter `Field(ge=1, le=50)` sur `max_retries` dans `AutoFixLoopStartRequest`.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T138/reviews/implementation-review.md
- generated at: 2026-05-22T16:06:45Z

---

Now I have everything I need to write the complete review.

---

# PR Review — T138: Generic AI Sandbox Auto-Fix Loop

## Résumé

L'implémentation couvre l'essentiel des exigences du ticket : orchestrateur de loop borné, collecte de contexte, invocation IA via subprocess, validation de patches par whitelist, persistance d'historique par itération, UI dashboard avec polling, tests couvrant les scénarios obligatoires.

Un **problème bloquant** est détecté : la liste de scripts requis est hardcodée, en contradiction directe avec l'exigence de généricité du ticket.

---

## Vérifications effectuées

- Lecture complète de `services/supervisor/auto_fix_loop.py` (318 lignes)
- Lecture complète de `services/supervisor/auto_fix_proposer.py` (252 lignes)
- Lecture de l'intégration supervisor `main.py` (lignes 1049–1299)
- Lecture de `tests/test_auto_fix_loop.py` (276 lignes, 9 tests)
- Lecture de `tests/test_auto_fix_proposer.py` (162 lignes, 8 tests)
- Vérification des fichiers diff (`git diff --name-only main...HEAD`)

---

## Points validés

**Loop bornée et observable** : `for attempt in range(1, max_retries + 1)` avec `default=3`, configurable 1–10 depuis le dashboard. Exhaustion explicitement traitée (lignes 304–311). Conforme.

**Payload AI générique** : Le prompt construit dans `_build_prompt()` ne référence aucun framework, port ou service. Les scripts sont inclus par lecture directe du répertoire, sans hypothèse sur leurs noms. L'invocation via `subprocess.run(shlex.split(exec_cmd) + ["--print"])` est conforme au pattern `_invoke_llm` existant.

**Modification de fichiers sécurisée** : `_is_allowed_path()` combine check `..` + `startswith(_ALLOWED_PREFIX + "/")`. Rejet des chemins absolus, relatifs hors-scope, traversals. Les tests couvrent 6 bad paths paramétrés (test 7). Conforme.

**Persistance d'historique** : Session + itérations écrites après chaque itération. Layout `{runtime_root}/auto-fix-sessions/{project_id}/{session_id}/state.json` + `iter-{n}/run.log`. Chargement et listage fonctionnels. Conforme.

**Dashboard UI** : `AutoFixPanel.jsx` couvre proposals et loop sessions, avec polling 4s, tables, vues détail par itération (fichiers modifiés, reasoning, logs, steps). Conforme.

**Tests** : 20 tests au total. Convergence, retry limit, malformed AI output, patch application failure, persistance — tous couverts. Conforme.

**Gestion d'erreurs par phase** : Chaque phase de la loop (collect\_context, call\_ai, validate, apply\_patches, run\_validation) a un `try/except` isolé qui ferme l'itération avec `status="error"` et continue la loop. Conforme.

---

## Problèmes détectés

### [BLOQUANT] `_REQUIRED_SCRIPTS` hardcodée — violation directe de la généricité

**Fichier** : `services/supervisor/auto_fix_loop.py`, ligne 36

```python
_REQUIRED_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]
```

La validation post-patch (lignes 141–186) itère sur cette liste fixe et retourne `False, "required script missing: ..."` si l'un des quatre scripts est absent.

**Problème** : Le ticket est explicite :
> *The loop must NOT assume: ai-dev-factory project structure, specific frameworks*

Ces quatre noms de scripts (`bootstrap.sh`, `build.sh`, `start.sh`, `healthcheck.sh`) sont le modèle opérationnel d'ai-dev-factory. Tout projet générique n'ayant pas exactement ces quatre scripts verra la validation échouer dès la première itération avec "required script missing", sans jamais tenter de fix — la loop devient inutilisable hors du contexte ai-dev-factory.

**Correction attendue** : La liste des scripts à valider doit être dérivée du contexte du projet. Options acceptables :
- Lire les scripts présents dans `.ai-dev-factory/scripts/` et les exécuter tous (sorted) — comportement totalement générique.
- Ou lire une clé `validation_scripts` dans `deploy.yml` — plus flexible.
- Ou passer la liste via paramètre à `run_scripts_validation()`.

La liste ne doit pas être hardcodée dans le module.

---

### [MINEUR] Statut de proposal incohérent sur patches mixtes

**Fichier** : `services/supervisor/main.py`, ligne 1103–1104

```python
any_invalid = any(not p["valid"] for p in validated)
proposal["status"] = "rejected" if any_invalid else "ready"
```

Si l'IA propose 3 patches dont 2 valides et 1 hors-scope, la proposal entière est marquée `"rejected"`. Les patches valides ne sont jamais signalés comme exploitables. L'utilisateur voit son proposal "rejeté" sans distinguer les patches OK des patches KO.

**Impact** : UX dégradée, mais les patches valides restent visibles dans le détail. Non bloquant.

**Correction suggérée** : Utiliser `"ready_with_warnings"` si `any_valid and any_invalid`, `"rejected"` si tous invalides, `"ready"` si tous valides.

---

### [MINEUR] Paramètre `project_root` inutilisé dans `validate_patches`

**Fichier** : `services/supervisor/auto_fix_proposer.py`, ligne 179

```python
def validate_patches(patches: list[dict], project_root: Path) -> list[dict]:  # noqa: ARG001
```

`project_root` est accepté mais ignoré (noqa ARG001). Soit ce paramètre a une utilité future non implémentée (vérifier l'existence du fichier cible ?), soit il doit être retiré de la signature.

---

### [MINEUR] Sessions "running" orphelines sur redémarrage supervisor

Les loops tournent dans des threads `daemon=True`. Un redémarrage du supervisor laisse les sessions avec `status="running"` sans mécanisme de reprise ou de timeout. L'UI affichera ces sessions indéfiniment en état pending. Acceptable pour un contexte dev, mais mérite une note.

---

### [MINEUR] Aucune validation de `max_retries` à l'API

Le champ `max_retries: int = 3` dans `AutoFixLoopStartRequest` n'a pas de contrainte `Field(ge=1, le=50)`. Un appelant peut passer `max_retries=10000` et initier une loop très longue. Trivial à corriger avec une validation Pydantic.

---

## Risques éventuels

- **Exécution arbitraire de scripts** : La loop exécute en l'état les scripts dans `.ai-dev-factory/scripts/` après modification par l'IA. Si le modèle IA est compromis, il peut écrire n'importe quel contenu dans ces scripts. Ce risque est by design (c'est le but du système) et acceptable en sandbox dev, mais mérite une documentation explicite.
- **Timeout AI de 300s** : Le thread background peut rester bloqué 5 minutes sans signal visible côté UI (juste "pending" indéfiniment). Acceptable pour un usage dev.

---

## Décision

L'implémentation est solide dans sa structure, ses mécanismes de sécurité et sa couverture de tests. Cependant, la violation directe de l'exigence de généricité (`_REQUIRED_SCRIPTS` hardcodé) est bloquante : un utilisateur hors du contexte ai-dev-factory ne peut pas utiliser cette loop telle quelle, ce qui contredit l'objectif central du ticket.

## Actions demandées

1. **[BLOQUANT]** Supprimer `_REQUIRED_SCRIPTS = ["bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"]`. Remplacer par une logique générique qui exécute tous les scripts présents dans le répertoire scripts (sorted), ou lit la liste depuis `deploy.yml`.
2. **[MINEUR]** Corriger le statut de proposal pour distinguer `ready` / `ready_with_warnings` / `rejected`.
3. **[MINEUR]** Ajouter `Field(ge=1, le=50)` sur `max_retries` dans `AutoFixLoopStartRequest`.

IMPLEMENTATION_FIX_REQUIRED