# T018 — Runtime capability and failure detection

## Contexte

Les tickets T014 à T017 ont renforcé le workflow engine :

- validation planner assouplie
- review decision keywords dynamiques
- runtime prompt snapshots persistés
- checkpoints Git workflow-aware

Pendant ces tickets, plusieurs problèmes runtime ont été observés :

- Claude lancé sans permission d’écriture produisait seulement un diff au lieu de modifier les fichiers
- le process LLM pouvait échouer avec un exit code non nul
- le quota provider pouvait bloquer l’exécution
- un step pouvait écrire un output mais ne produire aucun changement réel attendu
- le workflow devait être repris plus tard sans corruption d’état

Le comportement actuel est déjà sain sur un point important : si le process retourne un exit code non nul, `run_ticket.py` garde l’état inchangé.

Mais le moteur ne qualifie pas encore clairement le type d’échec.

Principe voulu :

```text
Le workflow engine doit détecter et rendre explicites les failures runtime.
```

Cela permet de distinguer :

- quota exceeded
- permission/write mode absent
- provider failure
- timeout ou crash
- output vide
- no filesystem changes when code changes are expected

## Objectif

Ajouter une détection claire des capacités et échecs runtime autour des steps LLM.

Le runner doit :

- logguer explicitement le type probable d’échec
- conserver l’état inchangé en cas d’échec
- rendre le diagnostic visible dans `runtime.log`
- éventuellement écrire un artefact dédié dans `runs/TXXX/`
- aider l’utilisateur à reprendre correctement le workflow

## Inclus

### 1. Classification minimale des échecs runtime

Ajouter une fonction de classification, par exemple :

```python
classify_runtime_failure(return_code, stdout, stderr) -> str
```

Catégories possibles :

```text
quota_exceeded
permission_denied
write_permission_missing
provider_error
empty_output
process_failed
unknown
```

La liste exacte peut être ajustée dans le plan.

### 2. Détection permission/write mode

Détecter les sorties typiques où l’agent indique qu’il ne peut pas écrire les fichiers ou demande une autorisation.

Exemples observés :

```text
I need write permission
Please grant it
```

Le runner doit logguer clairement :

```text
runtime failure: write_permission_missing
```

### 3. Détection quota/provider failure

Détecter les messages de quota ou de limite provider lorsque présents dans stdout/stderr.

Le runner doit logguer clairement :

```text
runtime failure: quota_exceeded
```

### 4. Output vide ou anormal

Si un step retourne 0 mais produit un output vide ou quasi vide, le runner doit logguer un warning.

Pour les steps coder, si aucun changement de fichiers n’est détecté alors que le step est censé modifier le repo, le runner peut logguer un warning non bloquant ou bloquant selon le plan.

### 5. Artefact de diagnostic runtime

Si pertinent, écrire un artefact comme :

```text
runs/TXXX/runtime-failures/<step>-attempt-N.md
```

ou ajouter une entrée claire dans `runtime.log`.

Le choix doit rester simple et borné.

### 6. Aucun changement d’état sur failure

Conserver l’invariant actuel :

```text
step failed → state unchanged
```

### 7. Tests

Ajouter des tests ciblés pour :

- quota exceeded
- write permission missing
- provider/process failure
- empty output warning
- état inchangé sur failure
- logs runtime explicites

## Hors scope

- provider abstraction complète
- multi-provider routing
- retry automatique temporisé
- daemon permanent
- backoff scheduler
- UI dashboard
- risk classifier
- replay engine complet
- merge automatique
- PR automatique

## Critères d’acceptation

### Failure explicite

Un échec LLM ne se limite plus à :

```text
exit code 1
```

Le runtime log contient un diagnostic lisible.

### State safe

L’état workflow reste inchangé en cas d’échec runtime.

### Permission issue détectée

Un output demandant une permission d’écriture est détecté comme problème runtime explicite.

### Quota/provider issue détecté

Un message de quota ou provider failure est classifié si reconnaissable.

### Compatibilité workflow

Aucune régression sur :

- `--auto`
- reviews
- fix loops
- prompt snapshots
- commit/push checkpoints

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
tools/agent_runner/run_step.py
tests/
README.md
```
