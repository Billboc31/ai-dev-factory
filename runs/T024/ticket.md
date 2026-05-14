# T024 — Daemon GitHub issue polling

## Contexte

Le workflow dispose maintenant de trois briques séparées :

```text
run_daemon.py        = orchestration locale des runs existants
run_issue_intake.py  = transformation GitHub Issue → run local
run_ticket.py        = moteur workflow canonique
```

Actuellement :

- le daemon scanne uniquement `runs/*/state.json`
- `run_issue_intake.py` doit être lancé manuellement
- une issue GitHub ne démarre pas encore automatiquement un run local

Architecture cible :

```text
GitHub Issue ai-ready
→ daemon détecte
→ run_issue_intake.py crée run + branche + ticket.md + state.json
→ daemon orchestre run_ticket.py --auto
```

## Objectif

Étendre le daemon local pour détecter les issues GitHub prêtes à être traitées et lancer l’intake correspondant.

Le daemon ne doit pas parser ou transformer lui-même les issues : il doit appeler `run_issue_intake.py`.

## Inclus

- ajouter une option daemon pour activer le polling GitHub issues
- rechercher les issues avec un label explicite, par exemple `ai-ready`
- éviter de réingérer une issue déjà traitée
- appeler `run_issue_intake.py` avec le numéro d’issue, le ticket id et le branch slug
- logguer clairement les issues détectées, ignorées et ingérées
- préserver le scan existant des runs locaux
- ajouter des tests ciblés

## Comportement attendu

Exemple d’usage :

```bash
python tools/agent_runner/run_daemon.py \
  --exec-cmd "claude --dangerously-skip-permissions" \
  --poll-issues \
  --issue-label ai-ready
```

Le daemon :

1. scanne les issues prêtes
2. crée les runs locaux manquants via `run_issue_intake.py`
3. continue à scanner les `runs/*/state.json`
4. lance les étapes auto-runnable
5. s’arrête aux gates humaines

## Stratégie anti-doublon

Le daemon doit éviter de traiter deux fois la même issue.

Approches acceptables :

- détecter un `runs/TXXX/ticket.md` contenant l’issue number
- stocker un petit index local dans `runs/.issue-intake.json`
- se baser sur une convention de ticket id explicite

Le plan doit choisir l’approche la plus simple et bornée.

## Contraintes

- `run_ticket.py` reste le moteur workflow canonique
- `run_issue_intake.py` reste l’adapter issue → run
- le daemon orchestre mais ne duplique pas la logique d’intake
- aucun merge automatique
- aucune PR automatique
- aucun commentaire GitHub automatique dans ce ticket

## Hors scope

- création automatique de PR
- slash commands GitHub
- modification des labels GitHub
- fermeture automatique d’issue
- risk classifier
- UI web
- merge automatique
- multi-worker distribué

## Critères d’acceptation

- le daemon peut détecter une issue prête
- le daemon appelle `run_issue_intake.py`
- un run local est créé pour l’issue
- une issue déjà traitée n’est pas réingérée
- les runs locaux existants continuent d’être orchestrés
- les logs daemon sont explicites
- le comportement peut être testé sans appeler réellement GitHub

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tests/
README.md
```
