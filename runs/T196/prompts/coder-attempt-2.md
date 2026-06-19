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


# T196 — T196 - Add UI action to install agent layout on existing projects and generate docs with AI analysis

**Source**: GitHub Issue #244

## Description

# Objective

After T195, bootstrap should install the standard AI Dev Factory layout for new projects.

But we also need to support projects that are already imported.

The UI must provide an action to install or regenerate the standard agent layout for an existing managed project, and this action must run an AI analysis of the project to generate meaningful `docs/` content.

---

# Problem

Currently, if a project was imported before the agent layout feature exists, there is no clean way from the UI to add:

```text
ai/
docs/
prompts/
runs/
tickets/
```

Also, `docs/` must not be a set of empty placeholders. The system should analyze the repository and generate useful documentation for agents and humans.

---

# Required UI behavior

On the project detail page, add a button/action such as:

```text
Install AI Dev Factory agent layout
```

or, if already present:

```text
Regenerate agent layout / docs
```

The action should:

1. Run on the selected existing project.
2. Analyze the repository.
3. Generate/update the standard folders:

```text
ai/
docs/
prompts/
runs/
tickets/
```

4. Create a setup/update branch.
5. Commit changes on that branch.
6. Open a PR in the target project.
7. Show the branch name, PR URL, warnings and generated docs summary in the UI.

Do not commit directly to the default branch.

---

# AI analysis requirement

The action must run an AI-assisted repository analysis before generating `docs/`.

The analysis should inspect, at minimum:

```text
README*
package.json
pyproject.toml
requirements.txt
pom.xml
build.gradle
Dockerfile
docker-compose*.yml
Makefile
src/
app/
services/
tests/
```

The analysis should identify:

- project purpose
- stack/languages/frameworks
- architecture overview
- main entry points
- important directories
- how to install dependencies
- how to run locally
- how to test
- how to build
- how to validate a PR
- risks/unknowns/TODOs

---

# Required generated docs

The generated `docs/` folder should include meaningful files, not empty placeholders.

At minimum:

```text
docs/project-overview.md
docs/architecture.md
docs/local-development.md
docs/validation.md
docs/agent-guidelines.md
docs/known-risks-and-todos.md
```

Suggested content:

## docs/project-overview.md

- what the project does
- detected stack
- main runtime components

## docs/architecture.md

- high-level architecture
- main modules/directories
- data/control flow when inferable

## docs/local-development.md

- install commands
- run commands
- useful local URLs if detected

## docs/validation.md

- test/lint/build/typecheck commands
- confidence level for each command
- TODOs where uncertain

## docs/agent-guidelines.md

- how agents should work in this repo
- conventions
- safe-change policy
- files/directories to avoid unless requested

## docs/known-risks-and-todos.md

- uncertain detections
- missing tests
- missing documentation
- commands requiring human confirmation

---

# Layout integration

The generated setup/update PR must also ensure the standard layout exists:

```text
ai/
prompts/
runs/
tickets/
```

These should follow the standard `ai-dev-factory` project layout from T195.

The docs generated by AI analysis should be referenced by the prompts and agent configuration where useful.

---

# Existing project behavior

For projects already imported:

- action must not re-bootstrap the runtime from scratch
- action must reuse the existing project registration and `project_runtime_root`
- action must be idempotent
- if layout already exists, create an update PR instead of overwriting blindly
- preserve user edits whenever possible

---

# PR behavior

Branch examples:

```text
ai-dev-factory/install-agent-layout
ai-dev-factory/update-agent-docs
```

PR title examples:

```text
Add AI Dev Factory agent layout
Update AI Dev Factory agent docs
```

PR body must include:

- generated/updated folders
- summary of AI analysis
- detected commands
- files changed
- TODOs requiring human review

---

# Acceptance criteria

- Existing imported projects have a UI button to install/regenerate the agent layout.
- The action creates or updates `ai/`, `docs/`, `prompts/`, `runs/`, and `tickets/`.
- `docs/` is generated from AI repository analysis, not empty placeholders.
- The action creates a branch and opens a PR in the target project.
- It does not commit directly to the default branch.
- It reuses the existing project runtime and registration.
- It is safe/idempotent for projects where the layout already exists.
- UI shows PR URL, warnings, and analysis summary.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All changes are in place. Here's a summary of everything implemented:

