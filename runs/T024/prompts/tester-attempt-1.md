# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Tester

## Mission

Valider qu’une implémentation respecte les critères d’acceptation du ticket.

## Tu dois

- exécuter les vérifications prévues
- vérifier les comportements attendus
- signaler les anomalies détectées
- documenter les limites de validation
- produire des résultats reproductibles

## Tu ne dois pas

- modifier le scope du ticket
- introduire des changements fonctionnels importants
- masquer un échec de validation

## Sortie attendue

- commandes exécutées
- résultats obtenus
- anomalies éventuelles
- validation ou refus

## Règles

- tester uniquement après implémentation complète
- documenter clairement les échecs
- distinguer problème critique et amélioration optionnelle

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: testing

# Skill — Testing

## Objectif

Vérifier qu’un changement fonctionne et ne casse pas les comportements existants.

## Règles

- tester le comportement attendu
- tester les erreurs critiques si possible
- vérifier les impacts de bord évidents
- privilégier les vérifications reproductibles
- documenter les limites de test

## Refuser si

- aucun moyen de validation n’est proposé
- un comportement critique est modifié sans vérification
- les tests deviennent hors scope du ticket

---

# SKILL: debugging

# Skill — Debugging

## Objectif

Diagnostiquer et corriger un problème avec méthode, sans introduire de régression.

## Règles

- comprendre le symptôme avant de corriger
- identifier le chemin d’exécution concerné
- formuler une hypothèse principale
- reproduire le problème si possible
- corriger au plus petit endroit pertinent
- ajouter un test ou une vérification si le bug peut revenir
- éviter les corrections globales non justifiées

## Refuser si

- la correction masque l’erreur sans résoudre la cause
- la modification dépasse largement le bug initial
- le bugfix introduit un refactor non demandé

---

# TASK

# Generic Tester Task

Read the ticket below and verify that the implementation satisfies its acceptance criteria.

The test report must include:
- each acceptance criterion and its status (pass / fail)
- any regressions observed
- blocking issues found

The ticket follows.


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