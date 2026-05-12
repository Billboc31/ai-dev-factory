# T020 — Local workflow daemon

## Contexte

Le workflow engine supporte maintenant :

- state machine
- retries
- reviews
- runtime snapshots
- runtime diagnostics
- workflow-aware commits/push
- normalized task source

Mais le workflow reste piloté manuellement via des commandes CLI répétitives.

Architecture cible :

```text
state.json = source de vérité
run_daemon.py = orchestrateur local
run_ticket.py = moteur d’exécution
```

Le daemon doit rester :

- explicite
- local-first
- contrôlable
- sans autonomie implicite dangereuse

---

## Objectif

Ajouter un daemon local simple capable de surveiller les tickets et de lancer automatiquement les étapes autorisées.

Le daemon ne doit jamais bypass une gate humaine.

---

## Inclus

### 1. Nouveau script daemon

Ajouter un script :

```text
tools/agent_runner/run_daemon.py
```

Le daemon :

- scanne `runs/*/state.json`
- détecte les états auto-runnable
- lance `run_ticket.py --auto`
- loggue explicitement ses actions

---

### 2. États auto-runnable

Supporter :

```text
INIT
PLAN_APPROVED
IMPLEMENTATION_REVIEW_NEEDED
IMPLEMENTATION_APPROVED
PLAN_FIX_REQUIRED
IMPLEMENTATION_FIX_REQUIRED
```

---

### 3. Gates humaines

Le daemon doit s’arrêter sur :

```text
PLAN_REVIEW_NEEDED
TEST_COMPLETE
DONE
```

Le daemon ne doit pas relancer automatiquement un état bloquant nécessitant une décision humaine.

---

### 4. Single-run protection

Empêcher deux exécutions concurrentes sur le même ticket.

Le mécanisme peut être :

```text
lock.json
PID file
in-memory lock
```

mais doit rester :

- simple
- local
- explicite
- déterministe

---

### 5. Logs runtime

Ajouter des logs explicites :

```text
[daemon] detected T020 state=PLAN_APPROVED
[daemon] launching coder
[daemon] skipping T020 state=PLAN_REVIEW_NEEDED
```

---

### 6. Boucle contrôlée

Le daemon fonctionne avec polling simple.

Exemple :

```bash
python tools/agent_runner/run_daemon.py --interval 5
```

---

### 7. Dry-run

Ajouter un mode dry-run.

Exemple :

```bash
python tools/agent_runner/run_daemon.py --dry-run
```

Le daemon doit logguer ce qu’il ferait sans lancer réellement les steps.

---

### 8. Compatibilité workflow

Préserver :

- `run_ticket.py`
- retries
- reviews
- snapshots
- diagnostics runtime
- workflow-aware commits/push

Le daemon doit utiliser les APIs/workflows existants autant que possible.

---

### 9. Tests

Ajouter des tests ciblés pour :

- détection états auto-runnable
- arrêt aux gates humaines
- single-run protection
- dry-run
- logs
- compatibilité workflow existant

---

## Hors scope

- GitHub API
- PR creation
- merge automatique
- daemon distribué
- multi-worker
- queue système
- websocket
- dashboard web
- risk classifier
- auto-review routing avancé
- orchestration multi-agent

---

## Critères d’acceptation

### Workflow automatique local

Le daemon peut lancer automatiquement des tickets locaux.

### Gates humaines respectées

Les états de review humaine restent bloquants.

### Aucun double run

Le même ticket ne peut pas être exécuté deux fois simultanément.

### Logs explicites

Les actions du daemon sont visibles dans les logs runtime.

### Compatibilité préservée

Le workflow actuel continue de fonctionner sans daemon.

### Philosophie projet respectée

Le système reste :

- explicite
- local-first
- reviewable
- Git-native
- sans merge automatique
- sans PR automatique
- sans agent caché

---

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tools/agent_runner/run_ticket.py
tests/
README.md
```