# T016 — Restore runtime prompt snapshots

## Contexte

T010 devait persister les runtime prompts complets utilisés par les agents.

Les logs runtime montrent que la composition fonctionne :

- compose: global-context
- compose: role
- compose: skill
- compose: task
- compose: extra-context

Mais le dossier :

```text
runs/TXXX/prompts/
```

reste vide.

Le prompt runtime est donc composé mais jamais persisté.

Cela casse :

- la rejouabilité
- le debug
- l’auditabilité
- la reproductibilité
- l’observabilité runtime

Principe voulu :

```text
Chaque exécution agentique doit être replayable et reviewable.
```

## Objectif

Persister automatiquement les runtime prompts complets dans :

```text
runs/TXXX/prompts/
```

avec :

- le step
- le numéro de tentative
- le prompt runtime complet exact
- les extra contexts injectés

## Inclus

### 1. Ajouter un mécanisme de snapshot

Créer une fonction explicite pour écrire les prompts runtime.

Exemple :

```python
_write_prompt_snapshot(...)
```

### 2. Naming déterministe

Format attendu :

```text
runs/T015/prompts/planner-attempt-1.md
runs/T015/prompts/review-attempt-2.md
runs/T015/prompts/coder-attempt-3.md
```

### 3. Snapshot avant exécution

Le snapshot doit être écrit avant :

```python
execute_external_command(...)
```

### 4. Inclure les extra contexts

Les snapshots doivent inclure :

- fix contexts
- review decision contexts
- retry contexts
- tout extra context injecté

### 5. Runtime logs

Ajouter un log explicite.

Exemple :

```text
snapshot: runtime-prompt=runs/T015/prompts/review-attempt-2.md
```

### 6. Tests

Ajouter des tests ciblés vérifiant :

- création du snapshot
- nommage correct
- incrément des tentatives
- présence des extra contexts
- contenu identique au prompt runtime

## Hors scope

- replay engine complet
- dashboard runtime
- UI web
- remote runners
- PR automation
- merge automatique

## Critères d’acceptation

Après exécution d’un step :

```text
runs/TXXX/prompts/
```

contient les prompts runtime exacts.

Les extra contexts injectés apparaissent dans le snapshot.

Aucune régression sur :

- fix loops
- review loops
- transitions workflow
- parsing review
- logs runtime

Le système reste :

- explicite
- déterministe
- reviewable
- Git-native
