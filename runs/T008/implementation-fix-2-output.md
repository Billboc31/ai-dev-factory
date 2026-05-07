Les règles `.gitignore` fonctionnent. Voici le récapitulatif des 3 corrections appliquées :

**Défaut 1 — BLOQUANT (`.gitignore` créé)**
`runs/*/state.json` et `runs/*/runtime.log` sont maintenant ignorés par git. Le gate "working tree clean" ne les verra plus en `??` après `--auto-init` ou le premier `--auto`.

**Défaut 2 — MOYEN (`_call_run_step` ligne 247-253)**
Si `rc == 0` mais que le fichier de sortie attendu est absent, un warning est émis sur stderr et une entrée est écrite dans `runtime.log`. L'absence n'est plus silencieuse.

**Défaut 3 — MINEUR (README session example)**
Un `--commit` est ajouté après chaque `--auto` dans l'exemple, reflétant que les artefacts produits (trackés par git) doivent être commités avant l'invocation suivante.
