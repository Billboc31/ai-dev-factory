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


# T175 — T175 - Environment creation UI must expose and validate runtime/deployment target

**Source**: GitHub Issue #202

## Description

# T175 - Environment creation UI must expose and validate runtime/deployment target

## Problem

The current environment creation flow hides important runtime/deployment target information.

During recent environment deploy testing:

- scripts were correctly executed from the fresh sandbox clone
- but the runtime/project context remained ambiguous
- the UI never clearly indicated where the environment would actually be deployed
- logs still referenced mixed runtime/project paths

This creates confusion about:

- which runtime is active
- where the sandbox is deployed
- which runtime root owns the environment
- whether deployment uses the fresh runtime or host runtime
- whether multiple runtime roots are conflicting

---

## Current confusing behavior

Example:

```text
source_path=/Users/.../sandboxes/.../source
```

but:

```text
project_root=/Users/.../runtime/ai-dev-factory/clones/ai-dev-factory
```

The deployment technically works, but the runtime ownership and deployment target remain unclear.

---

## Goal

The environment creation popup and deployment flow must:

- clearly expose the deployment/runtime target
- make runtime ownership explicit
- validate runtime consistency before deploy
- eliminate ambiguity between:
  - source clone
  - project root
  - runtime root
  - sandbox root

---

## Required UI changes

The popup must clearly display:

- current project
- repository
- selected branch
- runtime root
- sandbox destination path
- environment name

Example:

```text
Project: ai-dev-factory
Branch: main
Runtime root: /Users/.../sandboxes/ai-dev-factory
Environment path: /Users/.../sandboxes/ai-dev-factory/<sandbox-id>
```

The user must understand exactly where the environment will run.

---

## Required validation

Before deploy:

validate:

- runtime_root is consistent
- source_path belongs to runtime_root
- worktree/sandbox ownership is correct
- deploy scripts come from the sandbox source clone
- project_root and source_path are not silently mixed

If inconsistent:

fail clearly with explicit runtime mismatch diagnostics.

---

## Required logging

Before bootstrap:

```text
runtime_root=<runtime root>
sandbox_root=<sandbox root>
source_path=<source clone>
project_root=<project root>
script_source=<resolved scripts directory>
```

---

## Acceptance criteria

- Environment popup clearly shows deployment target/runtime
- Runtime ownership is understandable from the UI
- Logs clearly distinguish project_root vs source_path vs runtime_root
- Runtime mismatch situations fail explicitly
- Users can verify deploy destination before launching
- Sandbox deploy always uses scripts from sandbox source clone
- No hidden fallback to another runtime root

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 4 source files modified as planned (the `runtime.log` update is the auto-generated run log, not a code change). Implementation is complete.

---

## Summary

**Files modified:**

### Backend
- **`environment_provision.py`** — Added `_validate_runtime_consistency()` (called after `validate_project_root_on_host`): detects `project_root == sandbox_path`, either path nested inside the other, or missing parent dir; raises `ValueError` with explicit mismatch diagnostics. Also fixed the mislabeled `runtime_root=` log field to `project_root=` and added `sandbox_path=`.

- **`sandbox_runtime_deploy.py`** — Added an early assertion that `source_path` is inside `sandbox_dir` (explicit guard, fails with a clear RuntimeError). Added a five-line path header written to both `run.log` and `logger.info` at the start of every deploy: `runtime_root`, `sandbox_root`, `source_path`, `project_root`, `script_source`.

### Frontend
- **`CreateEnvironmentModal.jsx`** — Added a static "Runtime target" info block in the manual-entry form (non-project-id flow), showing `sandbox_path`, `sandbox_path/runtime`, and `sandbox_path/source`; updates reactively. Displays "(auto-assigned)" when no sandbox path is set.

- **`EnvironmentCard.jsx`** — Added a collapsible "Runtime paths" toggle (same pattern as Debug section) showing `project_root`, `runtime_root`, `sandbox_dir`, and `source_path` from the API response; only rendered when at least one field is non-empty.

---

## Review

Now I have enough information to write the full review.

---

# PR Review — T175

## Résumé

