Le plan est écrit dans `runs/T027/plan.md`. Voici le résumé :

**Deux changements dans `tools/agent_runner/run_ticket.py` :**

1. **`_determine_next_state`** (ligne 373) — élargir le regex de `^{kw}$` vers trois patterns alternatifs : ligne exacte, `**KEYWORD**` gras Markdown, et formes labellisées `Verdict : KEYWORD` / `Décision : KEYWORD` / `Decision: KEYWORD`. La guardrail (seuls les keywords de `possible_next` sont acceptés) reste intacte.

2. **Nouvelle fonction `_write_fix_artifact`** — appelée dans `auto_run` après `save_state` quand `next_state.endswith("_FIX_REQUIRED")`. Scanne les fichiers `fixes/plan-fix-*.md` ou `fixes/implementation-fix-*.md` existants, incrémente N correctement, écrit le fichier avec la décision, le chemin de la review source et le contenu complet. Logs explicites sur stdout et runtime.log.

**Tests** : ajouts dans `tests/test_review_decision_keywords.py` (7+ cas de parsing) et nouveau fichier `tests/test_fix_artifact.py` (8 cas couvrant création, incrément, contenu, et absence sur `*_APPROVED`).

**Hors scope documenté** : les transitions humaines (`--request-*-fix`) ne bénéficient pas de l'auto-création — l'utilisateur continue à créer le fichier manuellement dans ce cas.
