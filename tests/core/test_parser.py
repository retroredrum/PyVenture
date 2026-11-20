"""Tests du parseur."""

from __future__ import annotations

import pytest
from pyventure.core.errors import ParseError
from pyventure.core.model import GameProject
from pyventure.core.parser import parse
from pyventure.core.state import GameState


def test_direction(project: GameProject) -> None:
    state = GameState.new(project)
    command = parse(project, state, "nord")
    assert command.verb == "go"
    assert command.direct == "n"


def test_verb_with_article_fr(project: GameProject) -> None:
    state = GameState.new(project)
    command = parse(project, state, "prendre la lampe")
    assert command.verb == "get"
    assert command.direct == "flashlight"


def test_examine_alias(project: GameProject) -> None:
    state = GameState.new(project)
    command = parse(project, state, "examiner la lampe")
    assert command.verb == "look"
    assert command.direct == "flashlight"


def test_english(project: GameProject) -> None:
    state = GameState.new(project, "en")
    command = parse(project, state, "take the flashlight")
    assert command.verb == "get"
    assert command.direct == "flashlight"


def test_go_with_verb(project: GameProject) -> None:
    state = GameState.new(project)
    command = parse(project, state, "aller nord")
    assert command.verb == "go"
    assert command.direct == "n"


def test_unknown_verb(project: GameProject) -> None:
    state = GameState.new(project)
    with pytest.raises(ParseError) as exc:
        parse(project, state, "danser")
    assert exc.value.key == "command.unknown_verb"


def test_empty_input(project: GameProject) -> None:
    state = GameState.new(project)
    with pytest.raises(ParseError) as exc:
        parse(project, state, "   ")
    assert exc.value.key == "parser.empty"


def test_go_where(project: GameProject) -> None:
    state = GameState.new(project)
    with pytest.raises(ParseError) as exc:
        parse(project, state, "aller")
    assert exc.value.key == "parser.go_where"


def test_object_not_in_scope(project: GameProject) -> None:
    state = GameState.new(project)
    # La clé est dans la salle au trésor, pas dans la chambre.
    command = parse(project, state, "prendre cle")
    assert command.verb == "get"
    assert command.direct is None
