Le plan est écrit dans `runs/T023/plan.md`. Voici un résumé :

---

## Plan T023 — GitHub issue intake

**3 fichiers à toucher** : `run_issue_intake.py` (nouveau), `tests/test_run_issue_intake.py` (nouveau), `tools/agent_runner/README.md` (section intake). `run_ticket.py` n'est pas modifié.

**Séquence d'exécution du script** (ordre critique) :
1. Valider `--ticket-id` (pattern `T\d{3,}`)
2. Refuser si `state.json` existe déjà
3. Refuser si working tree sale
4. Fetch issue via `gh issue view --json title,body`
5. Créer la branche `ticket/TXXX-slug`
6. Écrire `ticket.md` + `state.json` (INIT) + `runtime.log`

Le script est **autonome** (pas d'import de `run_ticket.py`) — 8 petites fonctions internes seulement.

**10 cas de test** couvrant : happy path, invalid ticket-id, gh failure, state déjà existant, working tree sale, format ticket.md/state.json, détection repo auto vs `--repo` explicite.

**Risques principaux** : `gh` absent/non authentifié (message `gh auth login`), branche déjà existante (erreur explicite), demi-initialisation (loggué clairement).
