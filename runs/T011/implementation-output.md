All 5 changes are in place and syntax-clean. Here's a summary of what was implemented:

---

### Changements T011

**`tools/agent_runner/run_step.py`**
- Nouveau paramètre `--output-path` : permet à l'appelant de surcharger le fichier de sortie lors d'un `--exec-cmd`.

**`tools/agent_runner/run_ticket.py`**
- `_review_output_rel(current_state)` : dérive `reviews/plan-review.md` ou `reviews/implementation-review.md` selon l'état — corrige le bug critique où `_collect_fix_artifacts` ne trouvait jamais rien.
- `_call_run_step` : prend maintenant `current_state`, passe `--output-path` à `run_step.py`, et retourne `(rc, content, output_path)`.
- `auto_run` : log explicite `review parsed from:`, `keyword detected:`, `no keyword found in` pour chaque step non-déterministe.
- `set_workflow_state(ticket_id, new_state)` + `--set-state` CLI : point d'entrée propre pour les reviews humaines (valide l'état, log `(human)` dans `runtime.log`, pas d'édition directe de `state.json`).

**`docs/ai/workflow.md`**
- Section **Modes de review** : review agent vs review humaine, avec commande exacte.
- Invariant planner : "Un retry planner doit produire un plan complet autonome — jamais un résumé ou delta du plan précédent."
