Le plan est produit. Voici le résumé :

---

## Plan T015 — Injection dynamique des review decision keywords

### Ce que j'ai vérifié dans le code

| Point | Localisation | Observation |
|---|---|---|
| `_determine_next_state()` | `run_ticket.py:289–304` | Déjà correct — cherche les `possible_next` de `TRANSITIONS` par regex `^KW$` multiline, aucun changement requis |
| `possible_next` | `run_ticket.py:525` | Décompacté depuis `TRANSITIONS[current_state]` troisième élément |
| Fix context injection | `run_ticket.py:530–540` | Uniquement pour `*_FIX_REQUIRED` — pas de collision possible avec les états review |
| `extra_context_file` dans `run_step.py` | `run_step.py:345–358` | Mécanisme existant suffisant — pas besoin de modifier `run_step.py` |
| Hardcoding dans `T014-reviewer.md` | ligne 44–49 | `IMPLEMENTATION_APPROVED`/`IMPLEMENTATION_FIX_REQUIRED` hardcodés — à corriger |

### Invariant clé

Les états review (`*_REVIEW_NEEDED`) et les états fix (`*_FIX_REQUIRED`) sont **mutuellement exclusifs** dans `TRANSITIONS` — pas de risque de collision entre les deux types d'injection de contexte.

### 5 étapes

1. **Ajouter `REVIEW_DECISION_KEYWORDS`** dans `run_ticket.py` après `TRANSITIONS` — dict explicite `état → {approve, fix}`
2. **Ajouter `_build_review_decision_context_file()`** — génère `runs/T015/reviews/review-decision-context-{state}.md` avec les deux keywords valides
3. **Modifier `auto_run()`** — quand `step == "review"`, construire et injecter ce fichier comme `extra_context_file`
4. **Mettre à jour `prompts/T014-reviewer.md`** — remplacer le hardcoding par une instruction générique
5. **Créer `tests/test_review_decision_keywords.py`** — cohérence avec `TRANSITIONS`, contenu injecté, absence d'injection hors review, parsing inchangé

### Fichiers touchés

- `tools/agent_runner/run_ticket.py` (modifié)
- `prompts/T014-reviewer.md` (modifié)
- `tests/test_review_decision_keywords.py` (créé)
