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


# T130 — T130 — AI-assisted operational project analysis and deploy profile generation

**Source**: GitHub Issue #99

## Description

# T130 — AI-assisted operational project analysis and deploy profile generation

## Objective

Add an AI-assisted deployer workflow able to analyze any managed repository and generate reviewable operational documentation and deployment profiles.

The workflow must use the LLM runtime configured by the daemon/executor environment instead of hardcoding a specific AI provider.

## Included

- Add an “Analyze Project” action to the deployer UI.
- Use deterministic Python project scanning as structured context input.
- Send repository structure + scan result to the configured LLM runtime.
- Generate:
  - `.ai-dev-factory/deploy.yml`
  - `.ai-dev-factory/deployment.md`
  - optional `.ai-dev-factory/runtime-notes.md`
- Infer:
  - required tools
  - docker services
  - host-side processes
  - build commands
  - startup commands
  - restart commands
  - healthchecks
  - runtime dependencies
  - environment variables
  - known operational constraints
- Commit generated operational files to a dedicated branch.
- Create or update a PR for human review.
- Show analysis progress, logs and failures in the dashboard.
- Add tests for:
  - prompt generation
  - AI execution orchestration
  - file generation
  - Git branch workflow
  - PR creation/update

## Excluded

- Automatic deployment execution.
- Automatic install of missing dependencies.
- Automatic merge.
- Secrets management.
- Remote/cloud deployment orchestration.

## Acceptance criteria

- A user can trigger repository operational analysis from the dashboard.
- The configured LLM runtime analyzes the repository and generates reviewable operational files.
- Generated deploy.yml is valid and compatible with the deployer runtime.
- Generated documentation explains how to build/start/restart/check the project.
- Generated files are committed to a dedicated branch.
- A PR is created or updated automatically.
- Existing deployer/runtime workflows remain functional.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 20 tests pass. Here's what was done:

**Fix 1 — Path traversal (`run_analysis.py:183-193`):** Added a guard that raises `RuntimeError` for any LLM-generated path not starting with `.ai-dev-factory/`, preventing writes outside that directory.

**Fix 2 — New test file (`tests/test_run_analysis.py`, 8 tests):**

| Test | Covers |
|------|--------|
| `test_extract_files_valid_response` | Well-formed 3-file LLM output → correct dict |
| `test_extract_files_empty_output` | No blocks → empty dict |
| `test_extract_files_malformed_delimiter` | Broken delimiter → empty dict |
| `test_extract_files_partial_block` | Unclosed block → empty dict |
| `test_main_happy_path_writes_files_and_state` | Full orchestration: files written, state=success, branch/PR captured |
| `test_main_missing_required_file_sets_failed_state` | Missing deploy.yml → state=failed, error references deploy.yml |
| `test_main_path_traversal_rejected` | `../../etc/passwd` path → state=failed, no file written |
| `test_main_llm_failure_sets_failed_state` | LLM subprocess error → state=failed |

---

## Review

---

# PR Review — T130: AI-assisted operational project analysis and deploy profile generation

## Résumé

L'implémentation couvre l'ensemble des fonctionnalités demandées par le ticket : worker host-side (`run_analysis.py`), builder de prompt (`analysis_prompt_builder.py`), service git (`analysis_git_service.py`), endpoints supervisor, routes control API, composants frontend, et 20 tests unitaires. L'architecture est correcte et les flux de données sont cohérents.

Un défaut de sécurité bloquant a été identifié dans la protection contre le path traversal.

---

## Vérifications effectuées

- Lecture intégrale des 10 fichiers nouveaux et des fichiers modifiés
- Vérification de chaque critère d'acceptation du ticket
- Analyse des chemins d'exécution critiques (sécurité, erreurs, locking)
- Lecture de chaque fichier de test

---

## Points validés

