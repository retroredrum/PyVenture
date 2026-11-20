PYTHON ?= python3
PROJECT ?= examples/mini-game/game.yaml

.PHONY: help install install-dev play play-gui legacy test test-gui test-editor lint format validate editor convert-legacy golden clean

help:
	@echo "PyVenture — commandes disponibles"
	@echo ""
	@echo "  make install       Installe le moteur (sans interface graphique)"
	@echo "  make install-dev   Installe le moteur, pygame et les outils de dev"
	@echo "  make play          Lance le nouveau moteur (Phase 1)"
	@echo "  make play-gui      Lance la fenêtre pygame (Phase 2)"
	@echo "  make legacy        Lance le moteur historique"
	@echo "  make test          Lance pytest"
	@echo "  make test-gui      Lance les tests pygame en headless"
	@echo "  make test-editor   Lance les tests de l'éditeur (xvfb-run)"
	@echo "  make lint          Vérifie le style avec Ruff"
	@echo "  make format        Formate le code avec Ruff"
	@echo "  make validate      Valide le projet d'exemple"
	@echo "  make convert-legacy Convertit content.py vers examples/legacy-game"
	@echo "  make golden        Régénère les transcripts de référence"
	@echo "  make editor        Lance l'éditeur (Phase 3)"
	@echo "  make clean         Nettoie les artefacts"

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev,gui]"

play:
	$(PYTHON) -m pyventure play

play-gui:
	$(PYTHON) -m pyventure play --gui

legacy:
	$(PYTHON) start.py

test:
	$(PYTHON) -m pytest

test-gui:
	SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy $(PYTHON) -m pytest -m gui

test-editor:
	xvfb-run -a $(PYTHON) -m pytest -m editor

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

validate:
	$(PYTHON) -m pyventure validate $(PROJECT)

convert-legacy:
	$(PYTHON) tools/convert_legacy.py

golden:
	UPDATE_GOLDEN=1 $(PYTHON) -m pytest tests/golden -q

editor:
	$(PYTHON) -m pyventure editor

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
