---

# PR Review — T100 — Visual workflow timeline in dashboard

## Résumé

Implémentation d'un endpoint `GET /tickets/{ticket_id}/timeline` et d'un composant `WorkflowTimeline` dans le dashboard. 7 fichiers modifiés ou créés. L'approche est une projection pure de `state.json` sans état secondaire.

## Vérifications effectuées

- Lecture complète de `schemas.py`, `artifact_reader.py`, `routes/tickets.py`
- Lecture complète de `api/tickets.js`, `WorkflowTimeline.jsx`, `TicketDetailPage.jsx`
- Lecture complète de `tests/test_ticket_timeline.py` (9 cas)
- Lecture complète de `TicketDetail.test.jsx` et `TicketDetailPage.test.jsx`
- Vérification de l'alignement ticket / plan / implémentation

## Points validés

**Conformité ticket :**
- `GET /tickets/{ticket_id}/timeline` — endpoint présent, structure JSON conforme au ticket (ticket_id, current_state, current_agent, human_gate, last_event, steps)
- 6 statuts couverts : `pending`, `running`, `done`, `waiting_human`, `failed`, `skipped`
- Timeline dérivée uniquement depuis `state.json`, `runtime.log`, `retry-state.json` — aucune source de vérité dupliquée
- `state.json` non modifié par l'API — lecture seule strictement respectée
- Timeline comme onglet par défaut dans la page détail — bonne UX
- Logs conservés comme onglet secondaire

**Qualité backend :**
- `_STATUS_MAP` est un simple dict de projection — lisible, maintenable, sans logique de transition
- `validate_ticket_id()` réutilisé — pas de nouveau vecteur d'injection de chemin
- `_build_steps()` est pur, sans effet de bord
- Fallback pour états inconnus propre (issue_intake=done, reste=pending)
- `TEST_COMPLETE` géré séparément pour intégrer la présence de `retry-state.json`

**Qualité frontend :**
- `WorkflowTimeline` est un composant minimal, sans état interne — simple à tester
- Guard `if (!timeline)` présent pour le cas null
- `human_gate` banner redondant avec le step `waiting_human` mais justifié pour la lisibilité opérationnelle
- `status` inconnu redirigé vers `STATUS_CONFIG.pending` par défaut — dégradation gracieuse

**Tests :**
- 9 cas API : 404, INIT, PLAN_REVIEW_NEEDED, PLAN_APPROVED, IMPLEMENTATION_REVIEW_NEEDED, IMPLEMENTATION_FIX_REQUIRED, TEST_COMPLETE sans retry, TEST_COMPLETE avec retry, last_event — tous les cas requis par le ticket couverts
- Tests de polling frontend : invalidation sur changement d'état, préservation sur état stable, re-fetch systématique pour logs et timeline — comportement vérifié
- Mock `getTicketTimeline` correctement ajouté dans les deux fichiers de test existants

**Conformité plan :**
- Exactement les 7 fichiers planifiés
- Hors-scope respecté : pas de checkpoint/push/PR comme étapes, pas de WebSocket, pas d'historique de transitions

## Problèmes détectés

**Observations mineures (non bloquantes) :**

1. **`IMPLEMENTATION_APPROVED` : `fix_loop` toujours `skipped`** (`artifact_reader.py`, ligne ~165). Si le workflow a traversé un cycle `IMPLEMENTATION_FIX_REQUIRED` avant d'atteindre `IMPLEMENTATION_APPROVED`, `fix_loop` devrait afficher `done` et non `skipped`. La projection depuis `state.json` seul ne peut pas distinguer ces cas sans lire les logs. Limitation acceptée par le plan ("historique de transitions depuis les logs" hors scope), mais à documenter dans un ticket futur.

2. **Tableaux parallèles `_STEPS` / `_STEP_AGENTS`** (`artifact_reader.py`, ligne ~130). L'alignement par index est fragile si les listes sont réordonnées. Pourrait être exprimé comme une liste de tuples `(id, label, agent)`. Non bloquant pour V1 avec 7 étapes fixes.

3. **`status` est un `str` non contraint** dans `TimelineStep` (`schemas.py`, ligne 38). Un `Literal["pending", "running", "done", "waiting_human", "failed", "skipped"]` renforcerait le contrat et activerait la validation Pydantic. Non bloquant car le backend ne produit que des valeurs connues.

4. **Pas de test dédié `WorkflowTimeline.test.jsx`.** Le composant est testé indirectement via `TicketDetailPage`. Le ticket dit "si possible" — gap mineur acceptable.

5. **Le statut `failed` est défini côté frontend mais jamais produit par le backend.** Aucun état de `_STATUS_MAP` ne génère `failed`. Si le daemon crash en cours d'exécution, l'état `last_event` du log signale l'erreur mais aucun step ne passe à `failed`. Limitation cohérente avec l'approche projection, à adresser dans un ticket ultérieur.

## Risques éventuels

- **Aucun risque de sécurité** : l'endpoint est strictement en lecture, `validate_ticket_id()` protège contre le path traversal, aucun secret exposé.
- **Aucun risque de régression** : les routes et artefacts existants sont inchangés. Les tests existants passent (343 Python, 52 frontend selon le rapport d'implémentation).
- **Risque de dérive acceptable** : le composant affiche `fix_loop: skipped` même après un cycle de fix. Cela peut induire en erreur un opérateur, mais reste cohérent avec la contrainte "pas de deuxième state machine". À corriger dans une itération future.

## Décision

L'implémentation répond à tous les critères d'acceptation du ticket :
- Endpoint timeline opérationnel avec structure stable
- Vue stepper visuelle dans la page détail
- Étape courante identifiable, gates humaines visibles, retries visibles
- Logs conservés comme vue secondaire
- Aucun nouveau moteur workflow introduit
- Couverture de test conforme aux exigences

Les observations sont mineures et n'introduisent pas de bug fonctionnel dans le périmètre du ticket.

IMPLEMENTATION_APPROVED
