"""Géométrie et logique de la carte, sans dépendance à Tkinter ni à Pillow."""

from __future__ import annotations

from collections import deque
from typing import Any

NODE_W = 170
NODE_H = 96
GRID_X = 230
GRID_Y = 165
MARGIN = 60
PORT_RADIUS = 6
THUMB = (96, 54)

DIRECTION_OFFSETS: dict[str, tuple[int, int]] = {
    "n": (0, -1),
    "s": (0, 1),
    "e": (1, 0),
    "w": (-1, 0),
    "u": (1, -1),
    "d": (-1, 1),
    "in": (0, 1),
    "out": (0, -1),
}
ORDERED_DIRECTIONS = ["e", "w", "n", "s", "u", "d"]

EDGE_COLORS = {
    "plain": "#8899aa",
    "conditional": "#e0a040",
    "hidden": "#6fa8dc",
    "locked": "#d96a6a",
}

EDGE_LABELS = {
    "plain": "sortie simple",
    "conditional": "sortie conditionnelle",
    "hidden": "sortie cachée",
    "locked": "sortie verrouillée",
}


def exit_target(value: Any) -> str | None:
    """Identifiant de la pièce cible d'une sortie."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        target = value.get("room")
        return str(target) if isinstance(target, str) else None
    return None


def edge_style(value: Any) -> str:
    if isinstance(value, dict):
        if value.get("locked_message"):
            return "locked"
        if value.get("hidden"):
            return "hidden"
        if value.get("when"):
            return "conditional"
    return "plain"


def center(position: tuple[int, int]) -> tuple[int, int]:
    return position[0] + NODE_W // 2, position[1] + NODE_H // 2


def auto_layout(rooms: dict[str, Any], start_room: str) -> dict[str, tuple[int, int]]:
    """Place les pièces en largeur depuis la pièce de départ."""
    if not rooms:
        return {}
    start = start_room if start_room in rooms else next(iter(rooms))
    cells: dict[tuple[int, int], str] = {(0, 0): start}
    placed: dict[str, tuple[int, int]] = {start: (0, 0)}
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        cx, cy = placed[current]
        room = rooms.get(current)
        exits = room.get("exits") if isinstance(room, dict) else None
        if not isinstance(exits, dict):
            continue
        for direction, value in exits.items():
            target = exit_target(value)
            if target is None or target in placed or target not in rooms:
                continue
            dx, dy = DIRECTION_OFFSETS.get(str(direction), (1, 0))
            candidate = (cx + dx, cy + dy)
            while candidate in cells:
                candidate = (candidate[0] + 1, candidate[1] + 1)
            cells[candidate] = target
            placed[target] = candidate
            queue.append(target)
    row = max((cell[1] for cell in cells), default=0) + 1
    for room_id in rooms:
        if room_id not in placed:
            placed[room_id] = (0, row)
            row += 1
    return {
        room_id: (MARGIN + cell[0] * GRID_X, MARGIN + cell[1] * GRID_Y)
        for room_id, cell in placed.items()
    }


def guess_direction(source: tuple[int, int], target: tuple[int, int]) -> str:
    sx, sy = center(source)
    tx, ty = center(target)
    dx, dy = tx - sx, ty - sy
    if abs(dx) >= abs(dy):
        return "e" if dx >= 0 else "w"
    return "s" if dy >= 0 else "n"


def edge_point(source: tuple[int, int], target: tuple[int, int]) -> tuple[int, int]:
    """Point où le segment source→cible coupe le bord du rectangle source."""
    x, y = source
    cx, cy = x + NODE_W // 2, y + NODE_H // 2
    tx, ty = center(target)
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    scale_x = (NODE_W / 2) / abs(dx) if dx else float("inf")
    scale_y = (NODE_H / 2) / abs(dy) if dy else float("inf")
    scale = min(scale_x, scale_y)
    return int(cx + dx * scale), int(cy + dy * scale)


def free_direction(room: dict[str, Any], source: tuple[int, int], target: tuple[int, int]) -> str:
    exits = room.get("exits") if isinstance(room, dict) else None
    taken = set(exits) if isinstance(exits, dict) else set()
    preferred = guess_direction(source, target)
    for direction in [preferred, *ORDERED_DIRECTIONS]:
        if direction not in taken:
            return direction
    return preferred
