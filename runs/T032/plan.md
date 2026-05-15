Plan écrit dans `runs/T032/plan.md`. Voici un résumé :

**Constat clé** : la construction de commande ligne 465 de `run_daemon.py` est déjà correcte — `exec_cmd` est bien un seul élément de liste. Le ticket demande de rendre ce contrat explicite et testé.

**3 changements à faire :**

1. **`tools/agent_runner/run_daemon.py`**
   - Ajouter `import shlex`
   - Extraire `build_run_ticket_command(ticket_id, exec_cmd, ...)` comme fonction pure testable
   - Ajouter `_log(f"Running ticket command: {shlex.join(cmd)}")` avant `subprocess.run()`

2. **`tests/test_run_daemon.py`**
   - 4 tests pour `build_run_ticket_command` : contract de liste, non-split d'`exec_cmd`, structure positionnelle, flags optionnels

Aucun autre fichier n'est touché. Risque de régression quasiment nul — refactor structurel pur.
