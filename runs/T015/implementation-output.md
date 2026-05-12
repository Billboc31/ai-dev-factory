Everything looks correct. Here's a summary of what was implemented:

---

## Résumé des changements

### Fichiers modifiés

**`tools/agent_runner/run_ticket.py`**
- Ajout de `REVIEW_DECISION_KEYWORDS` (lignes 55–64) : dict explicite `état → {approve, fix}`, cohérent avec `TRANSITIONS`
- Ajout de `_build_review_decision_context_file()` (ligne 429) : génère `runs/TXXX/reviews/review-decision-context-{STATE}.md` avec les deux keywords valides pour l'état courant
- Modification de `auto_run()` (lignes 568–570) : injection du contexte review uniquement quand `step == "review"` et `current_state in REVIEW_DECISION_KEYWORDS`

**`prompts/T014-reviewer.md`**
- Remplacement des keywords hardcodés (`IMPLEMENTATION_APPROVED` / `IMPLEMENTATION_FIX_REQUIRED`) par une instruction générique demandant au reviewer d'utiliser les keywords injectés par le runtime

**`tests/test_review_decision_keywords.py`** (nouveau)
- 19 tests couvrant : cohérence avec `TRANSITIONS`, contenu des fichiers générés, isolation entre états, absence d'injection hors review, parsing `_determine_next_state()` inchangé

### Vérifications

- `_determine_next_state()` : inchangé — continue à parser les `possible_next` de `TRANSITIONS`
- Fix contexts (PLAN_FIX_REQUIRED, IMPLEMENTATION_FIX_REQUIRED) : mutuellement exclusifs avec les états review — aucune collision possible
- Étapes non-review (planner, coder, tester) : aucun contexte review injecté
- 25/25 tests passent
