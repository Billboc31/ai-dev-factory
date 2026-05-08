PLAN_FIX_REQUIRED

Le plan est globalement validé, mais il faut verrouiller trois conventions avant coder :

1. `_collect_fix_artifacts()` doit ignorer explicitement les fichiers `fixes/context-*.md` pour éviter l’auto-inclusion récursive des contextes générés.

2. La règle de sélection des reviews doit être stricte :
   - `PLAN_FIX_REQUIRED` utilise la dernière review pertinente de plan
   - `IMPLEMENTATION_FIX_REQUIRED` utilise la dernière review pertinente d’implémentation
   - documenter la convention exacte de nommage ou introduire un fichier stable `latest-review.md`.

3. La règle de sélection de l’output précédent doit être explicite :
   - `PLAN_FIX_REQUIRED` injecte `runs/TXXX/plan.md`
   - `IMPLEMENTATION_FIX_REQUIRED` injecte `runs/TXXX/implementation-output.md`

Le reste du plan est cohérent :
- `--extra-context-file` dans `run_step.py` est une bonne séparation de responsabilités
- `run_ticket.py` reste orchestrateur workflow
- invocation humaine préservée
- pas de boucle automatique
- artefacts injectés logués