**Fonctionnel — ticket couvert à ~95% :**
- Bouton "Analyze Project" dans la UI (`DeployerPage.jsx:267-271`)
- Scan déterministe du projet côté host (`run_analysis.py:85-111`)
- Génération du prompt avec schéma DeployProfile, arbre de fichiers et résultat du scan (`analysis_prompt_builder.py`)
- Invocation LLM via `exec_cmd` configuré — aucun provider hardcodé (`run_analysis.py:114-128`)
- Extraction des blocs `--- BEGIN FILE / END FILE ---` et écriture dans `.ai-dev-factory/` (`run_analysis.py:131-194`)
- Vérification que `deploy.yml` et `deployment.md` sont présents dans la sortie LLM (`run_analysis.py:178-181`)
- Commit sur branche dédiée `ai-analysis/{id}-{YYYYMMDD-HHMMSS}` et PR create/update (`analysis_git_service.py`)
- Locking par projet dans le supervisor — pas de double démarrage (`supervisor/main.py:126-134`, `281-329`)
- Propagation d'état via fichier JSON (`run_analysis.py:57-58`, `supervisor/main.py:332-349`)
- Détection de la mort du processus dans le supervisor (transition `running → failed` automatique, `supervisor/main.py:335-348`)
- Statut, logs et lien PR visibles dans le dashboard avec polling 5s (`DeployerPage.jsx:192-276`)
- Tests couvrant : prompt, orchestration, fichiers générés, git, PR, path traversal, erreur LLM

**Sécurité :**
- La protection contre path traversal est présente et testée — mais incomplète (voir ci-dessous)
- Path `project_root` validé via `resolve_project` déjà existant

**Qualité :**
- Code simple, fonctions courtes
- Aucune dépendance superflue
- Gestion d'erreurs explicite avec propagation dans le fichier d'état
- Zéro régression sur les endpoints deployer existants

---

## Problèmes détectés

### BLOQUANT — Path traversal bypass dans `run_analysis.py:187`

**Fichier** : `tools/agent_runner/run_analysis.py`, ligne 187

```python
if not rel_path.startswith(".ai-dev-factory/"):
    raise RuntimeError(...)
target = project_root / rel_path
target.write_text(content, encoding="utf-8")
```

**Problème** : le check `startswith(".ai-dev-factory/")` passe pour un chemin tel que `.ai-dev-factory/../../../etc/passwd`. Lors de la résolution OS, ce chemin échappe du répertoire projet.

- `.ai-dev-factory/../../../etc/passwd` commence par `.ai-dev-factory/` → check **passe**
- `/home/user/project/.ai-dev-factory/../../../etc/passwd` → résolu en `/etc/passwd`

**Le test existant** `test_main_path_traversal_rejected` ne couvre que le cas `../../etc/passwd` (sans le préfixe `.ai-dev-factory/`) — le bypass n'est pas testé.

**Correction requise** :

```python
target = (project_root / rel_path).resolve()
if not str(target).startswith(str(project_root.resolve()) + "/"):
    raise RuntimeError(
        f"LLM returned path escaping project root: {rel_path}"
    )
```

Et ajouter un test pour `.ai-dev-factory/../../../etc/passwd`.

---

### MINEUR — Validation du `deploy.yml` absent

Le critère d'acceptation stipule : _"Generated deploy.yml is valid and compatible with the deployer runtime."_ Après l'écriture des fichiers, aucune validation n'est faite que `deploy.yml` parse comme un `DeployProfile` valide. Si le LLM génère un YAML invalide ou non conforme, l'erreur ne sera découverte qu'au déploiement.

**Suggestion** (non bloquante) : après l'écriture, parser le `deploy.yml` avec `yaml.safe_load` et tenter une construction `DeployProfile(**data)` — rejeter si ça échoue.

---

### MINEUR — `get_analysis_status` avale silencieusement toutes les exceptions

`analysis_manager.py:60-63` :
```python
except Exception:
    return AnalysisStatus()
```

Si le supervisor est injoignable pendant le polling de statut, le dashboard affiche silencieusement `idle` sans indiquer l'erreur. Différencier au moins `httpx.ConnectError` pour remonter l'état `error="supervisor_unreachable"` (comme dans `start_analysis`).

---

### MINEUR — `--print` couplé implicitement au CLI Claude