## Summary

All 8 deliverables from the approved plan are complete. 28 new tests pass, 0 regressions.

### Files created
- **`tools/agent_runner/docs_prompt_builder.py`** — Scans the repo (README, package.json, pyproject.toml, Dockerfile, docker-compose, Makefile, source directories, etc.) and builds the LLM prompt instructing Claude to produce 10 required base docs plus up to 14 conditional docs based on detected signals.
- **`tools/agent_runner/install_agent_layout.py`** — Orchestrator: calls the LLM, parses variable-number FILE blocks, validates every path (no absolute, no traversal, must be under `docs/`, must be `.md`), checks all 10 base docs are present, ensures `ai/prompts/runs/tickets/` layout dirs exist (idempotent), commits to `ai-dev-factory/install-agent-layout` (new) or `ai-dev-factory/update-agent-docs` (existing), pushes and creates/reuses a PR.
- **`tests/test_install_agent_layout.py`** — 28 tests covering: variable doc generation, conditional docs (`docs/docker.md`, `docs/api.md`), path validation rejection (absolute, traversal, non-markdown), missing base docs warning, idempotency, LLM failure, branch selection (install vs update).

### Files modified
- **`services/control_api/models/schemas.py`** — Added `InstallAgentLayoutResult` with `docs_paths: list[str]`, `docs_count: int`, `analysis_summary`, `warnings`, `error`.
- **`services/supervisor/main.py`** — Added `POST /projects/{project_id}/install-agent-layout` endpoint (synchronous, delegates to `install_agent_layout()`).
- **`services/control_api/routes/projects.py`** — Added `POST /{project_id}/install-agent-layout` endpoint proxying to supervisor with 420s timeout.
- **`apps/dashboard/src/api/projects.js`** — Added `installAgentLayout(projectId)` with 420s timeout.
- **`apps/dashboard/src/pages/ProjectDashboardPage.jsx`** — Added "Install agent layout" ActionButton and result card showing PR URL, branch, analysis summary, generated doc count/list, and warnings.

---

## Review

Here is the structured review:

---

# PR Review — T196: Add UI action to install agent layout on existing projects

## Résumé

L'implémentation couvre l'ensemble du flux bout-en-bout : bouton UI → control API → supervisor → outil Python → LLM → git → PR. Le code est propre, la sécurité des chemins est sérieuse, les tests sont substantiels (28 cas). Un bug architectural bloque l'approbation : le supervisor n'applique pas `mapper.map()` sur le `project_root` reçu, contrairement à toutes les autres opérations similaires (analysis, scripts, sandbox), ce qui fera échouer l'action en déploiement Docker standard.

---

## Vérifications effectuées

- Lecture complète de `tools/agent_runner/install_agent_layout.py` (404 lignes)
- Lecture complète de `tools/agent_runner/docs_prompt_builder.py` (229 lignes)
- Lecture complète de `tests/test_install_agent_layout.py` (351 lignes, 28 tests)
- Lecture de `services/control_api/routes/projects.py` — endpoint `POST /{project_id}/install-agent-layout`
- Lecture de `services/supervisor/main.py` — endpoint `POST /projects/{project_id}/install-agent-layout`
- Lecture de `apps/dashboard/src/api/projects.js` — `installAgentLayout()`
- Lecture de `apps/dashboard/src/pages/ProjectDashboardPage.jsx` — UI
- Lecture de `services/control_api/models/schemas.py` — `InstallAgentLayoutResult`
- Comparaison avec les patterns existants (analysis, scripts, sandbox) dans le supervisor

---

## Points validés

