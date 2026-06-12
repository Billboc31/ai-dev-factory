I have read all the relevant files. Here is the full review.

---

# PR Review — T186: Auto-register current AI Dev Factory project

## Résumé

Three targeted files changed (`git_root.py` new, `project_bootstrap.py` extended, `main.py` patched) plus two new test files (13 tests). The implementation matches the plan precisely and meets all ticket acceptance criteria.

## Vérifications effectuées

- Lecture du ticket, du plan, et de l'implementation-output
- Lecture complète de `git_root.py`, `project_bootstrap.py` (diff entre `bootstrap` et `auto_bootstrap`), et du patch `main.py`
- Lecture de `project_id.py` et `project_registry.py` pour valider les interactions
- Lecture de `test_git_root.py` et `test_auto_bootstrap.py`

## Points validés

**Correctness — worktree resolution**
`resolve_git_root` suit correctement la chaîne `.git` file → `gitdir` → `commondir` → parent. Les trois cas (clone normal, worktree, non-git) sont couverts avec fallback gracieux sur exception. Le check final `(_git_root / ".git").exists()` dans `main.py` fonctionne correctement : le main clone root a toujours `.git` en tant que répertoire.

**Idempotence**
`auto_bootstrap` utilise `ensure_registered()` (qui ne lève pas si le projet est déjà présent) et `mkdir(parents=True, exist_ok=True)` pour les sous-répertoires. Pas de levée d'exception au redémarrage. Testé dans `test_auto_bootstrap_is_idempotent`. ✓

**Stabilité du project ID**
`normalize_project_id(_git_root.name)` produit `"ai-dev-factory"` indépendamment du répertoire worktree dans lequel tourne le processus. ✓

**Scope borné**
`auto_bootstrap` est une fonction séparée de `bootstrap`. Aucun changement de signature ou comportement de `bootstrap`. Aucun changement aux routes, au registry, à `project_id.py`, ni au frontend. Entièrement conforme au plan.

**Sécurité**
La lecture du fichier `.git` pour en extraire un chemin ne comporte pas de risque d'exécution — c'est une opération purement filesystem, protégée par le bloc `except Exception`. Le path traversal est couvert par `assert_contained` (qui était déjà en place).

**Validation d'entrée**
`validate_project_id` est appelé en premier dans `auto_bootstrap`. Si l'ID est invalide, log + return sans propager. Le cas extrême d'un nom de répertoire de 65+ chars avec un '-' en position 64 (que `normalize` ne trimme pas après troncature) serait catcherré par ce guard. Non-bloquant.

**Couverture de tests**
`test_git_root.py` : 5 cas (clone normal, non-git, worktree, `.git` file malformé, `commondir` absent). `test_auto_bootstrap.py` : 8 cas (runtime dirs, project.yml, pas d'écrasement, idempotence, runtime_root=None ×2, ID invalide, path worktree). La couverture est adéquate.

## Problèmes détectés

**Observation mineure (non-bloquante) — test manquant**
`test_auto_bootstrap_writes_project_yml` vérifie la présence de `name:` et `bootstrapped_at:` dans `project.yml` mais pas de `stack:`. Le plan stipule "correct `name` and `stack` fields". Acceptable car la fonctionnalité de `detect_stack` est testée ailleurs, mais la complétude du test est légèrement incomplète.

**Observation mineure (non-bloquante) — double entrée en mode single-root + worktree**
Quand aucune variable d'environnement n'est définie (`_pr=None`, `_runtime_root=None`), le registry est initialisé via `from_single_root(_root)` avec `id=_root.name` (ex: `"T186"`). Puis `auto_bootstrap` ajoute `"ai-dev-factory"`. Le registry contient alors deux entrées. Cela n'affecte que le mode développeur local sans env vars (non-production). Le projet "T186" aurait une registration incomplète mais le projet "ai-dev-factory" serait correct.

## Risques éventuels

Aucun risque bloquant identifié. L'implémentation est défensive, idempotente, et bornée au scope du ticket.

## Décision

L'implémentation est correcte, conforme au plan et au ticket, et ne présente aucun problème bloquant. Les deux observations mineures n'affectent pas la fonctionnalité en production.

IMPLEMENTATION_APPROVED
