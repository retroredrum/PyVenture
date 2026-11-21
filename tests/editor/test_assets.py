"""Tests de l'inventaire des illustrations (sans Tkinter)."""

from __future__ import annotations

from pathlib import Path

from pyventure.editor import assets
from pyventure.editor.document import ProjectDocument


def _document(example_path: Path) -> ProjectDocument:
    return ProjectDocument.load(example_path)


def test_collect_assets_lists_every_kind(example_path: Path) -> None:
    document = _document(example_path)
    refs = assets.collect_assets(document.data)
    paths = {ref.path for ref in refs}
    kinds = {ref.kind for ref in refs}
    assert "art/rooms/bedroom.png" in paths
    assert "art/objects/flashlight.png" in paths
    assert "art/endings/escaped.png" in paths
    assert {"room", "object", "ending", "variant"} <= kinds


def test_expected_sizes(example_path: Path) -> None:
    document = _document(example_path)
    refs = assets.collect_assets(document.data)
    room = next(ref for ref in refs if ref.kind == "room")
    game_object = next(ref for ref in refs if ref.kind == "object")
    assert assets.expected_size(document.data, room) == (320, 180)
    assert assets.expected_size(document.data, game_object) == (32, 32)


def test_statuses_report_missing(example_path: Path, tmp_path: Path) -> None:
    document = _document(example_path)
    statuses = assets.statuses(tmp_path, document.data)
    assert statuses
    assert all(not status.exists for status in statuses)
    assert assets.missing(tmp_path, document.data)


def test_make_placeholder_then_detected(tmp_path: Path, example_path: Path) -> None:
    document = _document(example_path)
    room = next(ref for ref in assets.collect_assets(document.data) if ref.kind == "room")
    target = tmp_path / room.path
    assets.make_placeholder(target, (320, 180), "bedroom")
    assert target.is_file()
    assert assets.image_size(target) == (320, 180)

    statuses = assets.statuses(tmp_path, document.data)
    found = next(status for status in statuses if status.ref.path == room.path)
    assert found.exists is True
    assert found.size == (320, 180)
    assert room.path not in {ref.path for ref in assets.missing(tmp_path, document.data)}


def test_unused_files(tmp_path: Path, example_path: Path) -> None:
    document = _document(example_path)
    art = tmp_path / "art" / "rooms"
    art.mkdir(parents=True)
    (art / "bedroom.png").write_bytes(b"")
    (tmp_path / "art" / "orphan.png").write_bytes(b"")
    unused = {path.name for path in assets.unused_files(tmp_path, document.data)}
    assert "orphan.png" in unused
    assert "bedroom.png" not in unused


def test_import_asset_copies_file(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"donnees")
    target = assets.import_asset(source, tmp_path / "root", "art/rooms/x.png")
    assert target.is_file()
    assert target.read_bytes() == b"donnees"


def test_placeholder_color_is_deterministic() -> None:
    assert assets.placeholder_color("cave") == assets.placeholder_color("cave")
    assert assets.placeholder_color("cave") != assets.placeholder_color("vault")


def test_meta_size_defaults() -> None:
    assert assets.meta_size({}) == (320, 180)
    assert assets.meta_size({"meta": {"art": {"width": 256, "height": 144}}}) == (256, 144)


def test_dimension_mismatch_is_flagged(tmp_path: Path, example_path: Path) -> None:
    document = _document(example_path)
    room = next(ref for ref in assets.collect_assets(document.data) if ref.kind == "room")
    assets.make_placeholder(tmp_path / room.path, (100, 100), "x")
    statuses = assets.statuses(tmp_path, document.data)
    found = next(status for status in statuses if status.ref.path == room.path)
    assert found.state == "dimensions"


def test_correct_size_is_ok(tmp_path: Path, example_path: Path) -> None:
    document = _document(example_path)
    room = next(ref for ref in assets.collect_assets(document.data) if ref.kind == "room")
    assets.make_placeholder(tmp_path / room.path, (320, 180), "x")
    statuses = assets.statuses(tmp_path, document.data)
    found = next(status for status in statuses if status.ref.path == room.path)
    assert found.state == "ok"
