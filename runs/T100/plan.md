Le plan est écrit à `runs/T100/plan.md`. Voici le résumé :

---

## Plan T100 — Visual workflow timeline in dashboard

**7 étapes, 5 fichiers modifiés, 2 fichiers créés.**

### Ce qui est fait

**Backend (3 fichiers) :**
1. `schemas.py` — ajouter `TimelineStep` et `TimelineResponse` (Pydantic)
2. `artifact_reader.py` — ajouter `get_ticket_timeline()` qui dérive la timeline uniquement depuis `state.json` (champ `state`), la dernière ligne de `runtime.log`, et optionnellement `retry-state.json`
3. `routes/tickets.py` — ajouter `GET /tickets/{ticket_id}/timeline`

**Frontend (3 fichiers) :**
4. `api/tickets.js` — ajouter `getTicketTimeline(id)`
5. `components/WorkflowTimeline.jsx` — nouveau composant stepper vertical (done/running/waiting_human/pending/skipped avec Tailwind CSS)
6. `pages/TicketDetailPage.jsx` — ajouter le tab `timeline` avec rendu `<WorkflowTimeline>` au lieu d'un `<pre>`

**Tests :**
7. `tests/test_ticket_timeline.py` — 8 cas : INIT, PLAN_REVIEW_NEEDED, PLAN_APPROVED, IMPLEMENTATION_REVIEW_NEEDED, IMPLEMENTATION_FIX_REQUIRED, TEST_COMPLETE, 404, retry-state présent

### Logique clé

La timeline est une **projection pure** de `state.json` via une table de mapping. Pas de parsing de logs, pas de state machine dupliquée. 7 étapes fixes toujours affichées (`issue_intake` → `plan` → `plan_review` → `implementation` → `implementation_review` → `fix_loop` → `tests`), chacune avec statut déduit de l'état courant.

### Hors scope

Checkpoint/push/PR comme étapes, WebSocket temps réel, historique de transitions depuis les logs, modification d'artefacts.

PLAN_APPROVED

Note:
OK pour une V1 basée sur state.json avec étapes fixes. Les checkpoints/push/PR et l’historique fin des transitions restent hors scope de cette itération et devront faire l’objet d’un ticket ultérieur.