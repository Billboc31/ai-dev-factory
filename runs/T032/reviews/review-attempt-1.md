# PR Review — T032

## Résumé

L'implémentation corrige la construction de commande dans `run_daemon.py` pour garantir que `--exec-cmd` est transmis comme une seule string complète à `run_ticket.py`. Tous les critères d'acceptation du ticket sont couverts.

## Vérifications effectuées

- Lecture complète de `tools/agent_runner/run_daemon.py` (fonctions `build_run_ticket_command`, `launch_ticket`, `parse_args`, `main`)
- Lecture de `tests/test_run_daemon.py` (section `build_run_ticket_command`, lignes 302–329)
- Exécution des tests : `pytest tests/test_run_daemon.py -k build_run_ticket` → **4 passed**
- Vérification de l'argument parsing (`--exec-cmd` déclaré `required=True`, sans `nargs`)
- Vérification de l'absence de modification directe de `state.json` dans le daemon
- Vérification de l'absence de duplication de la state machine

## Points validés

**Contrat CLI canonique respecté**

`build_run_ticket_command` (ligne 444) construit :
```python
cmd = [sys.executable, str(RUN_TICKET), ticket_id, "--auto"]
if exec_cmd:
    cmd.extend(["--exec-cmd", exec_cmd])
```
`exec_cmd` reste une string unique — pas de split, pas de `shlex.split`.

**Logging sans ambiguïté**

Ligne 486 : `_log(f"Running ticket command: {shlex.join(cmd)}")` — conforme à la recommandation du ticket.

**Argument parsing correct**

Ligne 662 : `parser.add_argument("--exec-cmd", required=True, ...)` — argparse conserve la valeur telle quelle, sans nargs, donc `"claude --dangerously-skip-permissions"` arrive intact dans `args.exec_cmd`.

**Fonction pure extraite et testée**

`build_run_ticket_command` est une fonction pure sans effets de bord, testée par 4 tests unitaires ciblés :
- `test_build_run_ticket_command_exec_cmd_not_split` : vérifie explicitement que `"claude --dangerously-skip-permissions"` est un seul élément et que `"--dangerously-skip-permissions"` n'est pas un argument séparé.

**Aucune modification de `state.json` depuis le daemon**

Aucun accès en écriture à `state.json` détecté dans `run_daemon.py`.

**Aucune duplication de logique workflow**

Le daemon délègue entièrement à `run_ticket.py --auto`, sans réimplémenter la state machine.

## Problèmes détectés

**Mineurs uniquement — non bloquants**

1. **Incohérence de type sur `exec_cmd` entre `launch_ticket` et `build_run_ticket_command`**

   - `launch_ticket` déclare `exec_cmd: str` (non nullable)
   - `build_run_ticket_command` déclare `exec_cmd: str | None`
   
   À l'usage, `launch_ticket` est toujours appelé avec `args.exec_cmd` qui est `required=True`, donc jamais `None`. La signature de `build_run_ticket_command` est plus permissive que nécessaire mais pas incorrecte. Pas de risque fonctionnel.

2. **Inconsistance de format dans le log dry-run**

   Ligne 477 : `_log(f"dry-run: would launch {ticket_id} --auto --exec-cmd {exec_cmd!r}")` utilise `!r` tandis que le log réel (ligne 486) utilise `shlex.join`. La représentation en dry-run est donc moins canonique. Pas de risque fonctionnel mais légère confusion de lisibilité.

## Risques éventuels

Aucun risque bloquant identifié. Le changement est borné au périmètre du ticket. Les comportements existants (retry, lock, checkpoint) ne sont pas altérés.

## Décision

- APPROVED

## Actions demandées

Aucune correction obligatoire.

Suggestions optionnelles (post-merge) :
- Aligner la signature de `build_run_ticket_command` sur `exec_cmd: str` si None n'est pas un cas voulu
- Harmoniser le log dry-run pour utiliser également `shlex.join`

IMPLEMENTATION_APPROVED
