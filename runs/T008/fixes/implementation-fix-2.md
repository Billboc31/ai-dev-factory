# Implementation Fix Request — T008

Status: IMPLEMENTATION_FIX_REQUIRED

## Défaut bloquant — gate working tree auto-bloquant après --auto-init

Après `--auto-init`, `runs/TXXX/state.json` est créé mais non versionné. Sans `.gitignore`, `git status --porcelain` le voit en `??`, donc le premier `--auto` échoue sur le gate "working tree clean".

Même problème pour `runs/TXXX/runtime.log`.

## Correction obligatoire

Créer un `.gitignore` projet à la racine avec au minimum :

```gitignore
runs/*/state.json
runs/*/runtime.log
```

Cela respecte l’intention du plan :
- `state.json` est source de vérité runtime locale
- `runtime.log` est log runtime local
- ces fichiers ne sont pas versionnés directement
- le gate working tree clean reste strict pour le reste

## Correction recommandée 2

Dans `_call_run_step`, si `rc == 0` mais que le fichier de sortie attendu n’existe pas :
- afficher un warning stderr
- écrire une entrée dans `runtime.log`

Ne pas masquer silencieusement l’absence du fichier.

## Correction README

Dans l’exemple de session README, indiquer qu’il faut commit les artefacts entre deux invocations `--auto`, par exemple :

```bash
# After each step, commit artifacts before the next --auto
python tools/agent_runner/run_ticket.py T009 --commit
```

## Contraintes

Ne pas affaiblir le gate working tree clean en ignorant tous les untracked.
Ne pas changer l’architecture générale :
- `state.json` reste source de vérité
- `workflow-status.md` reste journal append-only
- `--auto` reste une seule étape par invocation
- pas de PR auto
- pas de merge auto