**Fonctionnalités ticket**
- Bouton "Install agent layout" présent sur la page projet (`ProjectDashboardPage.jsx` l.196–201) ✅
- Analyse IA du dépôt : `docs_prompt_builder.py` scanne README, package.json, pyproject.toml, Dockerfile, docker-compose.yml, Makefile, go.mod, Cargo.toml, dirs src/app/services/tests ✅
- Génération des dossiers standard `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/` via `_ensure_layout_dirs()` ✅
- Branche dédiée `ai-dev-factory/install-agent-layout` ou `ai-dev-factory/update-agent-docs` ✅
- Commit sur la branche, jamais sur le branch par défaut ✅
- Ouverture d'une PR via `gh pr create`, avec corps structuré (résumé analyse, docs générés, TODOs) ✅
- Affichage dans l'UI : PR URL cliquable, branche, résumé analyse, docs générés, warnings ✅
- Idempotence : réutilise PR existante, ne ré-écrit pas les fichiers déjà présents, `mkdir(exist_ok=True)` partout ✅
- Réutilise le `project_root` enregistré dans le registry, pas de re-bootstrap ✅

**Sécurité des chemins générés par le LLM**
- Rejet des chemins absolus (`/etc/hosts`) ✅
- Rejet du path traversal (`docs/../../../evil.md`) via `resolved.relative_to(docs_root)` ✅
- Rejet des fichiers non-markdown ✅
- Rejet des fichiers vides ✅
- Tous les cas testés dans `test_install_agent_layout.py` ✅

**Architecture**
- Layering correct : dashboard → control API → supervisor → outil Python ✅
- Timeout 420 s cohérent sur toute la chaîne (JS axios, httpx, subprocess) ✅
- Gestion des erreurs structurée à chaque couche, retour `error` dans le résultat ✅
- `InstallAgentLayoutResult` Pydantic bien défini ✅

**Tests**
- 28 tests unitaires et d'intégration (vrai dépôt git, LLM mocké) ✅
- Couverture : validation des chemins, parsing des blocs FILE, sélection de branche, idempotence, erreur LLM, absence de remote, commit vérifié ✅

---

## Problèmes détectés

### 🔴 BLOQUANT — Absence de `mapper.map()` dans le supervisor (path mapping Docker)

**Fichier :** `services/supervisor/main.py` — `install_agent_layout_endpoint` (l.1661–1702)

**Description :**  
Toutes les opérations comparables dans le supervisor appliquent `mapper.map()` sur le `project_root` reçu depuis la control API avant d'utiliser le chemin :

```python
# analysis_start — ligne 678
mapped_root = mapper.map(body.project_root)

# sandbox_start — ligne 998
mapped_root = mapper.map(body.project_root)
```

L'endpoint `install_agent_layout_endpoint` ne le fait **pas** :

```python
# install_agent_layout_endpoint — ligne 1666
project_root = Path(body.project_root).expanduser().resolve()
# ← mapper.map() absent
```

**Impact :**  
En déploiement Docker standard, la control API tourne dans un container et stocke dans le registry des chemins de type `/runtime/clones/<project-id>`. Le supervisor tourne sur le host. Sans `mapper.map()`, le supervisor reçoit un chemin container invalide côté host, la vérification `project_root.exists()` (l.1673) échoue, et l'endpoint retourne `{"error": "path_not_found"}` — la feature ne fonctionne pas.

**Correction attendue :**
```python
@app.post("/projects/{project_id}/install-agent-layout")
def install_agent_layout_endpoint(project_id: str, body: InstallAgentLayoutRequest):
    ...
    try:
-       project_root = Path(body.project_root).expanduser().resolve()
+       mapped = mapper.map(body.project_root)
+       project_root = Path(mapped).expanduser().resolve()
    except (OSError, PermissionError) as exc:
        ...
```

---

### 🟡 Mineur — Label du bouton statique (écart spec ticket)

**Fichier :** `apps/dashboard/src/pages/ProjectDashboardPage.jsx` l.197

Le ticket spécifie explicitement deux labels différents :
- "Install AI Dev Factory agent layout" si le layout n'existe pas
- "Regenerate agent layout / docs" si le layout existe déjà

L'implémentation affiche toujours "Install agent layout" quel que soit l'état. La détection de l'état du layout par l'UI nécessiterait soit un appel API dédié, soit d'exposer un flag `layout_installed` dans `ProjectInfo`. Il est acceptable de traiter cet écart comme une amélioration post-merge, mais c'est une exigence explicite du ticket.