Implémentation de 4 fichiers modifiés (2 backend, 2 frontend) pour exposer et valider les cibles de déploiement runtime dans le flux de création d'environnement. Le périmètre correspond globalement au plan. La validation backend est solide. Trois problèmes significatifs ont été trouvés.

## Vérifications effectuées

- Lecture du diff complet des 4 fichiers modifiés contre `main`
- Vérification de la sérialisation API (`SandboxState`, `routes/environments.py`) pour confirmer la disponibilité des champs runtime dans la réponse
- Lecture du composant `CreateEnvironmentModal.jsx` pour comprendre les deux branches de rendu (project-ID vs. manual entry)
- Vérification de la logique du guard dans `sandbox_runtime_deploy.py` (construction de `source_path`)
- Vérification de la validité de la classe CSS `not-font-mono`
- Vérification des critères d'acceptation du ticket vs. implémentation

## Points validés

- **`_validate_runtime_consistency()` est correcte et exhaustive** : détecte `project == sandbox`, `sandbox` imbriqué dans `project`, `project` imbriqué dans `sandbox`, et parent dir manquant. Chaque cas lève un `ValueError` avec un message diagnostique explicite. Intégrée au bon endroit dans `provision_environment()`.

- **Logging fix dans `environment_provision.py`** : le label `runtime_root=` a été corrigé en `project_root=` et `sandbox_path=` a été ajouté. Conforme au plan et au ticket.

- **5-line path header dans `sandbox_runtime_deploy.py`** : écrit dans `run.log` et `logger.info` avant le bootstrap, avec les 5 champs requis par le ticket : `runtime_root`, `sandbox_root`, `source_path`, `project_root`, `script_source`. 

- **`EnvironmentCard.jsx` — Runtime paths section** : implémentation correcte en collapsible, même pattern que la section Debug existante. Les 4 champs (`project_root`, `sandbox_runtime_root`, `sandbox_dir`, `source_path`) sont déjà présents dans `SandboxState` et sérialisés nativement — aucune modification de sérialisation n'était nécessaire.

- **Gestion HTTP 422** : `ValueError` issu de `_validate_runtime_consistency` est bien capturé et retourné en 422 dans `routes/environments.py` (ligne 129-130).

## Problèmes détectés

### P1 — Guard mort dans `sandbox_runtime_deploy.py` (lignes 283-287)

```python
source_path = sandbox_dir / "source"  # toujours sous sandbox_dir par construction
if not source_path.is_relative_to(sandbox_dir):  # ← ne peut jamais être True
    raise RuntimeError(...)
```

`source_path` est construit directement comme `sandbox_dir / "source"` à la ligne précédente. Il sera toujours relative à `sandbox_dir`. La condition sera toujours `False`, le `RuntimeError` ne peut jamais être levé. Ce guard est du dead code qui simule une protection sans en fournir réellement une. Il induit en erreur les futurs mainteneurs.

**Impact** : Le ticket exige "Sandbox deploy always uses scripts from sandbox source clone" et "No hidden fallback to another runtime root". Ce guard ne protège pas contre cela — il est tautologiquement vrai.

**Correction attendue** : soit supprimer le guard (inutile), soit déplacer la protection vers une assertion utile, par exemple vérifier que `script_source` (`.ai-dev-factory/scripts`) existe réellement avant d'exécuter les scripts.

---

### P2 — Bloc "Runtime target" absent du flux project-ID

