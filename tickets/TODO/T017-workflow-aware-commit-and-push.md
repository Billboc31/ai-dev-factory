# T017 — Workflow-aware commit and push checkpoints

## Contexte

T013 a ajouté des primitives Git au runner : ensure branch, commit checkpoint, push contrôlé.

Depuis T014, T015 et T016, le workflow réel a révélé une limite importante :

```text
python tools/agent_runner/run_ticket.py TXXX --commit
```

ne committe actuellement que les artefacts `runs/TXXX/`.

Or les agents modifient maintenant réellement :

- `tools/`
- `tests/`
- `prompts/`
- `tickets/`
- `docs/`
- `ai/`

Résultat : après chaque étape coder/tester, il faut encore faire manuellement :

```bash
git status
git add tools/ tests/ prompts/ runs/TXXX/
git commit -m "..."
git push
```

Cela casse la fluidité du workflow et crée un décalage entre :

```text
artefacts workflow
```

et :

```text
changements code réels
```

Principe voulu :

```text
Le checkpoint Git doit représenter l’état réel du ticket : code + tests + prompts + artefacts runtime.
```

Git reste la source de vérité. Le système doit rester explicite, borné et sans merge automatique.

## Objectif

Améliorer les primitives Git du runner pour gérer proprement les checkpoints complets du ticket.

Le runner doit permettre de committer et pousser :

- les artefacts `runs/TXXX/`
- les fichiers code modifiés par le ticket
- les tests ajoutés/modifiés
- les prompts/tickets/docs liés

sans faire de `git add .` aveugle et sans introduire d’autonomie dangereuse.

## Inclus

### 1. Commit workflow-aware

Améliorer ou compléter `--commit` pour pouvoir inclure les changements de code liés au ticket.

Exemples possibles :

```bash
python tools/agent_runner/run_ticket.py T017 --commit --include-code
```

ou :

```bash
python tools/agent_runner/run_ticket.py T017 --checkpoint
```

Le comportement final peut être choisi par le plan, mais il doit rester explicite.

### 2. Scope de staging sûr

Le runner doit éviter :

```bash
git add .
```

Le staging doit être limité à des chemins autorisés, par exemple :

```text
runs/TXXX/
tools/
tests/
prompts/
tickets/
docs/
ai/
```

Le runner doit afficher ou logger les fichiers inclus.

### 3. Guardrails Git

Le commit doit refuser ou avertir clairement si :

- la branche courante ne correspond pas au ticket
- `state.json` indique une autre branche
- aucun fichier n’est à committer
- des fichiers hors scope sont modifiés
- le repo est dans un état Git incohérent

### 4. Messages de commit cohérents

Le message par défaut doit rester stable et lié au ticket.

Exemple :

```text
T017: checkpoint [IMPLEMENTATION_REVIEW_NEEDED]
```

ou :

```text
T017: workflow-aware checkpoint [IMPLEMENTATION_REVIEW_NEEDED]
```

Un message personnalisé doit rester possible.

### 5. Push contrôlé

Améliorer ou valider `--push` pour :

- pousser uniquement la branche ticket attendue
- refuser si la branche courante ne correspond pas à `state.json`
- refuser si le working tree est sale sauf option explicite
- logger l’action dans `runtime.log`

### 6. Option pratique commit + push

Ajouter si pertinent une option explicite :

```bash
--checkpoint-push
```

ou permettre :

```bash
--commit --include-code --push
```

Le comportement doit rester explicite et jamais automatique par défaut.

### 7. Tests

Ajouter ou mettre à jour des tests pour couvrir :

- staging limité aux chemins autorisés
- refus des fichiers hors scope
- commit avec artefacts seuls
- commit avec code + artefacts
- refus mauvaise branche
- push uniquement branche ticket
- absence de `git add .`

## Hors scope

- merge automatique
- création automatique de PR
- auto-merge
- GitHub API obligatoire
- remote runners
- daemon permanent
- risk classifier
- replay engine complet

## Critères d’acceptation

### Commit complet explicite

Une commande explicite permet de committer en une seule fois :

- code modifié
- tests modifiés
- prompts/tickets/docs liés
- artefacts `runs/TXXX/`

### Staging sûr

Le runner ne fait jamais de `git add .` aveugle.

### Hors scope protégé

Les fichiers hors scope ne sont pas commités silencieusement.

### Push sûr

Le push ne concerne que la branche ticket attendue.

### Logs runtime

Les actions Git sont loggées dans :

```text
runs/TXXX/runtime.log
```

### Compatibilité workflow

Aucune régression sur :

- `--auto`
- `--auto-init`
- `--ensure-branch`
- fix loops
- review loops
- snapshots runtime prompts

### Philosophie projet respectée

Le système reste :

- explicite
- local-first
- reviewable
- Git-native
- sans merge automatique
- sans PR automatique
- sans agent caché

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_ticket.py
tests/
README.md
```
