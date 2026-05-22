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

All 16 tests pass. Here's a summary of what was implemented:

## Files created / modified

**New files:**
- `services/control_api/models/auto_fix.py` — `ProposalStatus`, `PatchProposal`, `AutoFixProposal` Pydantic models
- `services/supervisor/auto_fix_proposer.py` — `collect_failure_context`, `call_ai_runtime` (mirrors `_invoke_llm`), `validate_patches`, `persist_proposal`/`load_proposal`/`list_proposals`
- `services/control_api/services/auto_fix_runner.py` — HTTP proxy to supervisor (mirrors `sandbox_runner.py`)
- `services/control_api/routes/auto_fix.py` — 3 endpoints: `POST /projects/{id}/auto-fix/propose`, `GET /projects/{id}/auto-fix/proposal/{pid}`, `GET /projects/{id}/auto-fix/proposals`
- `apps/dashboard/src/api/autoFix.js` — Axios client
- `apps/dashboard/src/components/AutoFixPanel.jsx` — read-only patch preview UI with polling
- `tests/test_auto_fix_proposer.py` — 8 proposer unit tests
- `tests/test_auto_fix_routes.py` — 3 route integration tests

**Modified files:**
- `services/supervisor/main.py` — added `uuid` import + 3 new auto-fix endpoints (`POST/GET /auto-fix/…`) with background thread execution
- `services/control_api/main.py` — registered `auto_fix.router`
- `apps/dashboard/src/App.jsx` — added `AutoFixPanel` import + `/auto-fix` route + nav link

---

## Review

I now have a complete picture of the implementation. Let me write the structured review.

---

# PR Review — T138 — Generic AI sandbox auto-fix loop

## Résumé

L'implémentation livre un système de **proposition de patches en lecture seule** : l'AI analyse un échec sandbox et propose des corrections visualisables dans le dashboard. Aucun fichier n'est modifié, aucun sandbox n'est relancé, aucune boucle de retry n'existe. C'est ce que le plan approuvé a spécifié — mais cela ne couvre pas les critères d'acceptance du ticket.

## Vérifications effectuées

- Lecture complète des 8 fichiers créés et des 3 modifiés
- Comparaison point par point avec les acceptance criteria du ticket
- Analyse de la sécurité (exec_cmd, path traversal, concurrence)
- Revue de la couverture de tests
- Traçage du lifecycle workflow (plan-review.md × 2, workflow-status.md)

## Points validés

**Architecture et patterns**
- `call_ai_runtime` suit fidèlement le pattern `_invoke_llm` de `run_scripts.py` : `shlex.split(exec_cmd) + ["--print"]`, subprocess, stdin prompt, stdout parsed — aucun SDK provider, aucune variable d'env hardcodée.
- Le découpage supervisor/control_api/dashboard respecte l'architecture en couches existante.
- `auto_fix_runner.py` est un proxy HTTP propre, miroir de `sandbox_runner.py`.
- Le background thread dans `supervisor/main.py` retourne immédiatement un `proposal_id`, le polling est correctement implémenté côté dashboard.

**Sécurité path**
- `validate_patches` rejette les path traversal (`..`) et tout chemin hors `.ai-dev-factory/scripts/`.
- Aucun secret hardcodé dans le code de production (hors valeur par défaut, voir ci-dessous).

**Qualité code**
- Code lisible, fonctions courtes, nommage explicite.
- Gestion d'erreurs explicite dans `_run_proposal_bg` (try/except sur collect, call, validate puis sur persist séparément).
- 16 tests passent, couvrant les cas unitaires du proposer et les routes.

**Généricité**
- `collect_failure_context` ne fait aucune hypothèse sur les noms de services, ports ou frameworks.
- Le contexte est construit depuis `deploy.yml`, `state.json`, `run.log` et les scripts — conformément au ticket.

## Problèmes détectés

### [BLOQUANT] Loop absente — 5 acceptance criteria non satisfaits