Dans `CreateEnvironmentModal.jsx`, le bloc "Runtime target" est rendu uniquement dans le `else` de `!projectId` (branch manual entry, lignes 238+). Quand `projectId` est fourni (cas nominal d'utilisation depuis le panel projets), le bloc n'apparaît pas.

Le ticket est explicite :

> "The environment creation popup and deployment flow must: clearly expose the deployment/runtime target"

Il n'y a aucune restriction au flux sans project-ID. Dans le flux avec project-ID, le `sandbox_path` est auto-assigné, ce qui rend le déploiement encore plus opaque pour l'utilisateur — c'est précisément le cas où afficher "auto-assigned" est utile.

**Correction attendue** : ajouter le bloc (avec `(auto-assigned)` pour tous les champs) également dans la branche project-ID, idéalement après le sélecteur de branche. Ou extraire le bloc en composant et l'inclure dans les deux branches.

---

### P3 — Classe CSS invalide `not-font-mono` (lignes 264, 268, 274)

```jsx
<span className="text-blue-600 not-font-mono font-medium">Sandbox path: </span>
```

`not-font-mono` n'est pas une classe Tailwind valide. Tailwind ne dispose pas d'un préfixe `not-` pour annuler des utilities. L'intent est probablement d'exclure ces `<span>` du `font-mono` appliqué sur le `<div>` parent. La classe correcte serait `font-sans`.

**Impact** : actuellement aucun effet visuel (la classe est ignorée par le moteur CSS). Les labels héritent du `font-mono` du parent — les titres "Sandbox path:", "Runtime root:", "Source clone:" s'affichent en monospace alors qu'ils devraient probablement être en sans-serif.

**Correction** : remplacer `not-font-mono` par `font-sans` sur les 3 spans.

## Risques éventuels

- **`script_source` loggué mais non validé** : le champ `script_source` est calculé comme `source_path / ".ai-dev-factory" / "scripts"` et inclus dans le log, mais aucune vérification d'existence n'est faite. Si les scripts ne sont pas présents à cet emplacement dans le sandbox source clone, le déploiement échouera plus tard avec un message d'erreur moins clair. Accepté dans le plan comme exclu (pas d'E2E), mais à surveiller.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **[Bloquant] Supprimer ou corriger le guard mort** dans `sandbox_runtime_deploy.py` (lignes 283-287). Si une protection est souhaitée, vérifier l'existence effective de `script_source` (`.ai-dev-factory/scripts`).

2. **[Bloquant] Ajouter le bloc "Runtime target" dans le flux project-ID** de `CreateEnvironmentModal.jsx`. Le cas nominal (création depuis le panel projets) doit aussi montrer la cible de déploiement, même si tous les champs affichent "(auto-assigned)".

3. **[Mineur] Corriger `not-font-mono` → `font-sans`** sur les 3 spans labels dans `CreateEnvironmentModal.jsx`.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T175/reviews/implementation-review.md
- generated at: 2026-06-05T07:47:20Z

---

Now I have enough information to write the full review.

---

# PR Review — T175

## Résumé

Implémentation de 4 fichiers modifiés (2 backend, 2 frontend) pour exposer et valider les cibles de déploiement runtime dans le flux de création d'environnement. Le périmètre correspond globalement au plan. La validation backend est solide. Trois problèmes significatifs ont été trouvés.

## Vérifications effectuées

- Lecture du diff complet des 4 fichiers modifiés contre `main`
- Vérification de la sérialisation API (`SandboxState`, `routes/environments.py`) pour confirmer la disponibilité des champs runtime dans la réponse
- Lecture du composant `CreateEnvironmentModal.jsx` pour comprendre les deux branches de rendu (project-ID vs. manual entry)
- Vérification de la logique du guard dans `sandbox_runtime_deploy.py` (construction de `source_path`)
- Vérification de la validité de la classe CSS `not-font-mono`
- Vérification des critères d'acceptation du ticket vs. implémentation

## Points validés

- **`_validate_runtime_consistency()` est correcte et exhaustive** : détecte `project == sandbox`, `sandbox` imbriqué dans `project`, `project` imbriqué dans `sandbox`, et parent dir manquant. Chaque cas lève un `ValueError` avec un message diagnostique explicite. Intégrée au bon endroit dans `provision_environment()`.

- **Logging fix dans `environment_provision.py`** : le label `runtime_root=` a été corrigé en `project_root=` et `sandbox_path=` a été ajouté. Conforme au plan et au ticket.

- **5-line path header dans `sandbox_runtime_deploy.py`** : écrit dans `run.log` et `logger.info` avant le bootstrap, avec les 5 champs requis par le ticket : `runtime_root`, `sandbox_root`, `source_path`, `project_root`, `script_source`. 

- **`EnvironmentCard.jsx` — Runtime paths section** : implémentation correcte en collapsible, même pattern que la section Debug existante. Les 4 champs (`project_root`, `sandbox_runtime_root`, `sandbox_dir`, `source_path`) sont déjà présents dans `SandboxState` et sérialisés nativement — aucune modification de sérialisation n'était nécessaire.

