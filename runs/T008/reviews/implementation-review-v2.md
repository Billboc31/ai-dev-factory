Voici la review structurée de l'implémentation.

---

## Review T008 — mode `--auto`

**Verdict global : IMPLEMENTATION_FIX_REQUIRED**

L'architecture générale est correcte et les invariants principaux sont respectés. Trois défauts méritent correction avant approbation.

---

### ✅ Points validés

| Critère | Statut |
|---|---|
| 8 états valides définis | ✓ |
| 10 transitions correctes (table `TRANSITIONS`) | ✓ |
| `state.json` seule source de vérité | ✓ |
| `workflow-status.md` append-only, jamais lu | ✓ |
| 5 gates pré-exécution présents et séquentiels | ✓ |
| Écriture atomique (write + rename) | ✓ |
| Regex `^KEYWORD$` MULTILINE | ✓ |
| Multiple keywords → first wins + warning | ✓ |
| Pas de merge, pas de boucle | ✓ |
| `--auto-init` refuse d'écraser `state.json` existant | ✓ |
| Validation de branche dans `--auto-init` | ✓ |
| `--exec-cmd` obligatoire avec `--auto` | ✓ |
| `TEST_COMPLETE` → exit 0 + message clair | ✓ |

---

### 🔴 Défaut 1 — Transition d'état après step en échec (bloquant)

**Fichier** : `run_ticket.py:343-346`

```python
rc, output_content = _call_run_step(ticket_id, step, exec_cmd)
_log_runtime(ticket_id, f"auto-run: step={step} done rc={rc}")

next_state = _determine_next_state(is_deterministic, output_content, possible_next)
```

Le code capture `rc` mais ne l'utilise jamais pour bloquer la transition. Pour les étapes déterministes (`planner`, `coder`, `tester`), `_determine_next_state` retourne `possible_next[0]` inconditionnellement. Si `run_step.py` échoue (timeout, crash Claude, API error), l'état avance quand même : ex. `PLAN_APPROVED → IMPLEMENTATION_REVIEW_NEEDED` sans implémentation produite.

**Correction attendue** : bloquer avec exit code 2 si `rc != 0` (après log et avant la détermination du next state).

---

### 🟡 Défaut 2 — Sortie bufferisée, pas de visibilité live

**Fichier** : `run_ticket.py:78-84` (`run_command`) et `run_ticket.py:230-248` (`_call_run_step`)

`capture_output=True` accumule tout stdout/stderr en mémoire jusqu'à la fin du processus. Pour un step Claude qui dure plusieurs minutes, l'utilisateur voit un terminal vide puis une avalanche de sortie. Le critère "logs visibles" du plan est partiellement manqué.

Le plan n'impose pas de streaming temps réel, mais le `runtime.log` n'est pas mentionné dans le README comme mécanisme de monitoring alternatif (`tail -f runs/TXXX/runtime.log`).

**Correction attendue** : ajouter dans le README une mention de `runtime.log` comme point de monitoring pendant un step long. Le streaming live serait souhaitable mais représente un changement plus profond.

---

### 🟡 Défaut 3 — Portabilité de `path.with_suffix(".json.tmp")`

**Fichier** : `run_ticket.py:190`

```python
tmp = path.with_suffix(".json.tmp")
```

Sur Python 3.12+, `with_suffix()` valide que le suffixe ne contient pas de point interne, selon la PEP et le changelog. `.json.tmp` contient un point après la première position, ce qui peut lever un `ValueError` selon la version et la build Python exacte. 

**Correction attendue** : remplacer par `path.parent / (path.name + ".tmp")` — équivalent sûr sur toutes les versions.

---

### ⚪ Points mineurs (non bloquants)

**Commentaires de gates incohérents** (`run_ticket.py:314, 321`) : les gates 1 et 2 (dans `load_state`) n'ont pas de label commentaire, les gates 3-5 en ont. Cohérence recommandée.

**Couplage `DEFAULT_OUTPUTS`** (`run_ticket.py:48-54`) : la contrainte "must stay in sync with run_step.py" n'est pas vérifiable statiquement. Si le chemin change dans `run_step.py`, la détection de keywords échouera silencieusement avec exit 1 ("no keyword found"). Envisager une assertion ou un test de cohérence.

**Session example README** : l'exemple montre 6 invocations `--auto` (correct) mais le plan v2 mentionnait "7 invocations" (qui comptait `--auto-init`). Pas d'impact utilisateur, mais la documentation gagne à préciser "6 invocations `--auto`" ou "7 invocations au total (`--auto-init` inclus)".

---

### Résumé des corrections requises

| Priorité | Fichier | Correction |
|---|---|---|
| 🔴 Bloquant | `run_ticket.py:343` | Vérifier `rc != 0` avant la transition, bloquer exit 2 |
| 🟡 Modéré | `run_ticket.py:190` | `path.parent / (path.name + ".tmp")` |
| 🟡 Modéré | `README.md` | Mentionner `runtime.log` comme monitoring step long |

**IMPLEMENTATION_FIX_REQUIRED**
