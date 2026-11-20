"""Tests du moteur : déroulement d'une partie complète."""

from __future__ import annotations

from pyventure.core.engine import Engine
from pyventure.core.events import Style
from pyventure.core.model import GameProject


def test_start_shows_room(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()
    result = engine.start(state)
    text = result.text()
    assert "Chambre" in text
    assert "lampe torche" in text
    assert any(line.style is Style.ROOM_TITLE for line in result.lines)


def test_look_and_inventory(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()
    assert "Chambre" in engine.execute("regarder", state).text()
    assert "rien" in engine.execute("inventaire", state).text()


def test_get_object(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()
    result = engine.execute("prendre lampe", state)
    assert state.carries("flashlight")
    assert "lampe torche" in result.text()


def test_cannot_go_through_hidden_exit(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()
    engine.execute("nord", state)
    engine.execute("nord", state)
    assert state.room == "cave"
    result = engine.execute("est", state)
    assert state.room == "cave"
    assert result.text().strip() != ""


def test_full_playthrough(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()

    engine.execute("prendre lampe", state)
    engine.execute("nord", state)
    engine.execute("nord", state)
    assert state.room == "cave"

    result = engine.execute("utiliser lampe", state)
    assert state.flags["cave_lit"] is True
    assert state.room_variants["cave"] == "lit"
    assert state.object_state(project, "flashlight") == "on"
    assert "lampe" in result.text().lower()

    engine.execute("est", state)
    assert state.room == "vault"

    engine.execute("prendre cle", state)
    assert state.carries("key")

    result = engine.execute("utiliser cle", state)
    assert result.ended == "escaped"
    assert state.score(project) == 10
    assert "Évasion" in result.text()


def test_examine_reflects_state(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()
    engine.execute("prendre lampe", state)
    engine.execute("nord", state)
    engine.execute("nord", state)
    engine.execute("utiliser lampe", state)
    result = engine.execute("examiner lampe", state)
    assert "allumée" in result.text()


def test_english_messages(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state("en")
    assert "Bedroom" in engine.start(state).text()
    assert "You take flashlight" in engine.execute("take flashlight", state).text()


def test_once_interaction_does_not_repeat(project: GameProject) -> None:
    engine = Engine(project)
    state = engine.new_state()
    engine.execute("prendre lampe", state)
    engine.execute("nord", state)
    engine.execute("nord", state)
    engine.execute("utiliser lampe", state)
    again = engine.execute("utiliser lampe", state)
    assert "allume" not in again.text().lower()