Le ticket T138 est intitulé **"Generic AI sandbox auto-fix loop"**. Les critères d'acceptance suivants ne sont pas satisfaits :

| Critère ticket | Statut |
|---|---|
| sandbox reruns after fixes | ❌ pas implémenté |
| retries are bounded and observable | ❌ aucune boucle |
| iteration history is persisted and visible | ❌ proposals sans notion d'itération |
| the system never enters infinite retry loops | ❌ N/A (pas de loop) |
| successful fixes result in sandbox success state | ❌ pas implémenté |
| failed retries result in clean terminal failed state | ❌ pas implémenté |

Le plan reviewer a intentionnellement réduit ce scope (plan-review.md : *"Do not automatically modify operational artifacts or rerun sandboxes yet"*). Le plan approuvé est conforme à ce qui a été livré. Mais les acceptance criteria du ticket restent la barre de l'implementation review — et 5 sur 9 ne sont pas atteints.

**Action requise** : soit compléter T138 avec les composants manquants (apply, rerun, loop), soit amender explicitement les acceptance criteria du ticket pour le scope proposal-only et ouvrir un ticket de suivi pour la boucle.

### [BLOQUANT] Tests requis par le ticket absents

Le ticket demande explicitement des tests pour :
- successful convergence after fix — ❌ absent
- retry limit reached — ❌ absent
- patch application failure — ❌ absent
- sandbox crashes — ❌ absent
- iteration history persistence — ❌ couvert partiellement (proposals, pas itérations)

Les tests présents couvrent le proposer unitaire et les routes — utiles, mais insuffisants au regard du ticket.

### [MINEUR] Bug dans `_is_allowed_path` — condition doublon

```python
# auto_fix_proposer.py
return normalized.startswith(_ALLOWED_PREFIX + "/") or normalized == _ALLOWED_PREFIX
```

La condition `normalized == _ALLOWED_PREFIX` autorise le chemin `.ai-dev-factory/scripts` lui-même (sans filename) comme `relative_path` valide. Écrire dans un répertoire sans nom de fichier serait rejeté à l'écriture disque, mais c'est une fuite de validation à corriger :

```python
# correct : seuls les chemins avec un fichier à l'intérieur sont valides
return normalized.startswith(_ALLOWED_PREFIX + "/")
```

### [MINEUR] `exec_cmd` default dangereux en deux points

```python
# routes/auto_fix.py et supervisor/main.py
exec_cmd: str = "claude --dangerously-skip-permissions"
```

`--dangerously-skip-permissions` ne devrait pas être la valeur par défaut. Forcer l'appelant à passer explicitement `exec_cmd` réduit le risque d'exécution accidentelle.

### [MINEUR] Race condition proposal "pending" permanente

Le proposal est persisté en `status=pending` avant le lancement du thread. Si le superviseur s'arrête pendant l'exécution du thread, le proposal reste `pending` indéfiniment — pas de mécanisme de timeout ni de recovery au redémarrage. Acceptable pour une V1 proposal-only mais à documenter.

### [MINEUR] `project_root` inutilisé dans `validate_patches`

```python
def validate_patches(patches: list[dict], project_root: Path) -> list[dict]:  # noqa: ARG001
```

Le paramètre est ignoré. Si l'intention est de permettre une validation filesystem future, c'est acceptable — mais le `noqa: ARG001` devrait s'accompagner d'un commentaire expliquant pourquoi il est conservé.

## Risques éventuels

- Absence de concurrency control sur le endpoint `POST /propose` : plusieurs proposals peuvent être lancées en parallèle pour le même sandbox, potentiellement avec des appels AI redondants et des écritures concurrentes.
- La regex `re.search(r"\[.*\]", output, re.DOTALL)` est greedy — si l'AI ajoute du texte après `]`, le match peut s'étendre à des `]` parasites. En pratique, le `json.loads` catchera l'erreur et propagera `ValueError` correctement, mais c'est fragile.

## Décision

- ~~APPROVED~~
- **REQUEST_CHANGES**

## Actions demandées

