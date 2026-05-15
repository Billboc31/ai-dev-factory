# T032 — T032 — Fix daemon command contract with run_ticket.py

**Source**: GitHub Issue #34

## Description

# T032 — Fix daemon command contract with run_ticket.py

## Contexte

Après T031, le daemon n’a pas encore pu être utilisé correctement.

Le problème suspecté est que `run_daemon.py` n’appelle pas exactement `run_ticket.py` avec le contrat CLI canonique.

La commande canonique attendue est :

```bash
python tools/agent_runner/run_ticket.py TXXX \
  --auto \
  --exec-cmd "claude --dangerously-skip-permissions"
```

Le daemon doit donc transmettre `--exec-cmd` comme une seule chaîne complète, et non splitter la commande Claude en plusieurs arguments.

## Objectif

Corriger la construction de commande dans `run_daemon.py` pour garantir que le daemon exécute exactement le workflow canonique.

## Règles importantes

- `run_daemon.py` ne doit pas modifier directement `state.json`
- `run_daemon.py` ne doit pas réimplémenter la state machine
- `run_ticket.py` reste le moteur workflow canonique
- ne jamais utiliser `git add .`
- ne pas modifier le comportement de checkpoint/PR hors nécessité
- ne pas contourner les gates humaines

## Commande attendue

Pour un ticket `T032`, le daemon doit construire l’équivalent de :

```python
[
    sys.executable,
    "tools/agent_runner/run_ticket.py",
    "T032",
    "--auto",
    "--exec-cmd",
    "claude --dangerously-skip-permissions",
]
```

Et non :

```python
[
    sys.executable,
    "tools/agent_runner/run_ticket.py",
    "T032",
    "--auto",
    "--exec-cmd",
    "claude",
    "--dangerously-skip-permissions",
]
```

## Travail demandé

### 1. Corriger `run_daemon.py`

Identifier la fonction qui lance `run_ticket.py`.

S’assurer que :

```python
cmd = [
    sys.executable,
    "tools/agent_runner/run_ticket.py",
    ticket_id,
    "--auto",
]

if exec_cmd:
    cmd.extend(["--exec-cmd", exec_cmd])
```

`exec_cmd` doit rester une string complète.

### 2. Logger la commande exécutée

Ajouter un log clair avant exécution :

```text
Running ticket command: python tools/agent_runner/run_ticket.py T032 --auto --exec-cmd "claude --dangerously-skip-permissions"
```

Le log doit aider à diagnostiquer les erreurs sans être ambigu.

Attention : pour éviter les confusions, logger avec `shlex.join(cmd)` si disponible.

### 3. Vérifier l’argument parsing

Vérifier que `run_daemon.py` accepte bien :

```bash
--exec-cmd "claude --dangerously-skip-permissions"
```

et que cette valeur est passée telle quelle à `run_ticket.py`.

### 4. Ajouter ou adapter les tests

Ajouter un test qui vérifie que la commande construite contient bien :

```python
"--exec-cmd",
"claude --dangerously-skip-permissions"
```

et pas :

```python
"--exec-cmd",
"claude",
"--dangerously-skip-permissions"
```

Si la construction de commande n’est pas facilement testable, extraire une petite fonction pure, par exemple :

```python
build_run_ticket_command(ticket_id: str, exec_cmd: str | None) -> list[str]
```

Puis tester cette fonction.

## Critères d’acceptation

- Le daemon lance `run_ticket.py` avec le ticket id en premier argument positionnel
- `--auto` est bien passé
- `--exec-cmd` est transmis comme une seule string complète
- la commande exacte exécutée est visible dans les logs
- les tests passent
- aucun changement direct de `state.json` depuis le daemon
- aucune duplication de logique workflow dans le daemon
