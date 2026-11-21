"""Tests de l'export du plan (PNG et PDF), sans Tkinter."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pyventure.editor import map_export, map_model
from pyventure.editor.document import ProjectDocument


def _document(example_path: Path) -> ProjectDocument:
    return ProjectDocument.load(example_path)


def test_resolve_positions_covers_all_rooms(example_path: Path) -> None:
    document = _document(example_path)
    positions = map_export.resolve_positions(document)
    assert set(positions) == set(document.section("rooms"))


def test_render_returns_image(example_path: Path) -> None:
    document = _document(example_path)
    image = map_export.render(document, scale=2.0)
    assert image.width > 0 and image.height > 0
    assert image.mode == "RGB"


def test_render_uses_given_positions(example_path: Path) -> None:
    document = _document(example_path)
    positions = {
        room_id: (index * 300, index * 200)
        for index, room_id in enumerate(document.section("rooms"))
    }
    image = map_export.render(document, positions, scale=1.0)
    assert image.width > 600


def test_export_png_writes_file(example_path: Path, tmp_path: Path) -> None:
    document = _document(example_path)
    target = tmp_path / "plan.png"
    map_export.export_png(document, target)
    assert target.is_file()
    with Image.open(target) as image:
        assert image.format == "PNG"
        assert image.width > 0


def test_export_pdf_writes_file(example_path: Path, tmp_path: Path) -> None:
    document = _document(example_path)
    target = tmp_path / "plan.pdf"
    map_export.export_pdf(document, target)
    assert target.is_file()
    assert target.read_bytes()[:4] == b"%PDF"


def test_export_dispatches_on_suffix(example_path: Path, tmp_path: Path) -> None:
    document = _document(example_path)
    png = map_export.export(document, tmp_path / "a.png")
    pdf = map_export.export(document, tmp_path / "a.pdf")
    assert png.is_file()
    assert pdf.is_file()
    assert pdf.read_bytes()[:4] == b"%PDF"


def test_export_rejects_unknown_format(example_path: Path, tmp_path: Path) -> None:
    document = _document(example_path)
    import pytest

    with pytest.raises(ValueError):
        map_export.export(document, tmp_path / "plan.svg")


def test_render_with_thumbnail(example_path: Path, tmp_path: Path) -> None:
    document = _document(example_path)
    target = tmp_path / "game.yaml"
    document.save(target)
    art = tmp_path / "art" / "rooms"
    art.mkdir(parents=True)
    from pyventure.editor import assets

    assets.make_placeholder(art / "bedroom.png", (320, 180), "bedroom")
    document.section("rooms")["bedroom"]["art"] = "art/rooms/bedroom.png"
    image = map_export.render(document, scale=1.0, thumbnails=True)
    assert image.width > 0


def test_map_model_auto_layout_and_direction(example_path: Path) -> None:
    document = _document(example_path)
    rooms = document.section("rooms")
    layout = map_model.auto_layout(rooms, str(document.meta()["start_room"]))
    assert set(layout) == set(rooms)
    assert map_model.guess_direction((0, 0), (500, 0)) == "e"
    assert map_model.guess_direction((0, 0), (0, 500)) == "s"
    assert map_model.edge_style({"room": "x", "hidden": True}) == "hidden"
    assert map_model.exit_target({"room": "x"}) == "x"
