"""Fixtures partagées des tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyventure.core.loader import load_project
from pyventure.core.model import GameProject

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "mini-game" / "game.yaml"


@pytest.fixture(scope="session")
def example_path() -> Path:
    return EXAMPLE


@pytest.fixture
def project() -> GameProject:
    return load_project(EXAMPLE)
