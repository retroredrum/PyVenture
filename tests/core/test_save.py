"""Tests de sauvegarde et de chargement."""

from __future__ import annotations

import pytest
from pyventure.core.engine import Engine
from pyventure.core.errors import SaveError
from pyventure.core.model import GameProject
from pyventure.core.save import load_state, save_state


def test_round_trip(project: GameProject, tmp_path) -> None:
    engine = Engine(project)
    state = engine.new_state()
    engine.execute("prendre lampe", state)
    engine.execute("nord", state)

    path = tmp_path / "save.json"
    save_state(project, state, path)
    assert path.is_file()

    restored = load_state(project, path)
    assert restored.room == state.room
    assert restored.carries("flashlight")
    assert restored.to_dict() == state.to_dict()


def test_wrong_project_rejected(project: GameProject, tmp_path) -> None:
    engine = Engine(project)
    state = engine.new_state()
    path = tmp_path / "save.json"
    save_state(project, state, path)

    from pyventure.core.model import Meta

    other = GameProject(
        meta=Meta(id="other", title="Other", start_room="bedroom", default_language="fr"),
        languages=project.languages,
        rooms=project.rooms,
        objects=project.objects,
        interactions=project.interactions,
        endings=project.endings,
        vocabulary=project.vocabulary,
        messages=project.messages,
        flags=project.flags,
        counters=project.counters,
        root=project.root,
    )
    with pytest.raises(SaveError):
        load_state(other, path)


def test_corrupted_save(project: GameProject, tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(SaveError):
        load_state(project, path)
