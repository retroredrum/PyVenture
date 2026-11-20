"""Le contenu historique converti reste jouable et valide."""

from __future__ import annotations

from pathlib import Path

from pyventure.core.engine import Engine
from pyventure.core.loader import load_project

LEGACY = Path(__file__).resolve().parents[2] / "examples" / "legacy-game" / "game.yaml"


def test_legacy_example_loads_and_validates() -> None:
    project = load_project(LEGACY)
    assert project.meta.id == "legacy-house"
    assert project.meta.default_language == "en"
    assert project.meta.start_room == "room-7"
    assert "room-11" in project.rooms


def test_legacy_statue_opens_the_staircase() -> None:
    project = load_project(LEGACY)
    engine = Engine(project)
    state = engine.new_state()
    assert state.room == "room-7"

    result = engine.execute("push statue", state)
    assert "staircase" in result.text()

    engine.execute("d", state)
    assert state.room == "room-9"


def test_legacy_flashlight_is_needed_in_the_cave() -> None:
    project = load_project(LEGACY)
    engine = Engine(project)
    state = engine.new_state()
    # Sans la lampe, la commande échoue proprement.
    engine.execute("push statue", state)
    engine.execute("d", state)
    result = engine.execute("use flashlight", state)
    assert "can't do that" in result.text().lower()