`_invoke_llm` appende `--print` à tout `exec_cmd`. Ce flag est spécifique au CLI Claude. Toute autre valeur d'`exec_cmd` qui ne supporte pas ce flag échouera sans message explicite.

---

## Risques éventuels

- **Sécurité** : le bypass de path traversal exposé ci-dessus est exploitable si le LLM est compromis ou remplacé par une implémentation malveillante — priorité correction avant merge.
- **Fiabilité** : si `pyyaml` n'est pas installé sur l'hôte, `docker_services` sera toujours `[]` sans log visible (l'exception est absorbée dans `_scan_project`). Acceptable en graceful degradation.
- **Opérationnel** : la variable `AI_DEV_FACTORY_SUPERVISOR_URL` doit être configurée — son absence retourne 503. C'est documenté par le code mais pas par la documentation opérationnelle.

---

## Décision

- REQUEST_CHANGES — 1 problème de sécurité bloquant à corriger

## Actions demandées

1. **[Bloquant]** Corriger la protection path traversal dans `run_analysis.py:187-193` pour résoudre le chemin avant la comparaison, et ajouter un test couvrant `.ai-dev-factory/../../../etc/passwd`.
2. **[Recommandé]** Ajouter validation post-génération du `deploy.yml` contre le schéma `DeployProfile`.
3. **[Optionnel]** Différencier `ConnectError` dans `get_analysis_status` pour ne pas silencer les erreurs supervisor.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T130/reviews/implementation-review.md
- generated at: 2026-05-21T21:36:52Z

---

---

# PR Review — T130: AI-assisted operational project analysis and deploy profile generation

## Résumé

L'implémentation couvre l'ensemble des fonctionnalités demandées par le ticket : worker host-side (`run_analysis.py`), builder de prompt (`analysis_prompt_builder.py`), service git (`analysis_git_service.py`), endpoints supervisor, routes control API, composants frontend, et 20 tests unitaires. L'architecture est correcte et les flux de données sont cohérents.

Un défaut de sécurité bloquant a été identifié dans la protection contre le path traversal.

---

## Vérifications effectuées

- Lecture intégrale des 10 fichiers nouveaux et des fichiers modifiés
- Vérification de chaque critère d'acceptation du ticket
- Analyse des chemins d'exécution critiques (sécurité, erreurs, locking)
- Lecture de chaque fichier de test

---

## Points validés

**Fonctionnel — ticket couvert à ~95% :**
- Bouton "Analyze Project" dans la UI (`DeployerPage.jsx:267-271`)
- Scan déterministe du projet côté host (`run_analysis.py:85-111`)
- Génération du prompt avec schéma DeployProfile, arbre de fichiers et résultat du scan (`analysis_prompt_builder.py`)
- Invocation LLM via `exec_cmd` configuré — aucun provider hardcodé (`run_analysis.py:114-128`)
- Extraction des blocs `--- BEGIN FILE / END FILE ---` et écriture dans `.ai-dev-factory/` (`run_analysis.py:131-194`)
- Vérification que `deploy.yml` et `deployment.md` sont présents dans la sortie LLM (`run_analysis.py:178-181`)
- Commit sur branche dédiée `ai-analysis/{id}-{YYYYMMDD-HHMMSS}` et PR create/update (`analysis_git_service.py`)
- Locking par projet dans le supervisor — pas de double démarrage (`supervisor/main.py:126-134`, `281-329`)
- Propagation d'état via fichier JSON (`run_analysis.py:57-58`, `supervisor/main.py:332-349`)
- Détection de la mort du processus dans le supervisor (transition `running → failed` automatique, `supervisor/main.py:335-348`)
- Statut, logs et lien PR visibles dans le dashboard avec polling 5s (`DeployerPage.jsx:192-276`)
- Tests couvrant : prompt, orchestration, fichiers générés, git, PR, path traversal, erreur LLM

**Sécurité :**
- La protection contre path traversal est présente et testée — mais incomplète (voir ci-dessous)
- Path `project_root` validé via `resolve_project` déjà existant

**Qualité :**
- Code simple, fonctions courtes
- Aucune dépendance superflue
- Gestion d'erreurs explicite avec propagation dans le fichier d'état
- Zéro régression sur les endpoints deployer existants

---

## Problèmes détectés

### BLOQUANT — Path traversal bypass dans `run_analysis.py:187`

**Fichier** : `tools/agent_runner/run_analysis.py`, ligne 187

```python
if not rel_path.startswith(".ai-dev-factory/"):
    raise RuntimeError(...)
target = project_root / rel_path
target.write_text(content, encoding="utf-8")
```

**Problème** : le check `startswith(".ai-dev-factory/")` passe pour un chemin tel que `.ai-dev-factory/../../../etc/passwd`. Lors de la résolution OS, ce chemin échappe du répertoire projet.

- `.ai-dev-factory/../../../etc/passwd` commence par `.ai-dev-factory/` → check **passe**
- `/home/user/project/.ai-dev-factory/../../../etc/passwd` → résolu en `/etc/passwd`

**Le test existant** `test_main_path_traversal_rejected` ne couvre que le cas `../../etc/passwd` (sans le préfixe `.ai-dev-factory/`) — le bypass n'est pas testé.

**Correction requise** :

```python
target = (project_root / rel_path).resolve()
if not str(target).startswith(str(project_root.resolve()) + "/"):
    raise RuntimeError(
        f"LLM returned path escaping project root: {rel_path}"
    )
```

Et ajouter un test pour `.ai-dev-factory/../../../etc/passwd`.

---

### MINEUR — Validation du `deploy.yml` absent

Le critère d'acceptation stipule : _"Generated deploy.yml is valid and compatible with the deployer runtime."_ Après l'écriture des fichiers, aucune validation n'est faite que `deploy.yml` parse comme un `DeployProfile` valide. Si le LLM génère un YAML invalide ou non conforme, l'erreur ne sera découverte qu'au déploiement.

**Suggestion** (non bloquante) : après l'écriture, parser le `deploy.yml` avec `yaml.safe_load` et tenter une construction `DeployProfile(**data)` — rejeter si ça échoue.

---

### MINEUR — `get_analysis_status` avale silencieusement toutes les exceptions

`analysis_manager.py:60-63` :
```python
except Exception:
    return AnalysisStatus()
```

Si le supervisor est injoignable pendant le polling de statut, le dashboard affiche silencieusement `idle` sans indiquer l'erreur. Différencier au moins `httpx.ConnectError` pour remonter l'état `error="supervisor_unreachable"` (comme dans `start_analysis`).

---

### MINEUR — `--print` couplé implicitement au CLI Claude

`_invoke_llm` appende `--print` à tout `exec_cmd`. Ce flag est spécifique au CLI Claude. Toute autre valeur d'`exec_cmd` qui ne supporte pas ce flag échouera sans message explicite.

---

## Risques éventuels

- **Sécurité** : le bypass de path traversal exposé ci-dessus est exploitable si le LLM est compromis ou remplacé par une implémentation malveillante — priorité correction avant merge.
- **Fiabilité** : si `pyyaml` n'est pas installé sur l'hôte, `docker_services` sera toujours `[]` sans log visible (l'exception est absorbée dans `_scan_project`). Acceptable en graceful degradation.
- **Opérationnel** : la variable `AI_DEV_FACTORY_SUPERVISOR_URL` doit être configurée — son absence retourne 503. C'est documenté par le code mais pas par la documentation opérationnelle.

---

## Décision

- REQUEST_CHANGES — 1 problème de sécurité bloquant à corriger

## Actions demandées

1. **[Bloquant]** Corriger la protection path traversal dans `run_analysis.py:187-193` pour résoudre le chemin avant la comparaison, et ajouter un test couvrant `.ai-dev-factory/../../../etc/passwd`.
2. **[Recommandé]** Ajouter validation post-génération du `deploy.yml` contre le schéma `DeployProfile`.
3. **[Optionnel]** Différencier `ConnectError` dans `get_analysis_status` pour ne pas silencer les erreurs supervisor.

IMPLEMENTATION_FIX_REQUIRED