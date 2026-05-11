# Git Workflow — ai-dev-factory

## Principe

Un ticket = une branche = une PR.

Chaque ticket vit sur une branche dédiée jusqu'à son merge humain.

## Convention de branche

```
ticket/TXXX-<slug>
```

Exemples :
- `ticket/T007-git-ticket-branch-workflow`
- `ticket/T012-add-memory-updater`

Le slug est un résumé court en kebab-case du sujet du ticket.

## Commandes du runner

Le runner local `tools/agent_runner/run_ticket.py` expose trois commandes Git.

### Créer ou switcher vers la branche ticket

```bash
python tools/agent_runner/run_ticket.py TXXX --branch --branch-slug <slug>
# ou, de façon équivalente :
python tools/agent_runner/run_ticket.py TXXX --ensure-branch --branch-slug <slug>
```

- Refuse si le working tree est sale (commit ou stash avant).
- Si la branche existe déjà : `git checkout <name>` (pas d'écrasement).
- Si la branche n'existe pas : `git checkout -b <name>`.
- L'action est loggée dans `runs/TXXX/runtime.log`.

### Commiter les artefacts du ticket

```bash
python tools/agent_runner/run_ticket.py TXXX --commit
python tools/agent_runner/run_ticket.py TXXX --commit --commit-message "T007: fix checkout_branch"
```

- Vérifie qu'il y a des changements dans `runs/TXXX/` avant de stager.
- Message par défaut : `TXXX: checkpoint [<STATE>] — update workflow artifacts` (lu depuis `state.json`).
- Seul le répertoire `runs/TXXX/` est stagé automatiquement.
- Les autres fichiers modifiés (code source, docs) doivent être stagés manuellement avant d'appeler `--commit`.
- Retourne `rc=1` (non-bloquant) si rien à committer.
- Le SHA du commit et le message sont loggés dans `runtime.log`.

### Pusher la branche

```bash
python tools/agent_runner/run_ticket.py TXXX --push --branch-slug <slug>
```

- Vérifie que la branche courante correspond à `state.json["branch"]` avant de push.
- Si `state.json` est absent : warning non-bloquant, push avec le nom calculé depuis `--branch-slug`.
- Exécute `git push -u origin <branch>`.
- Le push est toujours explicite : aucune commande de push automatique n'est déclenchée par le runner sans flag.
- L'action est loggée dans `runtime.log`.

### Auto-commit et auto-push dans le mode `--auto`

```bash
python tools/agent_runner/run_ticket.py TXXX --auto --exec-cmd "..." --auto-commit
python tools/agent_runner/run_ticket.py TXXX --auto --exec-cmd "..." --auto-commit --auto-push
```

- `--auto-commit` : après chaque transition d'état réussie, déclenche un commit des artefacts `runs/TXXX/`.
- `--auto-push` : si le commit a réussi (rc=0), déclenche un push de la branche.
- Un échec du commit ou du push est un warning — l'état sauvegardé n'est pas modifié.
- `--auto-push` sans `--auto-commit` est silencieusement ignoré (pas de commit = pas de push).

## Invariants

- Pas de merge automatique.
- Pas d'ouverture automatique de PR.
- Pas de review distante automatique.
- Le push est toujours une action explicite (`--push` ou `--auto-push`).
- La branche est créée depuis `main` ; elle reste vivante jusqu'au merge de la PR.
- Le working tree doit être propre pour `--branch` / `--ensure-branch`.
- La branche est vérifiée contre `state.json` avant tout push.

## Workflow type

```
1. git checkout main && git pull          # étape manuelle — hors runner intentionnellement
2. python run_ticket.py TXXX --ensure-branch --branch-slug <slug>
3. <travail sur le ticket>
4. git add <fichiers modifiés hors runs/>
5. python run_ticket.py TXXX --commit
6. python run_ticket.py TXXX --push --branch-slug <slug>
7. Ouvrir la PR manuellement sur GitHub
```

L'étape 1 est intentionnellement manuelle : le runner n'automatise pas le retour sur `main` ni le pull, car cela interférerait avec un workflow déjà en cours.

## Logging runtime

Toutes les actions Git importantes sont loggées dans `runs/TXXX/runtime.log` :

| Action | Entrée log |
|---|---|
| `--ensure-branch` (refus) | `ensure-branch: refused — <raison>` |
| `--ensure-branch` (succès) | `ensure-branch: done branch=<name>` |
| `--commit` (refus) | `commit-checkpoint: refused — nothing to commit in runs/` |
| `--commit` (succès) | `commit-checkpoint: sha=<sha> message=<msg>` |
| `--push` (refus) | `push: refused — <raison>` |
| `--push` (succès) | `push: done branch=<name>` |
| `--auto-commit` déclenché | `auto-run: auto-commit triggered` |
| `--auto-push` déclenché | `auto-run: auto-push triggered` |

## Liens

- [`pr-lifecycle.md`](./pr-lifecycle.md) — conventions PR et arborescence `runs/TXXX/`
- [`workflow.md`](./workflow.md) — lifecycle métier complet
