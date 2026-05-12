I have a complete picture. Let me now write the structured review.

---

## Review T015 — Injection dynamique des review decision keywords

### Périmètre vérifié

| Fichier | Statut |
|---|---|
| `tools/agent_runner/run_ticket.py` | Modifié — conforme |
| `tools/agent_runner/run_step.py` | Non modifié — conforme |
| `prompts/T014-reviewer.md` | Modifié — conforme |
| `prompts/T015-reviewer.md` | Créé — conforme |
| `tests/test_review_decision_keywords.py` | Créé — 19/19 passent |

---

### Vérifications ticket

#### Keywords dynamiques

Le runtime injecte correctement :
- `PLAN_APPROVED` / `PLAN_FIX_REQUIRED` quand `current_state == PLAN_REVIEW_NEEDED`
- `IMPLEMENTATION_APPROVED` / `IMPLEMENTATION_FIX_REQUIRED` quand `current_state == IMPLEMENTATION_REVIEW_NEEDED`

Le fichier `runs/T015/reviews/review-decision-context-IMPLEMENTATION_REVIEW_NEEDED.md` est présent et correctement formé. Le runtime.log confirme l'injection à `09:17:16Z`.

#### Compatibilité `TRANSITIONS`

`REVIEW_DECISION_KEYWORDS` est cohérent avec `TRANSITIONS` — la cohérence est garantie par `test_review_keywords_cover_all_review_states`, `test_review_keywords_approve_is_valid_next` et `test_review_keywords_fix_is_valid_next`. ✅

#### Compatibilité `_determine_next_state()`

Inchangé — parse toujours les `possible_next` issus de `TRANSITIONS`, pas les keywords injectés. Les tests couvrent explicitement les cas `wrong_keyword_returns_none` et `no_keyword_returns_none`. ✅

#### Compatibilité fix loops

L'invariant d'exclusivité mutuelle entre états `*_REVIEW_NEEDED` et `*_FIX_REQUIRED` est correct dans `TRANSITIONS`. Les deux blocs d'injection (`run_ticket.py:556-566` et `:568-570`) ne peuvent pas se déclencher simultanément — aucune collision possible. ✅

#### Aucun impact sur les étapes non-review

La garde `step == "review" and current_state in REVIEW_DECISION_KEYWORDS` garantit l'isolation. `test_non_review_states_not_in_review_decision_keywords` le vérifie. ✅

#### Prompts reviewer génériques

`T014-reviewer.md:44-45` remplace les keywords hardcodés par une instruction générique. `T015-reviewer.md` ne hardcode pas de keywords. ✅

#### Logs runtime

L'injection est loggée à `auto-run: review decision context: context_file=...` et à `compose: extra-context=...`. ✅

#### Changements bornés

Aucune modification en dehors du périmètre plan : `run_ticket.py`, `T014-reviewer.md`, `T015-reviewer.md`, `test_review_decision_keywords.py`. `run_step.py` n'est pas touché. ✅

---

### Observations

**Observation mineure — label "Contexte de retry" pour les keywords review**

`run_step.py:354` injecte tout extra context sous le label `## Contexte de retry injecté par run_ticket.py`. Pour les fix contexts, ce label est sémantiquement correct. Pour les review decision keywords, il est trompeur (ce n'est pas un retry).

Fonctionnellement sans impact — le reviewer voit le contenu correct. Hors scope T015 (nécessiterait de modifier `run_step.py` pour distinguer les types de contexte). À adresser dans un ticket futur si jugé utile.

**Observation mineure — un seul test de nommage de fichier**

`test_context_file_path_contains_state_name` couvre uniquement `PLAN_REVIEW_NEEDED`. Le cas `IMPLEMENTATION_REVIEW_NEEDED` est implicitement couvert par les tests de contenu. Non bloquant.

---

### Conclusion

L'implémentation est correcte, bornée et sûre. Les 5 étapes du plan ont été exécutées fidèlement. Le système reste déterministe, explicite et Git-native. Aucun comportement dangereux introduit. Aucune régression détectée.

IMPLEMENTATION_APPROVED
