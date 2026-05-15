La review est écrite dans `runs/T103/reviews/implementation-review.md`. Voici le résumé :

---

**Points validés (in-scope, corrects):**
- Bug 1 ✅ — push désormais inconditionnellement après commit rc=0/rc=1
- Bug 2 ✅ — branch guard dans `launch_ticket()` avec skip sécurisé
- Bug 3 ✅ — `_CODE_SCOPE_PREFIXES` déjà complet, pas de changement nécessaire
- Bug 4 ✅ — `git rm -r --cached apps/dashboard/node_modules/`, `.issue-intake.json` reste tracké
- Checkpoint avant `PLAN_REVIEW_NEEDED` ✅
- `_sync_ticket_branch` (ff-only) ✅

**3 bloquants identifiés :**

1. **Board feature hors-scope** — `board_service.py`, `BoardPage.jsx`, schemas, route `/board`, `getBoardData`. Le plan dit "2 fichiers modifiés" ; 6 fichiers sur 3 couches ont été ajoutés sans justification dans le ticket ou le plan.

2. **`_count_active_tickets` + `--max-active-tickets` hors-scope** — nouveau throttling non demandé, avec refactorisation silencieuse de `poll_github_issues` (1 issue par cycle au lieu de tous).

3. **`_sync_main_before_intake()` non planifié** — fait un `git checkout main` qui peut bloquer le daemon indéfiniment sur `main` sans mécanisme de retour vers la branche ticket.

**Décision : `IMPLEMENTATION_FIX_REQUIRED`**
