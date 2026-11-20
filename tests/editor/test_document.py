"""Tests de la couche document de l'éditeur (sans Tkinter)."""

from __future__ import annotations

from pathlib import Path

from pyventure.editor.document import ProjectDocument
from ruamel.yaml.comments import CommentedMap, CommentedSeq


def test_new_document_is_valid() -> None:
    document = ProjectDocument.new(game_id="demo", title="Demo", languages=("fr", "en"))
    assert document.validate() == []
    project = document.project()
    assert project.meta.id == "demo"
    assert project.meta.start_room == "start"
    assert "start" in project.rooms


def test_load_example_and_validate(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    assert document.validate() == []
    assert set(document.section("rooms")) == {"bedroom", "corridor", "cave", "vault"}


def test_save_round_trip(example_path: Path, tmp_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    document.section("flags")["new_flag"] = True
    document.touch()
    target = tmp_path / "out" / "game.yaml"
    document.save(target)
    assert target.is_file()
    assert document.dirty is False

    reloaded = ProjectDocument.load(target)
    assert reloaded.section("flags")["new_flag"] is True
    assert reloaded.validate() == []


def test_save_preserves_comments(tmp_path: Path) -> None:
    source = tmp_path / "game.yaml"
    source.write_text(
        "# mon commentaire\n"
        "format: pyventure-game\n"
        "format_version: 1\n"
        "meta:\n"
        "  id: demo\n"
        "  title: Demo\n"
        "  default_language: en\n"
        "  start_room: start\n"
        "languages: [en]\n"
        "rooms:\n"
        "  start:\n"
        "    name: Start\n"
        "    description: A room.\n",
        encoding="utf-8",
    )
    document = ProjectDocument.load(source)
    document.save()
    assert "# mon commentaire" in source.read_text(encoding="utf-8")


def test_undo_redo() -> None:
    document = ProjectDocument.new(languages=("en",))
    assert not document.can_undo()
    document.snapshot()
    document.section("flags")["a"] = True
    document.touch()
    assert document.can_undo()
    assert document.undo() is True
    assert "a" not in document.section("flags")
    assert document.redo() is True
    assert document.section("flags")["a"] is True


def test_validate_detects_broken_reference(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    document.section("rooms")["bedroom"]["exits"]["n"] = "ghost-room"
    problems = document.validate()
    assert any("ghost-room" in problem for problem in problems)


def test_set_localized_creates_multilingual(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    room = document.section("rooms")["bedroom"]
    document.set_localized(room, "name", "en", "The Bedroom")
    assert room["name"]["en"] == "The Bedroom"


def test_rename_room_updates_references(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    document.rename_room("cave", "grotto")
    assert "grotto" in document.section("rooms")
    assert "cave" not in document.section("rooms")
    # sortie de corridor -> cave devient grotto
    assert document.section("rooms")["corridor"]["exits"]["n"] == "grotto"
    # condition room: cave dans l'interaction
    interactions = document.section("interactions")
    when = interactions[0]["when"]
    rooms = [condition.get("room") for condition in when if isinstance(condition, dict)]
    assert "grotto" in rooms
    assert document.validate() == []


def test_rename_object_updates_references(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    document.rename_object("flashlight", "lamp")
    assert "lamp" in document.section("objects")
    interactions = document.section("interactions")
    assert "lamp" in interactions[0]["objects"]
    assert document.validate() == []


def test_rename_object_updates_object_state_condition(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    document.section("interactions").append(
        CommentedMap(
            {
                "id": "test",
                "verbs": CommentedSeq(["use"]),
                "objects": CommentedSeq(["flashlight"]),
                "when": CommentedSeq(
                    [CommentedMap({"object_state": {"object": "flashlight", "state": "off"}})]
                ),
                "effects": CommentedSeq([CommentedMap({"say": "hello"})]),
            }
        )
    )
    document.rename_object("flashlight", "lamp")
    condition = document.section("interactions")[2]["when"][0]["object_state"]
    assert condition["object"] == "lamp"
