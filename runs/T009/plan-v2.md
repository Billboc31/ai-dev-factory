Le plan v2 est écrit dans `runs/T009/plan.md`. Voici ce qui a changé par rapport à v1 :

---

**Clarification 1 — Exclusion des `context-*.md`**
`_collect_fix_artifacts()` filtre explicitement tout fichier dont le nom commence par `context-` avant la sélection par mtime. Le filtre est défensif : les patterns `plan-fix-*.md` / `implementation-fix-*.md` les excluent déjà structurellement, mais la règle est documentée et appliquée en code.

**Clarification 2 — Sélection des reviews**
Règle verrouillée par état :
- `PLAN_FIX_REQUIRED` → glob `reviews/plan-review*.md`, dernier par mtime
- `IMPLEMENTATION_FIX_REQUIRED` → glob `reviews/implementation-review*.md`, dernier par mtime

Cette règle couvre à la fois les noms stables (`plan-review.md`) et versionnés (`implementation-review-v4.md`) observés dans T008, sans imposer de changement de convention au reviewer.

**Clarification 3 — Output précédent**
Chemins fixes hard-codés par état :
- `PLAN_FIX_REQUIRED` → `runs/TXXX/plan.md`
- `IMPLEMENTATION_FIX_REQUIRED` → `runs/TXXX/implementation-output.md`

Ces chemins sont exactement ceux de `DEFAULT_OUTPUTS["planner"]` et `DEFAULT_OUTPUTS["coder"]` dans `run_step.py` — pas de magic string isolée.

PLAN_APPROVED
