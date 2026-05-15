# T025 — T025 — Daemon retry and cooldown policy

**Source**: GitHub Issue #19

## Description

# T025 — Daemon retry and cooldown policy

## Contexte

Le daemon peut maintenant :

- détecter des issues GitHub `ai-ready`
- créer des runs locaux
- lancer le workflow planner/coder/reviewer/tester
- orchestrer les étapes auto-runnable

Mais les erreurs runtime provider ne sont pas encore gérées intelligemment.

Exemple réel :

```text
Claude quota exceeded
→ daemon retry immédiat
→ boucle infinie
```

Le système doit maintenant supporter des politiques de retry et cooldown robustes.

## Objectif

Ajouter une politique de retry/cooldown pour les failures runtime détectées par T018.

Le daemon doit :

- classifier les failures
- appliquer un cooldown adapté
- éviter les retries infinis
- conserver les runs dans un état cohérent
- logguer clairement les décisions de retry/pause

## Inclus

- stockage local des retry states daemon
- cooldown provider quota
- retry exponentiel provider_error
- retry limité process_failed
- arrêt explicite sur write_permission_missing
- logs explicites
- tests ciblés

## Exemples attendus

```text
quota_exceeded
→ cooldown 1h
```

```text
provider_error
→ retry exponentiel
```

```text
write_permission_missing
→ stop + human attention
```

## Contraintes

- `run_ticket.py` reste le moteur workflow
- la classification runtime existante (T018) reste la source de vérité
- le daemon applique seulement des policies de retry
- aucun retry infini
- aucun état workflow cassé

## Hors scope

- model routing
- multi-provider balancing
- UI web
- notifications push
- PR automation
- distributed workers

## Critères d’acceptation

- un quota exceeded ne boucle pas infiniment
- les retries sont limités et traçables
- les cooldowns sont persistés
- les logs daemon sont explicites
- les tests couvrent les policies principales
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tests/
README.md
```
