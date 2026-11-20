# Contribuer à PyVenture

Merci de vouloir aider ! Ce projet est un moteur d'aventure texte avec illustrations pixel art et éditeur de contenu.

## Avant de commencer

1. Lire le [workflow de développement](docs/06-workflow-dev.md).
2. Parcourir la [roadmap](docs/03-roadmap.md) pour voir les priorités.
3. Ouvrir une issue ou commenter une tâche avant de gros changements.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,gui]"
pre-commit install
```

## Vérifications avant une PR

```bash
ruff check .
ruff format --check .
pytest
python -m pyventure validate examples/mini-game/game.yaml
```

## Règles

- Code et identifiants en anglais ; documentation en français ; textes du jeu localisés.
- Une fonctionnalité = une branche = une PR.
- Commits au format [Conventional Commits](https://www.conventionalcommits.org/).
- Tests obligatoires pour le moteur, le parseur et les règles.
- Ne pas casser le mode terminal.
- Mettre à jour la documentation et la roadmap si le comportement change.

## Signaler un bug

Indiquer :

- la commande ou l'action qui pose problème ;
- le comportement attendu et le comportement observé ;
- la version de Python et le système ;
- si possible, un extrait de projet YAML minimal qui reproduit le bug.

## Proposer une fonctionnalité

Décrire :

- le besoin de jeu ou d'édition ;
- le comportement souhaité ;
- les alternatives envisagées ;
- l'impact sur le format de données ou la compatibilité.

## Licence

Le projet est distribué sous **licence MIT** (voir [`LICENSE`](LICENSE)). En contribuant, vous acceptez que votre contribution soit publiée sous cette licence.