---

### 🟡 Mineur — Absence de verrou de concurrence

**Fichier :** `services/supervisor/main.py`

Les opérations analysis, scripts et sandbox utilisent des verrous par `project_id` (`_analysis_locks`, `_scripts_locks`, `_sandbox_locks`) avec pattern lock → pid check → spawn. L'endpoint `install_agent_layout` n'a pas de verrou équivalent. Un double-clic ou appel concurrent pourrait lancer deux invocations LLM simultanées sur le même dépôt (deux `git checkout -b` en course, conflits git possibles). Peu probable en pratique (timeout 7 min) mais incohérent avec le reste.

---

### 🟡 Mineur — `exec_cmd` non transmis depuis la control API

**Fichier :** `services/control_api/routes/projects.py` l.207–214

La control API envoie `project_root` et `project_id` au supervisor, mais pas `exec_cmd`. Le supervisor a ce paramètre dans `InstallAgentLayoutRequest` et le reçoit jamais depuis l'UI. Par cohérence avec les autres opérations (analysis, scripts), il serait préférable que la control API accepte `exec_cmd` en body et le relaie. Non bloquant (le défaut `"claude --dangerously-skip-permissions"` est correct), mais l'extension future sera difficile.

---

## Risques éventuels

1. **LLM output parsing fragile** : le format `--- BEGIN FILE: ... --- / --- END FILE ---` est custom. Si le LLM génère une variation de format (espace dans le délimiteur, casse différente, balises imbriquées), les blocs ne sont pas parsés. Risque faible si le prompt est suivi, mais non détectable sans retour d'erreur explicite (le résultat contiendra 0 docs et un warning "missing required base docs").

2. **`git add -A` (l.313)** : utiliser `git add -A` sans exclusion peut embarquer des fichiers non prévus dans le commit si le projet cible a des fichiers modifiés. Préférer `git add docs/ ai/ prompts/ runs/ tickets/` pour cibler uniquement les dossiers créés.

3. **Durée de l'opération (UI)** : 7 minutes avec seulement "…" dans le bouton. Selon l'implémentation d'`ActionButton`, cela peut sembler gelé. Non bloquant si ActionButton gère correctement les timeouts longs.

---

## Décision

Le cœur de l'implémentation est solide : la sécurité des chemins LLM est bien gérée, le flux git/PR est correct, les tests couvrent les cas importants. Un seul bug bloquant : l'absence de `mapper.map()` dans le supervisor rendrait la feature inopérante en déploiement Docker standard — ce qui est le déploiement cible.

## Actions demandées

1. **[BLOQUANT]** Ajouter `mapper.map(body.project_root)` dans `install_agent_layout_endpoint` avant de résoudre le path (même pattern que `analysis_start` et `sandbox_start`)
2. **[Optionnel]** Adapter le label du bouton selon la présence du layout (exposer `layout_installed` dans `GET /projects` ou via un endpoint dédié)
3. **[Optionnel]** Ajouter un verrou de concurrence par project_id sur l'opération
4. **[Optionnel]** Transmettre `exec_cmd` depuis la control API vers le supervisor

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T196/reviews/implementation-review.md
- generated at: 2026-06-19T13:41:49Z

---

Here is the structured review:

---

# PR Review — T196: Add UI action to install agent layout on existing projects

## Résumé

L'implémentation couvre l'ensemble du flux bout-en-bout : bouton UI → control API → supervisor → outil Python → LLM → git → PR. Le code est propre, la sécurité des chemins est sérieuse, les tests sont substantiels (28 cas). Un bug architectural bloque l'approbation : le supervisor n'applique pas `mapper.map()` sur le `project_root` reçu, contrairement à toutes les autres opérations similaires (analysis, scripts, sandbox), ce qui fera échouer l'action en déploiement Docker standard.

---

## Vérifications effectuées

