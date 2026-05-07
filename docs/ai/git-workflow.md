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

Le runner local `tools/agent_runner/run_ticket.py` expose trois commandes Git :

### Créer ou switcher vers la branche ticket

```bash
python tools/agent_runner/run_ticket.py TXXX --branch --branch-slug <slug>
```

- Si la branche existe déjà : `git checkout <name>` (pas d'écrasement).
- Si la branche n'existe pas : `git checkout -b <name>`.

### Commiter les artefacts du ticket

```bash
python tools/agent_runner/run_ticket.py TXXX --commit
python tools/agent_runner/run_ticket.py TXXX --commit --commit-message "T007: fix checkout_branch"
```

- Seul le répertoire `runs/TXXX/` est stagé automatiquement.
- Les autres fichiers modifiés (code source, docs) doivent être stagés manuellement avant d'appeler `--commit`.

### Pusher la branche

```bash
python tools/agent_runner/run_ticket.py TXXX --push --branch-slug <slug>
```

- Exécute `git push -u origin ticket/TXXX-<slug>`.
- Le push est toujours explicite : aucune commande de push automatique n'est déclenchée par le runner.

## Invariants

- Pas de merge automatique.
- Pas d'ouverture automatique de PR.
- Pas de review distante automatique.
- Le push est toujours une action humaine ou une commande explicite.
- La branche est créée depuis `main` ; elle reste vivante jusqu'au merge de la PR.

## Workflow type

```
1. git checkout main && git pull
2. python run_ticket.py TXXX --branch --branch-slug <slug>
3. <travail sur le ticket>
4. git add <fichiers modifiés hors runs/>
5. python run_ticket.py TXXX --commit
6. python run_ticket.py TXXX --push --branch-slug <slug>
7. Ouvrir la PR manuellement sur GitHub
```

## Liens

- [`pr-lifecycle.md`](./pr-lifecycle.md) — conventions PR et arborescence `runs/TXXX/`
- [`workflow.md`](./workflow.md) — lifecycle métier complet
