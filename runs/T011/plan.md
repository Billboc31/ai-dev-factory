J'ai tous les éléments. Voici le plan détaillé pour T011.

---

## Plan — T011 : Workflow Engine Stabilization

### Diagnostic des problèmes

#### Bug critique 1 : Fix loops toujours cassées (naming mismatch)

`run_step.py:44` écrit les reviews dans `reviews/review.md`.  
`_collect_fix_artifacts` (`run_ticket.py:268-298`) cherche `reviews/plan-review*.md` et `reviews/implementation-review*.md`.  
→ Le glob ne trouve jamais rien. Les fix loops ne peuvent pas fonctionner.

#### Bug critique 2 : Keyword detection aveugle

`_determine_next_state` (`run_ticket.py:212-227`) parse le contenu de l'output mais ne log ni le fichier parsé, ni le keyword trouvé, ni l'absence de keyword. Les transitions silencieuses sont inobservables.

#### Problème structurel : DEFAULT_OUTPUTS dupliqués

`run_step.py:38-45` et `run_ticket.py:49-54` maintiennent chacun leur propre `DEFAULT_OUTPUTS`. Ils ont déjà divergé : `run_step.py` inclut `memory-updater` et `memory-apply`, `run_ticket.py` non.

#### Problème documentaire : review humaine vs agent

L'`--auto` déclenche une review agent via `--exec-cmd`. La review humaine n'a pas de commande dédiée dans `run_ticket.py` : il faut éditer `state.json` à la main. Ce n'est ni documenté, ni sécurisé (pas de validation d'état).

Note : `run_step.py --set-status` écrit dans `workflow-status.md` (ancien système), pas dans `state.json` — ce n'est pas une alternative.

---

### Changements prévus

#### Étape 1 — `run_step.py` : paramètre `--output-path`

Ajouter un paramètre `--output-path` optionnel au mode `--exec-cmd`.

```
parse_args : +argument --output-path
main / exec_cmd block :
  si --output-path fourni → ensure_safe_relative_path(args.output_path)
  sinon → default_output_path(ticket_id, step)  [comportement inchangé]
```

Aucun comportement existant n'est modifié quand `--output-path` est absent.

#### Étape 2 — `run_ticket.py` : review naming context-aware

Ajouter une fonction :

```python
def _review_output_rel(current_state: str) -> str:
    if current_state == "PLAN_REVIEW_NEEDED":
        return "reviews/plan-review.md"
    if current_state == "IMPLEMENTATION_REVIEW_NEEDED":
        return "reviews/implementation-review.md"
    return DEFAULT_OUTPUTS["review"]  # fallback
```

Modifier `_call_run_step` pour accepter `current_state: str | None = None` :
- Si `step == "review"` et `current_state` connu → dériver `output_rel` via `_review_output_rel`, passer `--output-path runs/TXXX/{output_rel}` à `run_step.py`
- Sinon → comportement actuel inchangé

Modifier l'appel dans `auto_run` : passer `current_state=current_state`.

#### Étape 3 — `run_ticket.py` : observabilité keyword detection

Dans `auto_run`, après `_call_run_step`, pour les steps non-déterministes (`is_deterministic=False`) :

```
_log_runtime: "auto-run: review parsed from: {output_path}"
```

Après `_determine_next_state` :

```
si next_state trouvé :
    _log_runtime: "auto-run: keyword detected: {next_state}"
si next_state None :
    _log_runtime: "auto-run: no keyword found in {output_path}"
```

Pour les steps déterministes, pas de parsing → pas de log superflu.

#### Étape 4 — `run_ticket.py` : commande `--set-state` pour review humaine

Ajouter `--set-state` dans `parse_args` et une fonction dédiée :

```python
def set_workflow_state(ticket_id: str, new_state: str) -> int:
    # valide que new_state ∈ VALID_STATES
    # charge state.json existant
    # sauvegarde avec nouvelle valeur
    # log: "set-state: {old} → {new} (human)"
    # print: "state updated: {old} → {new}"
```

Usage : `python run_ticket.py T011 --set-state PLAN_APPROVED`

Cela donne un point d'entrée propre pour les reviews humaines sans éditer `state.json` à la main.

#### Étape 5 — `docs/ai/workflow.md` : clarification review humaine / agent

Ajouter une section dans le fichier existant :

```
## Modes de review

### Review agent (automatique)
Déclenchée par --auto avec --exec-cmd.
Le keyword (PLAN_APPROVED / PLAN_FIX_REQUIRED etc.) doit apparaître
seul sur sa propre ligne dans l'output du step review.

### Review humaine
Utiliser :
  python tools/agent_runner/run_ticket.py TXXX --set-state PLAN_APPROVED
Ne pas éditer state.json directement.
```

#### Étape 6 — Validation fix loop de bout en bout

Procédure de test reproductible à documenter dans `runs/T011/tests/test-report.md` :

1. Initialiser un ticket test en état `PLAN_FIX_REQUIRED`
2. Créer les artefacts requis (`plan.md`, `reviews/plan-review-*.md`, `fixes/plan-fix-*.md`)
3. Lancer `--auto` — vérifier :
   - `runtime.log` contient "review parsed from: runs/.../reviews/plan-review.md"
   - state transite vers `PLAN_REVIEW_NEEDED`
4. Répéter pour `IMPLEMENTATION_FIX_REQUIRED`

---

### Hors scope (confirmé)

- Pas de `--next` en mode `--auto` chaîné
- Pas de multi-agent, pas de remote runner
- Pas de merge/PR automatique
- Pas de refactor des prompts canoniques au-delà de la contrainte "plan complet"

---

### Note sur les plans canoniques (Étape 3 du ticket)

Ce point est purement prompt. La contrainte doit figurer dans le **template générique planner** (pas uniquement dans `T011-planner.md`). Le coder devra l'ajouter dans la section "Invariants" du prompt planner générique si un tel fichier existe, ou comme note dans `docs/ai/workflow.md` sous "Rôles / Planner" : *"Un retry planner doit produire un plan complet autonome — jamais un résumé ou delta du plan précédent."*

---

### Résumé des fichiers modifiés

| Fichier | Changement |
|---|---|
| `tools/agent_runner/run_step.py` | `--output-path` override pour `--exec-cmd` |
| `tools/agent_runner/run_ticket.py` | `_review_output_rel()`, `_call_run_step` context-aware, logging keyword, `--set-state` |
| `docs/ai/workflow.md` | Section review humaine/agent, contrainte plan canonique |

---

**PLAN_APPROVED** — ce plan est court, borné, et adresse les causes racines identifiées. Aucun nouveau composant, aucune dépendance externe.