- Lecture complète de `tools/agent_runner/install_agent_layout.py` (404 lignes)
- Lecture complète de `tools/agent_runner/docs_prompt_builder.py` (229 lignes)
- Lecture complète de `tests/test_install_agent_layout.py` (351 lignes, 28 tests)
- Lecture de `services/control_api/routes/projects.py` — endpoint `POST /{project_id}/install-agent-layout`
- Lecture de `services/supervisor/main.py` — endpoint `POST /projects/{project_id}/install-agent-layout`
- Lecture de `apps/dashboard/src/api/projects.js` — `installAgentLayout()`
- Lecture de `apps/dashboard/src/pages/ProjectDashboardPage.jsx` — UI
- Lecture de `services/control_api/models/schemas.py` — `InstallAgentLayoutResult`
- Comparaison avec les patterns existants (analysis, scripts, sandbox) dans le supervisor

---

## Points validés

**Fonctionnalités ticket**
- Bouton "Install agent layout" présent sur la page projet (`ProjectDashboardPage.jsx` l.196–201) ✅
- Analyse IA du dépôt : `docs_prompt_builder.py` scanne README, package.json, pyproject.toml, Dockerfile, docker-compose.yml, Makefile, go.mod, Cargo.toml, dirs src/app/services/tests ✅
- Génération des dossiers standard `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/` via `_ensure_layout_dirs()` ✅
- Branche dédiée `ai-dev-factory/install-agent-layout` ou `ai-dev-factory/update-agent-docs` ✅
- Commit sur la branche, jamais sur le branch par défaut ✅
- Ouverture d'une PR via `gh pr create`, avec corps structuré (résumé analyse, docs générés, TODOs) ✅
- Affichage dans l'UI : PR URL cliquable, branche, résumé analyse, docs générés, warnings ✅
- Idempotence : réutilise PR existante, ne ré-écrit pas les fichiers déjà présents, `mkdir(exist_ok=True)` partout ✅
- Réutilise le `project_root` enregistré dans le registry, pas de re-bootstrap ✅

**Sécurité des chemins générés par le LLM**
- Rejet des chemins absolus (`/etc/hosts`) ✅
- Rejet du path traversal (`docs/../../../evil.md`) via `resolved.relative_to(docs_root)` ✅
- Rejet des fichiers non-markdown ✅
- Rejet des fichiers vides ✅
- Tous les cas testés dans `test_install_agent_layout.py` ✅

**Architecture**
- Layering correct : dashboard → control API → supervisor → outil Python ✅
- Timeout 420 s cohérent sur toute la chaîne (JS axios, httpx, subprocess) ✅
- Gestion des erreurs structurée à chaque couche, retour `error` dans le résultat ✅
- `InstallAgentLayoutResult` Pydantic bien défini ✅

**Tests**
- 28 tests unitaires et d'intégration (vrai dépôt git, LLM mocké) ✅
- Couverture : validation des chemins, parsing des blocs FILE, sélection de branche, idempotence, erreur LLM, absence de remote, commit vérifié ✅

---

## Problèmes détectés

### 🔴 BLOQUANT — Absence de `mapper.map()` dans le supervisor (path mapping Docker)

**Fichier :** `services/supervisor/main.py` — `install_agent_layout_endpoint` (l.1661–1702)

**Description :**  
Toutes les opérations comparables dans le supervisor appliquent `mapper.map()` sur le `project_root` reçu depuis la control API avant d'utiliser le chemin :

```python
# analysis_start — ligne 678
mapped_root = mapper.map(body.project_root)

# sandbox_start — ligne 998
mapped_root = mapper.map(body.project_root)
```

L'endpoint `install_agent_layout_endpoint` ne le fait **pas** :

```python
# install_agent_layout_endpoint — ligne 1666
project_root = Path(body.project_root).expanduser().resolve()
# ← mapper.map() absent
```

**Impact :**  
En déploiement Docker standard, la control API tourne dans un container et stocke dans le registry des chemins de type `/runtime/clones/<project-id>`. Le supervisor tourne sur le host. Sans `mapper.map()`, le supervisor reçoit un chemin container invalide côté host, la vérification `project_root.exists()` (l.1673) échoue, et l'endpoint retourne `{"error": "path_not_found"}` — la feature ne fonctionne pas.

