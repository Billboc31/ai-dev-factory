# T003 — Agent local minimal

## Contexte

T002 a défini le lifecycle PR IA et les artefacts `runs/TXXX/`.

Il faut maintenant préparer un premier agent local simple qui exécute les prompts déjà créés par ChatGPT.

## Objectif

Créer un exécuteur local minimal pour lire les prompts canoniques et écrire les sorties dans `runs/TXXX/`.

## Inclus

- structure `tools/agent_runner/`
- script CLI minimal
- lecture ticket id `TXXX`
- lecture étape (`planner`, `coder`, `review`, `tester`, `memory-updater`, `memory-apply`)
- résolution du prompt canonique sous `prompts/`
- création de l’arborescence `runs/TXXX/`
- écriture d’un artefact de sortie fourni par stdin
- README d’usage

## Exclus

- pas d’intégration LLM automatique
- pas de watcher permanent
- pas de merge automatique
- pas de génération de prompts

## Critères d’acceptation

- `tools/agent_runner/run_step.py` existe
- `tools/agent_runner/README.md` existe
- le script affiche un prompt canonique
- le script crée les dossiers `runs/TXXX/`
- le script écrit une sortie dans un artefact cible
- la documentation explique l’usage
