# PR Review — T117

## Résumé

Implémentation des 6 correctifs prévus au plan : tous présents et techniquement corrects dans leur périmètre. Cependant, des modifications hors scope sur `docker-compose.yml` et `deploy/.env` ont été introduites sans couverture dans le plan approuvé, dont l'une introduit un bug de régression potentiel sur l'architecture runtime T116, et une autre casse les déploiements fresh. Un bug de correctness sur le `--rebase` sans abort est également bloquant.

## Vérifications effectuées

- Lecture de tous les fichiers modifiés vs `main` via `git diff`
- Vérification de la correspondance plan → implémentation (6 bugs, 6 correctifs)
- Analyse des chemins de failure dans `_sync_ticket_branch()` avec `--rebase`
- Vérification du `.gitignore` pour `runtime.log` (déjà présent sur main)
- Lecture complète de `docker-compose.yml` avant/après et de la suppression `deploy/.env`
- Lecture de `docs/daemon-lifecycle.md`

## Points validés

| Étape plan | Fichier | Verdict |
|---|---|---|
| Fix 1 : `--auto-commit`, `--auto-push`, `--worktrees-dir` | `daemon_manager.py` | ✅ Correct |
| Fix 2 : `git checkout -f main` à chaque `ensure_intake_worktree` | `worktree_manager.py` | ✅ Correct (voir observation mineure) |
| Fix 3 : `git ls-files --error-unmatch` avant restore | `run_issue_intake.py` | ✅ Correct |
| Fix 4 : création on-demand + skip sans fallback legacy | `run_daemon.py` | ✅ Correct |
| Fix 5 : `--rebase` au lieu de `--ff-only` | `run_daemon.py` | ✅ Intentionnel, mais incomplet (voir BLOQUANT #2) |
| Fix 6 : documentation lifecycle daemon | `docs/daemon-lifecycle.md` | ✅ Complète et précise |

## Problèmes détectés

### BLOQUANT #1 — Modifications hors scope sur Docker/deploy

Le plan approuvé liste explicitement sous **Hors scope** : `Docker / deploy`.

Pourtant deux fichiers ont été modifiés :

**`docker-compose.yml`** : le volume mount est changé de `~/runtime/ai-dev-factory:/runtime` (bind mount host-accessible) vers `runtime-data:/runtime` (named Docker volume). Ce changement :
- Sort du scope approuvé
- Brise la visibilité du runtime depuis le host (le daemon host-side ne peut plus accéder au runtime data via le chemin hôte)
- Est potentiellement une régression de l'architecture établie par T116 ("canonical runtime root", "do not reintroduce repo-local runtime ownership")

**`deploy/.env`** : fichier supprimé. Ce fichier était une erreur de commit sur `main` (contenait un PAT réel, commentaire disait "never committed"), mais sa suppression :
- Laisse `docker-compose.yml` avec `env_file: deploy/.env` pointant sur un fichier inexistant
- Casse `docker-compose up` pour tout déploiement fresh ("`no such file or directory`")
- Supprime la documentation des variables d'environnement attendues sans aucun remplacement

**Correction requise** : soit reverter ces changements, soit les justifier explicitement et corriger le `env_file` (créer `deploy/.env.example` avec les variables attendues, sans secrets).

---

### BLOQUANT #2 — `git pull --rebase` sans `git rebase --abort` sur échec

Dans `run_daemon.py`, `_sync_ticket_branch()` :

```python
result = subprocess.run(
    ["git", "pull", "--rebase", "origin", branch],
    ...
)
...
_log(f"{ticket_id}: sync branch {branch!r} failed — rebase conflict: {stderr}")
return False
```

Si un conflit de rebase se produit (plus probable maintenant avec des commits humains sur la branche), la fonction retourne `False` **sans appeler `git rebase --abort`**. Le worktree reste en état `rebase in progress`. Au cycle suivant, le `git pull --rebase` échoue avec "`rebase in progress`" et continue d'échouer indéfiniment — le ticket est bloqué de façon permanente.

**Correction requise** : ajouter `subprocess.run(["git", "rebase", "--abort"], cwd=cwd, capture_output=True)` dans le chemin d'échec avant de logger et retourner `False`.

## Risques éventuels

### Observation mineure — résultat de `git checkout -f main` non vérifié

Dans `worktree_manager.py`, `ensure_intake_worktree()` :

```python
subprocess.run(
    ["git", "checkout", "-f", "main"],
    capture_output=True, text=True, check=False,
    cwd=str(intake_path),
)
return True, intake_path
```

`check=False` + pas de vérification du returncode = retour `True` même si le checkout a échoué (ex: detached HEAD sans ref `main`). Recommandé : logger un warning si `returncode != 0`, et éventuellement retourner `False, intake_path` pour forcer recréation.

### Information — PAT GitHub dans l'historique git

Le fichier `deploy/.env` supprimé contenait un GitHub PAT réel sur `main`. Sa suppression ne retire pas le token de l'historique git. Ce token doit être révoqué et remplacé. Ce n'est pas un problème introduit par T117, mais la suppression du fichier devrait s'accompagner d'une note explicite.

## Décision

- REQUEST_CHANGES

## Actions demandées

1. **Reverter ou corriger les changements `docker-compose.yml` et `deploy/.env`** : soit les reverter (ils sortent du scope approuvé), soit documenter la justification, corriger le `env_file` cassé, et créer un `deploy/.env.example` avec les variables attendues (sans secrets).

2. **Ajouter `git rebase --abort` dans `_sync_ticket_branch()` sur échec** : avant de logger l'erreur et retourner `False`, appeler `git rebase --abort` pour sortir le worktree de l'état mid-rebase.

3. **(Mineur, recommandé)** Logger un warning dans `ensure_intake_worktree()` si `git checkout -f main` retourne un code non-zéro.

4. **(Hors T117 mais urgent)** Révoquer le GitHub PAT exposé dans l'historique git (`github_pat_11BU2KSUA0eNUOYTUUYPCt_...`).
