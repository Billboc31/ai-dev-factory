I have a complete picture. Writing the review now.

---

# PR Review — T102 (attempt 2)

## Contexte de la review

La première review (`IMPLEMENTATION_FIX_REQUIRED`) avait identifié un problème bloquant : `_sync_main_before_intake()` était appelée inconditionnellement au début de `poll_github_issues()`, avant tout filtrage des issues et des candidats. Le coder a soumis un fix. Cette review vérifie que le fix est correct et que l'implémentation globale est approuvable.

---

## Fix bloquant — vérification

**Fichier** : `tools/agent_runner/run_daemon.py`, fonction `poll_github_issues()` (lignes 806–859)

Le fix a été appliqué correctement. L'ordre de `poll_github_issues()` est désormais :

```python
1. fetch_ready_issues()          → return si aucune issue
2. load_issue_index()            → filtrer les déjà ingérées
3. candidates filtration         → return si tous déjà ingérés
4. _count_active_tickets()       → return si active >= max_active_tickets (log skipped-for-capacity)
5. log queued pour issues non sélectionnées
6. _sync_main_before_intake()    → abort si git sync échoue   ← position corrigée
7. call_issue_intake()
```

La synchronisation Git ne se déclenche plus qu'au moment effectif de l'intake, après validation de la capacité et de l'existence de candidats. L'implémentation respecte exactement la spécification du ticket : *"checkout main, pull origin main, then run issue intake"*.

---

## Vérification des 8 critères d'acceptation

| Critère | Fichier | Statut |
|---|---|---|
| Synchronise `main` avant intake | `run_daemon.py:849-851` | ✅ |
| Ne lance pas toutes les issues `ai-ready` simultanément | `run_daemon.py:839` (candidates[0]) | ✅ |
| Limite de capacité `max_active_tickets=1` | `run_daemon.py:712-724, 834` + CLI flag | ✅ |
| Issues non lancées visibles comme queued/skipped | `run_daemon.py:835-836, 841` + board | ✅ |
| API board expose les colonnes principales | `routes/daemon.py:39-41`, `board_service.py` | ✅ |
| Dashboard affiche une vue board globale | `BoardPage.jsx`, `App.jsx` | ✅ |
| Logs expliquent pourquoi une issue est/n'est pas lancée | `run_daemon.py:815-851` | ✅ |
| Aucun `git add .` | Tous les fichiers | ✅ |

---

## Vérification des contraintes

- **Pas de duplication `run_ticket.py`** : aucune state machine dupliquée — `run_daemon.py` délègue entièrement à `run_ticket.py --auto`. ✅
- **Pas de DB dédiée** : la queue est une projection de `runs/*/state.json`. ✅
- **Git source de vérité** : l'issue index est un fichier JSON versionné (`runs/.issue-intake.json`). ✅
- **Pas de `git add .`** : vérifié dans tous les fichiers modifiés. ✅
- **Pas d'auto-merge** : PR créée sans merge automatique. ✅
- **Dashboard client de la Control API** : `BoardPage.jsx` appelle uniquement `GET /daemon/board`. ✅
- **Pas de checkout/pull si working tree inconnu** : `_sync_main_before_intake()` ligne 688-689 aborte si `unknown_files`. ✅

---

## Points validés

- **Logique de classification board** : priorité stricte dans `board_service.py` — `done → pr_ready → waiting_human → blocked → running → queued → backlog`. Aucune ambiguïté entre colonnes.
- **`_count_active_tickets()`** : compte les tickets non archivés et non fermés (conservateur, correct pour V1). Couvre tous les états actifs incluant les gates humaines.
- **Gestion des échecs `gh`** : failure silencieuse dans `board_service._fetch_ai_ready_issues()` → backlog vide, pas d'erreur 500. Comportement documenté et correct.
- **Atomicité** : écriture de `.issue-intake.json` et `retry-state.json` via fichier `.tmp` + rename atomique. Correct.
- **Lock guard** : `_acquire_lock()` protège contre les lancements concurrents de `run_ticket.py` par ticket. Correct.
- **BoardPage.jsx** : poll 10s via `usePolling`, lien vers `/tickets/:id` pour les items avec `ticket_id`, gestion du loading/error. Correct.

---

## Observations mineures héritées (non bloquantes, V2)

### [MINEUR] `BoardItem.title` non peuplé pour les tickets ingérés

`board_service.py:83-88` — les cartes tickets n'ont pas de titre, seulement `state` ou `branch` comme sous-titre. Fonctionnel. Le titre est dans `runs/{ticket_id}/ticket.md` mais pas dans `state.json`. À adresser dans un ticket dédié.

### [MINEUR] `repo` non transmis au service board

`routes/daemon.py:41` — `board_service.get_board(_root(request))` n'utilise pas de repo explicite. `gh issue list` fonctionne via le contexte Git implicite. Suffisant en V1, non extensible en multi-repo. À documenter si nécessaire.

---

## Décision

Le problème bloquant de la première review a été corrigé correctement et sans dérive de scope. L'implémentation satisfait tous les critères d'acceptation, respecte toutes les contraintes, et est conforme au plan. Qualité du code correcte, fonctions lisibles, erreurs gérées explicitement.

IMPLEMENTATION_APPROVED
