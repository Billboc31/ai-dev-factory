Le plan est écrit dans `runs/T033/plan.md`. Voici un résumé des points clés :

**5 étapes bornées :**

1. **Intake bootstrap** — `run_issue_intake.py` : ajouter `commit_bootstrap()` qui stage uniquement `runs/TXXX/ticket.md` (jamais `git add .`), et un flag `--push` optionnel.

2. **Propagation daemon/intake** — `run_daemon.py` : passer `--push` à `call_issue_intake()`, et après intake+index, appeler `run_ticket.py TXXX --commit --include-code` pour commiter `runs/.issue-intake.json` via le système canonique.

3. **Pré-vol dirty tree** — `run_daemon.py` : avant chaque `launch_ticket()`, classer les fichiers dirty en `clean / workflow_artifacts / unknown_files` → checkpoint auto ou abort sécurisé selon le cas.

4. **Gitignore** — Supprimer les 4 lignes dupliquées (14-17) ; toutes les entrées requises sont déjà présentes (lignes 7-11).

5. **Tests** — Nouveau `test_intake_checkpoint.py` + extension de `test_daemon_checkpoint.py`.

**Aucune modification** de `run_ticket.py`, `run_step.py`, ou des agents. Le système canonique de commit existant est réutilisé tel quel.

PLAN_APPROVED

Note:
Le bootstrap checkpoint doit garantir que les artefacts workflow persistants (`state.json`, `runs/.issue-intake.json`) sont commités avant toute exécution auto suivante du daemon.
