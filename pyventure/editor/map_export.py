"""Export du plan en image (PNG) ou en document (PDF), via Pillow."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from . import map_model
from .map_model import EDGE_COLORS, EDGE_LABELS, MARGIN, NODE_H, NODE_W, THUMB

BACKGROUND = "#1e1e28"
NODE_FILL = "#2a2a38"
NODE_OUTLINE = "#6a6a8a"
TEXT_COLOR = "#eaeaea"
TITLE_COLOR = "#ffd24a"
MUTED_COLOR = "#8a8aa5"
LEGEND_ORDER = ["plain", "conditional", "hidden", "locked"]


_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _font_path() -> str | None:
    for candidate in _FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    return None


def _font(size: int) -> Any:
    from PIL import ImageFont

    size = max(6, int(size))
    path = _font_path()
    if path is not None:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - anciennes versions de Pillow
        return ImageFont.load_default()


def resolve_positions(
    document: Any, positions: dict[str, tuple[int, int]] | None = None
) -> dict[str, tuple[int, int]]:
    """Positions fournies, complétées par l'auto-layout pour les pièces manquantes."""
    rooms = document.section("rooms") or {}
    if not isinstance(rooms, dict):
        return {}
    if positions is None:
        positions = document.load_map_positions()
    merged = {room_id: positions[room_id] for room_id in rooms if room_id in positions}
    start = str(document.meta().get("start_room") or "")
    auto = map_model.auto_layout(rooms, start)
    for room_id in rooms:
        merged.setdefault(room_id, auto.get(room_id, (MARGIN, MARGIN)))
    return merged


def _title_of(document: Any) -> str:
    title = document.meta().get("title")
    default = document.default_language()
    if isinstance(title, dict):
        return str(title.get(default) or next(iter(title.values()), ""))
    return str(title or "")


def _styles_present(rooms: dict[str, Any]) -> list[str]:
    present: set[str] = set()
    for room in rooms.values():
        exits = room.get("exits") if isinstance(room, dict) else None
        if isinstance(exits, dict):
            for value in exits.values():
                present.add(map_model.edge_style(value))
    return [style for style in LEGEND_ORDER if style in present]


