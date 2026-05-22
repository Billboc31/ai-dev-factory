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
