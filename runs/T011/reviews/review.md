Voici la review technique complète de T011.

---

## Review — T011 : Workflow Engine Stabilization

### 1. Keywords détectés correctement

`_determine_next_state` (run_ticket.py:219) :

```python
found = [kw for kw in possible_next if re.search(rf"^{re.escape(kw)}$", output, re.MULTILINE)]
```

Regex `^KEYWORD$` avec `re.MULTILINE` — le keyword doit être seul sur sa propre ligne. Conforme à la spec workflow.md. ✓

Cas multi-keyword : warning explicite sur stderr + `found[0]` — comportement déterministe. ✓

### 2. Logs runtime explicites

Trois logs présents dans `auto_run` (run_ticket.py:474-487) :

| Situation | Log |
|---|---|
| Review step lancé | `auto-run: review parsed from: {output_path}` |
| Keyword trouvé | `auto-run: keyword detected: {next_state}` |
| Aucun keyword | `auto-run: no keyword found in {output_path}` |

Les logs pour les steps déterministes sont absents — correct, pas de parsing donc pas de log superflu. ✓

### 3. Review naming cohérent

`_review_output_rel` (run_ticket.py:230-235) :
- `PLAN_REVIEW_NEEDED` → `reviews/plan-review.md`
- `IMPLEMENTATION_REVIEW_NEEDED` → `reviews/implementation-review.md`

`_collect_fix_artifacts` cherche `reviews/plan-review*.md` — le glob `plan-review*.md` avec `*` zéro-char matche `plan-review.md`. Chaîne cohérente end-to-end. ✓

### 4. Fix loops réellement fonctionnelles

La chaîne complète :

1. `auto_run` état `PLAN_REVIEW_NEEDED` → `_call_run_step(..., current_state="PLAN_REVIEW_NEEDED")`
2. `_call_run_step` appelle `_review_output_rel` → `output_rel = "reviews/plan-review.md"`
3. `run_step.py --output-path runs/T011/reviews/plan-review.md` écrit l'artefact
4. Transition vers `PLAN_FIX_REQUIRED`
5. `auto_run` état `PLAN_FIX_REQUIRED` → `_collect_fix_artifacts` → glob `reviews/plan-review*.md` → trouve `plan-review.md` ✓

Fix loop réparable. ✓

Note sur le chemin : `output_path = Path("runs") / ticket_id / output_rel` est relatif, `ensure_safe_relative_path` dans run_step.py accepte des chemins relatifs. ✓

### 5. Séparation review humaine / review agent

`set_workflow_state` (run_ticket.py:352-366) :
- Validation `new_state not in VALID_STATES` avant toute écriture ✓
- `_log_runtime(..., f"set-state: {old} → {new} (human)")` — entrée explicite et distincte ✓
- Écriture atomique via `.tmp` + rename ✓
- Pas d'édition directe de `state.json` requise ✓

`workflow.md` : section "Modes de review" ajoutée avec commande exacte. ✓

### 6. Plans retry complets

Invariant ajouté dans `workflow.md` sous "Rôles / Planner" :

> Un retry planner doit produire un plan complet autonome — jamais un résumé ou delta du plan précédent.

✓

### Points à surveiller (non bloquants)

**DEFAULT_OUTPUTS dupliqués** : `run_step.py:38-45` vs `run_ticket.py:49-54` — divergence connue (`memory-updater`, `memory-apply` absents dans run_ticket.py). Le commentaire L.48 `# Must stay in sync` documente le risque mais ne le résout pas. Dette connue, non dans scope T011. Acceptable.

**Test-report** : l'étape 6 du plan (procédure de test reproductible) est à la charge du tester, pas du coder. Attendu au step suivant.

---

IMPLEMENTATION_APPROVED
