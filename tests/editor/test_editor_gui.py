"""Tests de l'éditeur Tkinter (nécessitent un affichage ; sinon ignorés)."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest
from pyventure.editor import forms
from pyventure.editor.document import ProjectDocument

tkinter = pytest.importorskip("tkinter")
from tkinter import ttk  # noqa: E402

from pyventure.editor.main_window import EditorWindow  # noqa: E402

pytestmark = pytest.mark.editor


@pytest.fixture
def tk_root():
    try:
        root = tkinter.Tk()
    except tkinter.TclError as exc:
        pytest.skip(f"pas d'affichage Tk : {exc}")
    root.withdraw()
    yield root
    with contextlib.suppress(tkinter.TclError):
        root.destroy()


@pytest.fixture
def window(tk_root, example_path: Path) -> EditorWindow:
    return EditorWindow(tk_root, ProjectDocument.load(example_path))


# --- Aides pures ---------------------------------------------------------


def test_yaml_text_round_trip() -> None:
    value = [{"say": "hello"}, {"set_flag": "done"}]
    text = forms.yaml_text(value)
    assert forms.parse_yaml_text(text) == value


def test_parse_yaml_text_empty_is_none() -> None:
    assert forms.parse_yaml_text("   ") is None


def test_parse_yaml_text_invalid_raises() -> None:
    with pytest.raises(ValueError):
        forms.parse_yaml_text("[unclosed")


def test_exit_helpers() -> None:
    assert forms._exit_parts("cave") == ("cave", False, "")
    assert forms._exit_parts({"room": "cave", "hidden": True}) == ("cave", True, "")
    assert forms._make_exit("cave", False, "") == "cave"
    made = forms._make_exit("cave", True, "locked")
    assert made["room"] == "cave"
    assert made["hidden"] is True
    assert made["locked_message"] == "locked"


def test_join_list() -> None:
    assert forms._join(["a", "b"]) == "a, b"
    assert forms._join(None) == ""


def test_template_for_known_and_unknown() -> None:
    assert "set_flag" in forms._template_for("set_flag")
    assert forms._template_for("inconnu")


# --- Fenêtre -------------------------------------------------------------


def test_tree_lists_content(window: EditorWindow) -> None:
    rooms_node = window.tree.get_children("cat:rooms")
    assert "bedroom" in [window.tree.item(node, "text") for node in rooms_node]
    assert window.tree.exists("cat:objects")


def test_select_room_builds_form(window: EditorWindow) -> None:
    window.tree.selection_set("rooms:bedroom")
    window._on_tree_select()
    assert window.selection == ("rooms", "bedroom")
    assert window.form_scroll.body.winfo_children()


def test_add_and_delete_room(window: EditorWindow) -> None:
    before = len(window.document.section("rooms"))
    window.add_room()
    assert len(window.document.section("rooms")) == before + 1
    assert window.selection[0] == "rooms"
    window.delete_selected()
    assert len(window.document.section("rooms")) == before


def test_add_interaction_and_delete(window: EditorWindow) -> None:
    before = len(window.document.section("interactions"))
    window.add_interaction()
    assert len(window.document.section("interactions")) == before + 1
    window.delete_selected()
    assert len(window.document.section("interactions")) == before


def test_undo_redo_via_window(window: EditorWindow) -> None:
    window.add_room()
    count = len(window.document.section("rooms"))
    window.undo()
    assert len(window.document.section("rooms")) == count - 1
    window.redo()
    assert len(window.document.section("rooms")) == count


def test_validate_now_reports_problem(window: EditorWindow) -> None:
    window.document.section("rooms")["bedroom"]["exits"]["n"] = "ghost"
    window.validate_now()
    entries = window.validation_list.get(0, "end")
    assert any("ghost" in entry for entry in entries)


def test_apply_yaml_updates_document(window: EditorWindow) -> None:
    window.yaml_text.delete("1.0", "end")
    window.yaml_text.insert(
        "1.0",
        "format: pyventure-game\n"
        "format_version: 1\n"
        "meta: {id: demo, title: Demo, default_language: en, start_room: start}\n"
        "languages: [en]\n"
        "rooms:\n"
        "  start: {name: Start, description: A room.}\n",
    )
    window.apply_yaml()
    assert window.document.meta()["id"] == "demo"
    assert window.yaml_error.cget("text") == ""


def test_apply_yaml_reports_error(window: EditorWindow) -> None:
    window.yaml_text.delete("1.0", "end")
    window.yaml_text.insert("1.0", "[unclosed")
    window.apply_yaml()
    assert window.yaml_error.cget("text")


def test_save_and_reload(window: EditorWindow, tmp_path: Path) -> None:
    window.document.section("flags")["x"] = True
    target = tmp_path / "game.yaml"
    window._save_to(target)
    assert target.is_file()
    assert window.document.dirty is False
    window.document.section("flags")["x"] = False
    window.reload()
    assert window.document.section("flags")["x"] is True


def test_flags_form_renders(window: EditorWindow) -> None:
    window.selection = ("flags", None)
    window._build_form()
    assert window.form_scroll.body.winfo_children()


def test_meta_form_renders(window: EditorWindow) -> None:
    window.selection = ("meta", None)
    window._build_form()
    assert window.form_scroll.body.winfo_children()


def test_object_form_renders(window: EditorWindow) -> None:
    window.selection = ("objects", "flashlight")
    window._build_form()
    assert window.form_scroll.body.winfo_children()


def test_interaction_form_renders(window: EditorWindow) -> None:
    window.selection = ("interactions", 0)
    window._build_form()
    assert window.form_scroll.body.winfo_children()


def test_message_and_ending_forms(window: EditorWindow) -> None:
    window.selection = ("messages", "flashlight_on")
    window._build_form()
    assert window.form_scroll.body.winfo_children()
    window.selection = ("endings", "escaped")
    window._build_form()
    assert window.form_scroll.body.winfo_children()


def test_room_form_edit_updates_document(window: EditorWindow) -> None:
    window.selection = ("rooms", "bedroom")
    window._build_form()
    document = window.document
    document.section("rooms")["bedroom"]["art"] = "rooms/bedroom.png"
    window._on_form_change()
    assert document.section("rooms")["bedroom"]["art"] == "rooms/bedroom.png"
    assert isinstance(window.tree, ttk.Treeview)


def test_duplicate_room(window: EditorWindow) -> None:
    before = len(window.document.section("rooms"))
    window.selection = ("rooms", "bedroom")
    window.duplicate_selected()
    rooms = window.document.section("rooms")
    assert len(rooms) == before + 1
    assert "bedroom-copy" in rooms
    assert window.selection == ("rooms", "bedroom-copy")


def test_duplicate_object(window: EditorWindow) -> None:
    window.selection = ("objects", "flashlight")
    window.duplicate_selected()
    assert "flashlight-copy" in window.document.section("objects")


def test_duplicate_interaction(window: EditorWindow) -> None:
    window.selection = ("interactions", 0)
    window.duplicate_selected()
    interactions = window.document.section("interactions")
    assert len(interactions) == 3
    assert interactions[-1]["id"] == "light-cave-copy"


def test_duplicate_twice_gives_unique_ids(window: EditorWindow) -> None:
    window.selection = ("rooms", "bedroom")
    window.duplicate_selected()
    window.selection = ("rooms", "bedroom")
    window.duplicate_selected()
    rooms = window.document.section("rooms")
    assert "bedroom-copy" in rooms
    assert "bedroom-copy-2" in rooms


def test_duplicate_undo(window: EditorWindow) -> None:
    window.selection = ("rooms", "bedroom")
    window.duplicate_selected()
    count = len(window.document.section("rooms"))
    window.undo()
    assert len(window.document.section("rooms")) == count - 1


def test_navigate_validation_selects_element(window: EditorWindow) -> None:
    window.document.section("rooms")["bedroom"]["exits"]["n"] = "ghost"
    window.validate_now()
    entries = list(window.validation_list.get(0, "end"))
    index = next(position for position, entry in enumerate(entries) if "bedroom" in entry)
    window.validation_list.selection_clear(0, "end")
    window.validation_list.selection_set(index)
    window._navigate_validation()
    assert window.selection == ("rooms", "bedroom")


def test_iid_for_problem_points_to_interaction(window: EditorWindow) -> None:
    window.document.section("interactions")[0]["objects"] = ["ghost"]
    window.validate_now()
    entries = list(window.validation_list.get(0, "end"))
    problem = next(entry for entry in entries if "ghost" in entry)
    assert window._iid_for_problem(problem) == "interaction:0"


def test_external_change_reloads_when_clean(
    window: EditorWindow, tmp_path: Path, monkeypatch
) -> None:
    import os

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    target = tmp_path / "game.yaml"
    window.document.section("flags")["ext"] = True
    window._save_to(target)
    assert window.document.section("flags")["ext"] is True

    target.write_text(
        target.read_text(encoding="utf-8").replace("ext: true", "ext: false"), encoding="utf-8"
    )
    stamp = target.stat().st_mtime + 10
    os.utime(target, (stamp, stamp))

    window._check_external_change()
    assert window.document.section("flags")["ext"] is False


def test_recent_menu_populated(window: EditorWindow, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    window._refresh_recent_menu()
    assert window.recent_menu.index("end") is not None
    assert window.recent_menu.index("end") >= 0


def test_window_has_map_and_assets_tabs(window: EditorWindow) -> None:
    tabs = [window.notebook.tab(index, "text") for index in range(window.notebook.index("end"))]
    assert "Carte" in tabs
    assert "Assets" in tabs


def test_open_room_from_map_selects_room(window: EditorWindow) -> None:
    window._open_room_from_map("cave")
    assert window.selection == ("rooms", "cave")


def test_assets_tab_lists_references(window: EditorWindow) -> None:
    window.assets_tab.reload()
    assert window.assets_tab.tree.get_children()


def test_map_tab_places_rooms(window: EditorWindow) -> None:
    window.map_view.reload()
    assert set(window.map_view.positions) == set(window.document.section("rooms"))