**Correction attendue :**
```python
@app.post("/projects/{project_id}/install-agent-layout")
def install_agent_layout_endpoint(project_id: str, body: InstallAgentLayoutRequest):
    ...
    try:
-       project_root = Path(body.project_root).expanduser().resolve()
+       mapped = mapper.map(body.project_root)
+       project_root = Path(mapped).expanduser().resolve()
    except (OSError, PermissionError) as exc:
        ...
```

---

### 🟡 Mineur — Label du bouton statique (écart spec ticket)

**Fichier :** `apps/dashboard/src/pages/ProjectDashboardPage.jsx` l.197

Le ticket spécifie explicitement deux labels différents :
- "Install AI Dev Factory agent layout" si le layout n'existe pas
- "Regenerate agent layout / docs" si le layout existe déjà

L'implémentation affiche toujours "Install agent layout" quel que soit l'état. La détection de l'état du layout par l'UI nécessiterait soit un appel API dédié, soit d'exposer un flag `layout_installed` dans `ProjectInfo`. Il est acceptable de traiter cet écart comme une amélioration post-merge, mais c'est une exigence explicite du ticket.

---

### 🟡 Mineur — Absence de verrou de concurrence

**Fichier :** `services/supervisor/main.py`

Les opérations analysis, scripts et sandbox utilisent des verrous par `project_id` (`_analysis_locks`, `_scripts_locks`, `_sandbox_locks`) avec pattern lock → pid check → spawn. L'endpoint `install_agent_layout` n'a pas de verrou équivalent. Un double-clic ou appel concurrent pourrait lancer deux invocations LLM simultanées sur le même dépôt (deux `git checkout -b` en course, conflits git possibles). Peu probable en pratique (timeout 7 min) mais incohérent avec le reste.

---

### 🟡 Mineur — `exec_cmd` non transmis depuis la control API

**Fichier :** `services/control_api/routes/projects.py` l.207–214

La control API envoie `project_root` et `project_id` au supervisor, mais pas `exec_cmd`. Le supervisor a ce paramètre dans `InstallAgentLayoutRequest` et le reçoit jamais depuis l'UI. Par cohérence avec les autres opérations (analysis, scripts), il serait préférable que la control API accepte `exec_cmd` en body et le relaie. Non bloquant (le défaut `"claude --dangerously-skip-permissions"` est correct), mais l'extension future sera difficile.

---

## Risques éventuels

1. **LLM output parsing fragile** : le format `--- BEGIN FILE: ... --- / --- END FILE ---` est custom. Si le LLM génère une variation de format (espace dans le délimiteur, casse différente, balises imbriquées), les blocs ne sont pas parsés. Risque faible si le prompt est suivi, mais non détectable sans retour d'erreur explicite (le résultat contiendra 0 docs et un warning "missing required base docs").

2. **`git add -A` (l.313)** : utiliser `git add -A` sans exclusion peut embarquer des fichiers non prévus dans le commit si le projet cible a des fichiers modifiés. Préférer `git add docs/ ai/ prompts/ runs/ tickets/` pour cibler uniquement les dossiers créés.

3. **Durée de l'opération (UI)** : 7 minutes avec seulement "…" dans le bouton. Selon l'implémentation d'`ActionButton`, cela peut sembler gelé. Non bloquant si ActionButton gère correctement les timeouts longs.

---

## Décision

Le cœur de l'implémentation est solide : la sécurité des chemins LLM est bien gérée, le flux git/PR est correct, les tests couvrent les cas importants. Un seul bug bloquant : l'absence de `mapper.map()` dans le supervisor rendrait la feature inopérante en déploiement Docker standard — ce qui est le déploiement cible.

## Actions demandées

1. **[BLOQUANT]** Ajouter `mapper.map(body.project_root)` dans `install_agent_layout_endpoint` avant de résoudre le path (même pattern que `analysis_start` et `sandbox_start`)
2. **[Optionnel]** Adapter le label du bouton selon la présence du layout (exposer `layout_installed` dans `GET /projects` ou via un endpoint dédié)
3. **[Optionnel]** Ajouter un verrou de concurrence par project_id sur l'opération
4. **[Optionnel]** Transmettre `exec_cmd` depuis la control API vers le supervisor

---

IMPLEMENTATION_FIX_REQUIRED