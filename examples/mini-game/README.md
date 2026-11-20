# Mini-jeu d'exemple

Ce projet montre le format cible de PyVenture :

- 4 pièces : chambre, couloir, grotte, salle au trésor ;
- 2 objets : lampe torche, clé en fer ;
- 2 interactions déclaratives ;
- français et anglais.

## Valider

```bash
python -m pyventure validate examples/mini-game/game.yaml
```

## Jouer

Le nouveau moteur arrive en Phase 1. En attendant, le jeu historique se lance avec :

```bash
python start.py
```

## Art

Les images référencées (`rooms/bedroom.png`, etc.) ne sont pas fournies : le moteur affichera des placeholders tant qu'elles n'existent pas. Voir [`art/README.md`](art/README.md).
