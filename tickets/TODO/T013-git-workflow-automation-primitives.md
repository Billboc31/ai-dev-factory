# T013 — Git workflow automation primitives

## Contexte

T008 a introduit une state machine stricte avec `state.json`.
T009 a ajouté les fix loops artifact-aware.
T010 a ajouté les snapshots de prompts runtime.
T011/T012 ont stabilisé le workflow engine, les reviews et la composition des prompts.

Le workflow fonctionne maintenant, mais il reste beaucoup de friction manuelle autour de Git :

- créer ou sélectionner la branche ticket
- vérifier la branche attendue
- commit les artefacts entre étapes
- push régulièrement
- gérer les working trees sales
- relancer le workflow après chaque checkpoint

Git est en train de devenir l’event log du système. Il faut donc ajouter des primitives Git fiables au runner.

## Objectif

Ajouter des primitives Git automatisées mais contrôlées pour réduire la friction du workflow.

Le runner doit aider à :

- préparer la branche ticket
- committer les checkpoints workflow
- pousser la branche
- tracer ces actions dans `runtime.log`

## Inclus

### 1. Ensure branch

Ajouter une commande ou option permettant de créer/switcher sur la branche attendue de façon sûre.

Exemple cible :

```bash
python tools/agent_runner/run_ticket.py T013 --ensure-branch --branch-slug git-workflow-automation-primitives
```

Règles :

- ne jamais écraser une branche existante
- refuser si le working tree est sale
- créer la branche si absente
- switcher dessus si elle existe
- logger l’action dans `runtime.log`

### 2. Commit checkpoint

Ajouter une primitive de commit contrôlé.

Objectif : committer les artefacts du ticket et les changements explicitement autorisés.

Règles :

- message par défaut basé sur ticket + état courant
- possibilité de message personnalisé
- refuser si rien à committer
- logger le commit dans `runtime.log`
- éviter `git add .` aveugle si possible

### 3. Push contrôlé

Ajouter une primitive de push sûre.

Règles :

- push uniquement la branche ticket attendue
- refuser si la branche courante ne correspond pas à `state.json`
- logger le push

### 4. Intégration avec `--auto`

Ne pas rendre `--auto` entièrement autonome.

Mais permettre une option explicite plus tard, par exemple :

```bash
--auto-commit
--auto-push
```

Pour T013, l’objectif principal est d’ajouter les primitives et leur documentation.

## Hors scope

- pas de création automatique de PR
- pas de merge automatique
- pas d’auto-commit implicite sans flag explicite
- pas de GitHub API obligatoire
- pas de remote runner

## Critères d’acceptation

- le runner peut créer/switcher une branche ticket sans commande Git manuelle
- le runner peut créer un commit checkpoint avec message stable
- le runner peut push la branche ticket attendue
- les actions Git sont loggées dans `runtime.log`
- les guards empêchent les actions sur mauvaise branche
- aucune PR ni merge automatique n’est introduit