1. **[Obligatoire]** Résoudre l'écart avec les acceptance criteria du ticket — soit implémenter la boucle apply/rerun/retry, soit explicitement amender le ticket pour scope proposal-only et créer un ticket de suivi pour la loop. Sans cela, T138 n'est pas livré.

2. **[Obligatoire]** Ajouter les tests requis par le ticket (convergence, retry limit, patch application failure) — ou documenter formellement leur déplacement dans un ticket de suivi.

3. **[Mineur]** Corriger `_is_allowed_path` : supprimer la condition `normalized == _ALLOWED_PREFIX`.

4. **[Mineur]** Supprimer la valeur par défaut `"claude --dangerously-skip-permissions"` pour `exec_cmd`.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T138/reviews/implementation-review.md
- generated at: 2026-05-22T15:51:59Z

---

I now have a complete picture of the implementation. Let me write the structured review.

---

# PR Review — T138 — Generic AI sandbox auto-fix loop

## Résumé

L'implémentation livre un système de **proposition de patches en lecture seule** : l'AI analyse un échec sandbox et propose des corrections visualisables dans le dashboard. Aucun fichier n'est modifié, aucun sandbox n'est relancé, aucune boucle de retry n'existe. C'est ce que le plan approuvé a spécifié — mais cela ne couvre pas les critères d'acceptance du ticket.

## Vérifications effectuées

- Lecture complète des 8 fichiers créés et des 3 modifiés
- Comparaison point par point avec les acceptance criteria du ticket
- Analyse de la sécurité (exec_cmd, path traversal, concurrence)
- Revue de la couverture de tests
- Traçage du lifecycle workflow (plan-review.md × 2, workflow-status.md)

## Points validés

**Architecture et patterns**
- `call_ai_runtime` suit fidèlement le pattern `_invoke_llm` de `run_scripts.py` : `shlex.split(exec_cmd) + ["--print"]`, subprocess, stdin prompt, stdout parsed — aucun SDK provider, aucune variable d'env hardcodée.
- Le découpage supervisor/control_api/dashboard respecte l'architecture en couches existante.
- `auto_fix_runner.py` est un proxy HTTP propre, miroir de `sandbox_runner.py`.
- Le background thread dans `supervisor/main.py` retourne immédiatement un `proposal_id`, le polling est correctement implémenté côté dashboard.

**Sécurité path**
- `validate_patches` rejette les path traversal (`..`) et tout chemin hors `.ai-dev-factory/scripts/`.
- Aucun secret hardcodé dans le code de production (hors valeur par défaut, voir ci-dessous).

**Qualité code**
- Code lisible, fonctions courtes, nommage explicite.
- Gestion d'erreurs explicite dans `_run_proposal_bg` (try/except sur collect, call, validate puis sur persist séparément).
- 16 tests passent, couvrant les cas unitaires du proposer et les routes.

**Généricité**
- `collect_failure_context` ne fait aucune hypothèse sur les noms de services, ports ou frameworks.
- Le contexte est construit depuis `deploy.yml`, `state.json`, `run.log` et les scripts — conformément au ticket.

## Problèmes détectés

### [BLOQUANT] Loop absente — 5 acceptance criteria non satisfaits

Le ticket T138 est intitulé **"Generic AI sandbox auto-fix loop"**. Les critères d'acceptance suivants ne sont pas satisfaits :

| Critère ticket | Statut |
|---|---|
| sandbox reruns after fixes | ❌ pas implémenté |
| retries are bounded and observable | ❌ aucune boucle |
| iteration history is persisted and visible | ❌ proposals sans notion d'itération |
| the system never enters infinite retry loops | ❌ N/A (pas de loop) |
| successful fixes result in sandbox success state | ❌ pas implémenté |
| failed retries result in clean terminal failed state | ❌ pas implémenté |

Le plan reviewer a intentionnellement réduit ce scope (plan-review.md : *"Do not automatically modify operational artifacts or rerun sandboxes yet"*). Le plan approuvé est conforme à ce qui a été livré. Mais les acceptance criteria du ticket restent la barre de l'implementation review — et 5 sur 9 ne sont pas atteints.

