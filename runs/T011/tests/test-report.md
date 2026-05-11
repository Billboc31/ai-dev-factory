---

## Résultat

**TEST_APPROVED**

Tous les 7 scénarios passent :

| # | Scénario | Résultat |
|---|---|---|
| S1 | `PLAN_FIX_REQUIRED` détecté correctement | PASS |
| S2 | `PLAN_APPROVED` détecté correctement | PASS |
| S3 | review filename cohérent (plan-review.md / implementation-review.md + glob matching) | PASS |
| S4 | retry planner fonctionne (`_collect_fix_artifacts` + `_build_fix_context_file`) | PASS |
| S5 | retry coder fonctionne (même chaîne pour impl) | PASS |
| S6 | logs runtime lisibles, format ISO, causalité traçable | PASS |
| S7 | invariant "plan retry complet" présent dans workflow.md § Planner | PASS |

Trois edge cases bonus validés : keyword inline ignoré, keyword avec espaces ignoré, double-keyword → warning + premier résultat déterministe.

Le rapport est écrit dans `runs/T011/tests/test-report.md`.
