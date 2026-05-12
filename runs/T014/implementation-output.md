6/6 tests passent. Voici le résumé des changements appliqués :

**Fichiers modifiés**

- `tools/agent_runner/run_step.py` — deux corrections :
  - `_REQUIRED_SECTION_GROUPS` : ajout de `"## contexte technique"` (groupe `contexte`), ajout de `"## acceptance criteria"` (groupe `critères d'acceptation`), suppression du doublon `"## étapes d'implémentation"` (groupe `inclus`)
  - `validate_planner_output()` : stripping des blocs de code (fences et inline) avant vérification des phrases interdites

**Fichiers créés**

- `tests/test_validate_planner_output.py` — 6 tests unitaires couvrant : plan canonique valide, synonymes valides, plan trop court, section manquante, phrase interdite réelle, phrase interdite dans un bloc de code (ne doit pas rejeter)

**Résultat** : `pytest tests/` — 6 passed in 0.01s. Le passage planner → `PLAN_REVIEW_NEEDED` est validé.