**Action requise** : soit compléter T138 avec les composants manquants (apply, rerun, loop), soit amender explicitement les acceptance criteria du ticket pour le scope proposal-only et ouvrir un ticket de suivi pour la boucle.

### [BLOQUANT] Tests requis par le ticket absents

Le ticket demande explicitement des tests pour :
- successful convergence after fix — ❌ absent
- retry limit reached — ❌ absent
- patch application failure — ❌ absent
- sandbox crashes — ❌ absent
- iteration history persistence — ❌ couvert partiellement (proposals, pas itérations)

Les tests présents couvrent le proposer unitaire et les routes — utiles, mais insuffisants au regard du ticket.

### [MINEUR] Bug dans `_is_allowed_path` — condition doublon

```python
# auto_fix_proposer.py
return normalized.startswith(_ALLOWED_PREFIX + "/") or normalized == _ALLOWED_PREFIX
```

La condition `normalized == _ALLOWED_PREFIX` autorise le chemin `.ai-dev-factory/scripts` lui-même (sans filename) comme `relative_path` valide. Écrire dans un répertoire sans nom de fichier serait rejeté à l'écriture disque, mais c'est une fuite de validation à corriger :

```python
# correct : seuls les chemins avec un fichier à l'intérieur sont valides
return normalized.startswith(_ALLOWED_PREFIX + "/")
```

### [MINEUR] `exec_cmd` default dangereux en deux points

```python
# routes/auto_fix.py et supervisor/main.py
exec_cmd: str = "claude --dangerously-skip-permissions"
```

`--dangerously-skip-permissions` ne devrait pas être la valeur par défaut. Forcer l'appelant à passer explicitement `exec_cmd` réduit le risque d'exécution accidentelle.

### [MINEUR] Race condition proposal "pending" permanente

Le proposal est persisté en `status=pending` avant le lancement du thread. Si le superviseur s'arrête pendant l'exécution du thread, le proposal reste `pending` indéfiniment — pas de mécanisme de timeout ni de recovery au redémarrage. Acceptable pour une V1 proposal-only mais à documenter.

### [MINEUR] `project_root` inutilisé dans `validate_patches`

```python
def validate_patches(patches: list[dict], project_root: Path) -> list[dict]:  # noqa: ARG001
```

Le paramètre est ignoré. Si l'intention est de permettre une validation filesystem future, c'est acceptable — mais le `noqa: ARG001` devrait s'accompagner d'un commentaire expliquant pourquoi il est conservé.

## Risques éventuels

- Absence de concurrency control sur le endpoint `POST /propose` : plusieurs proposals peuvent être lancées en parallèle pour le même sandbox, potentiellement avec des appels AI redondants et des écritures concurrentes.
- La regex `re.search(r"\[.*\]", output, re.DOTALL)` est greedy — si l'AI ajoute du texte après `]`, le match peut s'étendre à des `]` parasites. En pratique, le `json.loads` catchera l'erreur et propagera `ValueError` correctement, mais c'est fragile.

## Décision

- ~~APPROVED~~
- **REQUEST_CHANGES**

## Actions demandées

1. **[Obligatoire]** Résoudre l'écart avec les acceptance criteria du ticket — soit implémenter la boucle apply/rerun/retry, soit explicitement amender le ticket pour scope proposal-only et créer un ticket de suivi pour la loop. Sans cela, T138 n'est pas livré.

2. **[Obligatoire]** Ajouter les tests requis par le ticket (convergence, retry limit, patch application failure) — ou documenter formellement leur déplacement dans un ticket de suivi.

3. **[Mineur]** Corriger `_is_allowed_path` : supprimer la condition `normalized == _ALLOWED_PREFIX`.

4. **[Mineur]** Supprimer la valeur par défaut `"claude --dangerously-skip-permissions"` pour `exec_cmd`.

---

IMPLEMENTATION_FIX_REQUIRED