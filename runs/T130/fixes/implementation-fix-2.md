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
