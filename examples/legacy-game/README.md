# Contenu historique converti

Ce dossier est **généré** par [`tools/convert_legacy.py`](../../tools/convert_legacy.py) à partir de `content.py`.

La conversion est « meilleur effort » :

- les identifiants numériques deviennent des slugs `room-<n>` ;
- les noms de pièces sont génériques (`Room 3`) ;
- les descriptions d'objets sont provisoires (`A key.`) ;
- les textes sont en anglais, langue du contenu d'origine.

## Régénérer

```bash
python3 tools/convert_legacy.py
```

## Jouer

```bash
python3 -m pyventure play -p examples/legacy-game/game.yaml
```

## Étape suivante

Retravailler ce fichier (idéalement dans l'éditeur, en Phase 3) pour :

- renommer les pièces et objets avec des identifiants parlants ;
- écrire de vraies descriptions ;
- ajouter le français ;
- fournir les illustrations.
