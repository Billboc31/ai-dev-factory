# Skill — Risk Classification

## Objectif

Classifier les tickets selon leur niveau de risque et le niveau de supervision requis.

## Niveaux

- AUTO_SAFE
- CHAT_REVIEW_REQUIRED
- HIGH_RISK

## Règles

AUTO_SAFE :
- changement local
- faible impact architecture
- faible risque sécurité
- faible risque workflow

CHAT_REVIEW_REQUIRED :
- changement architecture
- changement mémoire globale
- changement workflow IA
- refactor transversal

HIGH_RISK :
- sécurité sensible
- suppression importante
- migration lourde
- changement destructif