def render(
    document: Any,
    positions: dict[str, tuple[int, int]] | None = None,
    *,
    scale: float = 2.0,
    title: str | None = None,
    thumbnails: bool = True,
    background: str = BACKGROUND,
) -> Any:
    """Rend le plan et renvoie une image Pillow."""
    from PIL import Image, ImageDraw

    rooms = document.section("rooms") or {}
    if not isinstance(rooms, dict) or not rooms:
        return Image.new("RGB", (int(400 * scale), int(200 * scale)), background)

    positions = resolve_positions(document, positions)
    factor = max(1.0, float(scale))
    node_w, node_h = int(NODE_W * factor), int(NODE_H * factor)
    margin = int(MARGIN * factor)

    xs = [position[0] for position in positions.values()]
    ys = [position[1] for position in positions.values()]
    min_x, min_y = min(xs), min(ys)
    width_model = (max(xs) + NODE_W) - min_x
    height_model = (max(ys) + NODE_H) - min_y

    title_text = title if title is not None else _title_of(document)
    styles = _styles_present(rooms)
    title_h = int(48 * factor) if title_text else 0
    legend_h = int(36 * factor) if styles else 0

    width = int(width_model * factor) + 2 * margin
    height = int(height_model * factor) + 2 * margin + title_h + legend_h
    image = Image.new("RGB", (max(1, width), max(1, height)), background)
    draw = ImageDraw.Draw(image)

    def transform(point: tuple[int, int]) -> tuple[int, int]:
        return (
            margin + int((point[0] - min_x) * factor),
            margin + title_h + int((point[1] - min_y) * factor),
        )

    font_title = _font(int(20 * factor))
    font_node = _font(int(12 * factor))
    font_small = _font(int(10 * factor))

    if title_text:
        draw.text((margin, margin // 2), title_text, fill=TITLE_COLOR, font=font_title)

    # Flèches
    for room_id, room in rooms.items():
        exits = room.get("exits") if isinstance(room, dict) else None
        if not isinstance(exits, dict):
            continue
        for direction, value in exits.items():
            target = map_model.exit_target(value)
            if target is None or target not in rooms or target not in positions:
                continue
            start = transform(map_model.edge_point(positions[room_id], positions[target]))
            end = transform(map_model.edge_point(positions[target], positions[room_id]))
            style = map_model.edge_style(value)
            color = EDGE_COLORS[style]
            width = max(1, int(2 * factor))
            if style == "hidden":
                _dashed_line(draw, start, end, color, width, int(8 * factor))
            else:
                draw.line([start, end], fill=color, width=width)
            _arrow_head(draw, start, end, color, factor)
            mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            draw.text(
                (mid[0], mid[1] - int(10 * factor)),
                str(direction),
                fill=color,
                font=font_small,
                anchor="mm",
            )

    # Nœuds
    for room_id in rooms:
        if room_id not in positions:
            continue
        x, y = transform(positions[room_id])
        draw.rectangle(
            [x, y, x + node_w, y + node_h],
            fill=NODE_FILL,
            outline=NODE_OUTLINE,
            width=max(1, int(2 * factor)),
        )
        text_y = y + node_h // 2
        if thumbnails:
            thumbnail = _thumbnail(document, rooms[room_id], factor)
            if thumbnail is not None:
                image.paste(
                    thumbnail,
                    (x + (node_w - thumbnail.width) // 2, y + int(6 * factor)),
                    thumbnail,
                )
                text_y = y + node_h - int(14 * factor)
        draw.text(
            (x + node_w // 2, text_y), str(room_id), fill=TEXT_COLOR, font=font_node, anchor="mm"
        )

    if styles:
        _draw_legend(draw, styles, margin, height - margin - int(8 * factor), font_small, factor)

    return image


def _dashed_line(
    draw: Any, start: tuple[int, int], end: tuple[int, int], color: str, width: int, dash: int
) -> None:
    total = math.hypot(end[0] - start[0], end[1] - start[1])
    if total == 0:
        return
    ux, uy = (end[0] - start[0]) / total, (end[1] - start[1]) / total
    position = 0.0
    draw_segment = True
    while position < total:
        segment = min(dash, total - position)
        if draw_segment:
            x1 = start[0] + ux * position
            y1 = start[1] + uy * position
            x2 = start[0] + ux * (position + segment)
            y2 = start[1] + uy * (position + segment)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
        position += segment
        draw_segment = not draw_segment


def _arrow_head(
    draw: Any, start: tuple[int, int], end: tuple[int, int], color: str, factor: float
) -> None:
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = max(6, int(11 * factor))
    for delta in (math.radians(150), math.radians(-150)):
        draw.line(
            [
                end,
                (end[0] + size * math.cos(angle + delta), end[1] + size * math.sin(angle + delta)),
            ],
            fill=color,
            width=max(1, int(2 * factor)),
        )


def _draw_legend(draw: Any, styles: list[str], x: int, y: int, font: Any, factor: float) -> None:
    cursor = x
    for style in styles:
        color = EDGE_COLORS[style]
        draw.line(
            [(cursor, y), (cursor + int(22 * factor), y)], fill=color, width=max(1, int(2 * factor))
        )
        draw.text(
            (cursor + int(28 * factor), y),
            EDGE_LABELS[style],
            fill=MUTED_COLOR,
            font=font,
            anchor="lm",
        )
        cursor += (
            int(28 * factor)
            + int(draw.textlength(EDGE_LABELS[style], font=font))
            + int(20 * factor)
        )


def _thumbnail(document: Any, room: Any, factor: float) -> Any:
    if not isinstance(room, dict) or not room.get("art"):
        return None
    path = Path(document.root) / str(room["art"])
    if not path.is_file():
        return None
    try:
        from PIL import Image

        with Image.open(path) as image:
            image = image.convert("RGBA")
            image.thumbnail((int(THUMB[0] * factor), int(THUMB[1] * factor)))
            return image.copy()
    except Exception:  # noqa: BLE001 - miniature facultative
        return None


def export_png(document: Any, path: Path | str, **options: Any) -> Path:
    path = Path(path)
    image = render(document, **options)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")
    return path


def export_pdf(document: Any, path: Path | str, **options: Any) -> Path:
    path = Path(path)
    image = render(document, **options)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PDF", resolution=150.0)
    return path


def export(document: Any, path: Path | str, fmt: str | None = None, **options: Any) -> Path:
    """Exporte selon l'extension (ou le format explicite)."""
    path = Path(path)
    chosen = (fmt or path.suffix.lstrip(".")).lower()
    if chosen == "pdf":
        return export_pdf(document, path, **options)
    if chosen in {"png", "jpg", "jpeg"}:
        image = render(document, **options)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        return path
    raise ValueError(f"format d'export non pris en charge : {chosen}")
