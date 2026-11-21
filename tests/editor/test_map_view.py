"""Tests de la vue carte (nécessitent un affichage ; sinon ignorés)."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest
from pyventure.editor.document import ProjectDocument

tkinter = pytest.importorskip("tkinter")

from pyventure.editor.map_view import MapView  # noqa: E402

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
def view(tk_root, example_path: Path) -> MapView:
    document = ProjectDocument.load(example_path)
    widget = MapView(tk_root, document)
    widget.reload()
    return widget


def test_reload_places_every_room(view: MapView) -> None:
    assert set(view.positions) == set(view.rooms())


def test_auto_layout_is_deterministic(view: MapView) -> None:
    first = view._auto_layout()
    second = view._auto_layout()
    assert first == second
    assert set(first) == set(view.rooms())


def test_guess_direction(view: MapView) -> None:
    view.positions = {
        "a": (0, 0),
        "east": (600, 0),
        "west": (-600, 0),
        "south": (0, 600),
        "north": (0, -600),
    }
    assert view._guess_direction("a", "east") == "e"
    assert view._guess_direction("a", "west") == "w"
    assert view._guess_direction("a", "south") == "s"
    assert view._guess_direction("a", "north") == "n"


def test_create_exit_links_rooms(view: MapView) -> None:
    view._create_exit("bedroom", "vault")
    exits = view.rooms()["bedroom"].get("exits") or {}
    targets = {
        value if isinstance(value, str) else (value or {}).get("room") for value in exits.values()
    }
    assert "vault" in targets


def test_reciprocal_exits_are_added(view: MapView) -> None:
    view._reciprocal_for("corridor")
    bedroom_exits = view.rooms()["bedroom"].get("exits") or {}
    targets = {
        value if isinstance(value, str) else (value or {}).get("room")
        for value in bedroom_exits.values()
    }
    assert "corridor" in targets


def test_clear_exits(view: MapView) -> None:
    view._clear_exits("corridor")
    room = view.rooms()["corridor"]
    assert not room.get("exits")


def test_hit_testing(view: MapView) -> None:
    x, y, _w, _h = view._rect("bedroom")
    assert view._room_at(x + 5, y + 5) == "bedroom"
    px, py = view._port("bedroom")
    assert view._port_at(px, py) == "bedroom"
    assert view._room_at(-10_000, -10_000) is None


def test_draw_does_not_crash(view: MapView) -> None:
    view._draw()
    assert view.canvas.find_all()


def test_edge_style_detection(view: MapView) -> None:
    assert view._edge_style("cave") == "plain"
    assert view._edge_style({"room": "cave", "hidden": True}) == "hidden"
    assert view._edge_style({"room": "cave", "when": [{"flag": "x"}]}) == "conditional"
    assert view._edge_style({"room": "cave", "locked_message": "m"}) == "locked"


def test_positions_persist_round_trip(tmp_path: Path, example_path: Path) -> None:
    target = tmp_path / "game.yaml"
    document = ProjectDocument.load(example_path)
    document.save(target)
    document.save_map_positions({"bedroom": (10, 20), "cave": (30, 40)})
    reloaded = ProjectDocument.load(target)
    positions = reloaded.load_map_positions()
    assert positions["bedroom"] == (10, 20)
    assert positions["cave"] == (30, 40)