- **Gestion HTTP 422** : `ValueError` issu de `_validate_runtime_consistency` est bien capturé et retourné en 422 dans `routes/environments.py` (ligne 129-130).

## Problèmes détectés

### P1 — Guard mort dans `sandbox_runtime_deploy.py` (lignes 283-287)

```python
source_path = sandbox_dir / "source"  # toujours sous sandbox_dir par construction
if not source_path.is_relative_to(sandbox_dir):  # ← ne peut jamais être True
    raise RuntimeError(...)
```

`source_path` est construit directement comme `sandbox_dir / "source"` à la ligne précédente. Il sera toujours relative à `sandbox_dir`. La condition sera toujours `False`, le `RuntimeError` ne peut jamais être levé. Ce guard est du dead code qui simule une protection sans en fournir réellement une. Il induit en erreur les futurs mainteneurs.

**Impact** : Le ticket exige "Sandbox deploy always uses scripts from sandbox source clone" et "No hidden fallback to another runtime root". Ce guard ne protège pas contre cela — il est tautologiquement vrai.

**Correction attendue** : soit supprimer le guard (inutile), soit déplacer la protection vers une assertion utile, par exemple vérifier que `script_source` (`.ai-dev-factory/scripts`) existe réellement avant d'exécuter les scripts.

---

### P2 — Bloc "Runtime target" absent du flux project-ID

Dans `CreateEnvironmentModal.jsx`, le bloc "Runtime target" est rendu uniquement dans le `else` de `!projectId` (branch manual entry, lignes 238+). Quand `projectId` est fourni (cas nominal d'utilisation depuis le panel projets), le bloc n'apparaît pas.

Le ticket est explicite :

> "The environment creation popup and deployment flow must: clearly expose the deployment/runtime target"

Il n'y a aucune restriction au flux sans project-ID. Dans le flux avec project-ID, le `sandbox_path` est auto-assigné, ce qui rend le déploiement encore plus opaque pour l'utilisateur — c'est précisément le cas où afficher "auto-assigned" est utile.

**Correction attendue** : ajouter le bloc (avec `(auto-assigned)` pour tous les champs) également dans la branche project-ID, idéalement après le sélecteur de branche. Ou extraire le bloc en composant et l'inclure dans les deux branches.

---

### P3 — Classe CSS invalide `not-font-mono` (lignes 264, 268, 274)

```jsx
<span className="text-blue-600 not-font-mono font-medium">Sandbox path: </span>
```

`not-font-mono` n'est pas une classe Tailwind valide. Tailwind ne dispose pas d'un préfixe `not-` pour annuler des utilities. L'intent est probablement d'exclure ces `<span>` du `font-mono` appliqué sur le `<div>` parent. La classe correcte serait `font-sans`.

**Impact** : actuellement aucun effet visuel (la classe est ignorée par le moteur CSS). Les labels héritent du `font-mono` du parent — les titres "Sandbox path:", "Runtime root:", "Source clone:" s'affichent en monospace alors qu'ils devraient probablement être en sans-serif.

**Correction** : remplacer `not-font-mono` par `font-sans` sur les 3 spans.

## Risques éventuels

- **`script_source` loggué mais non validé** : le champ `script_source` est calculé comme `source_path / ".ai-dev-factory" / "scripts"` et inclus dans le log, mais aucune vérification d'existence n'est faite. Si les scripts ne sont pas présents à cet emplacement dans le sandbox source clone, le déploiement échouera plus tard avec un message d'erreur moins clair. Accepté dans le plan comme exclu (pas d'E2E), mais à surveiller.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **[Bloquant] Supprimer ou corriger le guard mort** dans `sandbox_runtime_deploy.py` (lignes 283-287). Si une protection est souhaitée, vérifier l'existence effective de `script_source` (`.ai-dev-factory/scripts`).

2. **[Bloquant] Ajouter le bloc "Runtime target" dans le flux project-ID** de `CreateEnvironmentModal.jsx`. Le cas nominal (création depuis le panel projets) doit aussi montrer la cible de déploiement, même si tous les champs affichent "(auto-assigned)".

3. **[Mineur] Corriger `not-font-mono` → `font-sans`** sur les 3 spans labels dans `CreateEnvironmentModal.jsx`.

IMPLEMENTATION_FIX_REQUIRED