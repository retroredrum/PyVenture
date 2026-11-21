"""Vue carte : nœuds de pièces, flèches de sorties, glisser-déposer, export."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from ruamel.yaml.comments import CommentedMap

from . import map_export, map_model
from .document import ProjectDocument
from .map_model import (
    EDGE_COLORS,
    MARGIN,
    NODE_H,
    NODE_W,
    PORT_RADIUS,
    THUMB,
)


class MapView(ttk.Frame):
    """Carte interactive des pièces du projet."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        *,
        on_change: Callable[[], None] | None = None,
        on_open: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.on_change = on_change or (lambda: None)
        self.on_open = on_open or (lambda _room: None)

        self.positions: dict[str, tuple[int, int]] = {}
        self.selected: str | None = None
        self._drag_room: str | None = None
        self._drag_offset = (0, 0)
        self._port_source: str | None = None
        self._rubber_line: int | None = None
        self._thumbnails: dict[str, Any] = {}

        self._build_toolbar()
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, background="#1e1e28", highlightthickness=0)
        hbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        vbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=2, pady=2)
        buttons = [
            ("Auto-layout", self.auto_layout),
            ("Sorties réciproques", self.make_reciprocal),
            ("Ajuster", self.fit),
            ("Exporter PNG…", self.export_png),
            ("Exporter PDF…", self.export_pdf),
            ("Enregistrer les positions", self.save_positions),
        ]
        for text, command in buttons:
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=2)
        ttk.Label(
            bar,
            text="Glissez un nœud ; tirez depuis le point à droite pour créer une sortie.",
            foreground="#666",
        ).pack(side="left", padx=8)

    # -- Données ---------------------------------------------------------
    def rooms(self) -> dict[str, Any]:
        rooms = self.document.section("rooms")
        return rooms if isinstance(rooms, dict) else {}

    def reload(self) -> None:
        self._thumbnails.clear()
        rooms = self.rooms()
        saved = self.document.load_map_positions()
        positions = {room_id: saved[room_id] for room_id in rooms if room_id in saved}
        missing = [room_id for room_id in rooms if room_id not in positions]
        if missing:
            auto = self._auto_layout()
            for room_id in missing:
                positions[room_id] = auto.get(room_id, (MARGIN, MARGIN))
        self.positions = positions
        if self.selected not in rooms:
            self.selected = None
        self._draw()

    # -- Disposition -----------------------------------------------------
    def _auto_layout(self) -> dict[str, tuple[int, int]]:
        start = str(self.document.meta().get("start_room") or "")
        return map_model.auto_layout(self.rooms(), start)

    def auto_layout(self) -> None:
        self.positions = self._auto_layout()
        self._draw()
        self.save_positions()

    def save_positions(self) -> None:
        self.document.save_map_positions(self.positions)

    def fit(self) -> None:
        self._draw()

    # -- Géométrie -------------------------------------------------------
    def _rect(self, room_id: str) -> tuple[int, int, int, int]:
        x, y = self.positions.get(room_id, (MARGIN, MARGIN))
        return x, y, NODE_W, NODE_H

    def _center(self, room_id: str) -> tuple[int, int]:
        return map_model.center(self.positions.get(room_id, (MARGIN, MARGIN)))

    def _port(self, room_id: str) -> tuple[int, int]:
        x, y, w, h = self._rect(room_id)
        return x + w, y + h // 2

    # -- Dessin ----------------------------------------------------------
    def _draw(self) -> None:
        self.canvas.delete("all")
        rooms = self.rooms()
        for room_id, room in rooms.items():
            exits = room.get("exits") if isinstance(room, dict) else None
            if not isinstance(exits, dict):
                continue
            for direction, value in exits.items():
                target = map_model.exit_target(value)
                if target in rooms:
                    self._draw_edge(room_id, str(target), value, str(direction))
        for room_id in rooms:
            self._draw_node(room_id)
        self._update_scrollregion()

    def _update_scrollregion(self) -> None:
        if not self.positions:
            self.canvas.configure(scrollregion=(0, 0, 600, 400))
            return
        xs = [x for x, _ in self.positions.values()]
        ys = [y for _, y in self.positions.values()]
        self.canvas.configure(
            scrollregion=(
                min(xs) - MARGIN,
                min(ys) - MARGIN,
                max(xs) + NODE_W + MARGIN,
                max(ys) + NODE_H + MARGIN,
            )
        )

    def _edge_style(self, value: Any) -> str:
        return map_model.edge_style(value)

    def _draw_edge(self, source: str, target: str, value: Any, direction: str) -> None:
        start = map_model.edge_point(self.positions[source], self.positions[target])
        end = map_model.edge_point(self.positions[target], self.positions[source])
        style = map_model.edge_style(value)
        color = EDGE_COLORS[style]
        dash = (6, 4) if style == "hidden" else None
        self.canvas.create_line(*start, *end, fill=color, width=2, arrow=tk.LAST, dash=dash)
        mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        self.canvas.create_text(
            mid[0], mid[1] - 8, text=direction, fill=color, font=("TkDefaultFont", 8)
        )

    def _draw_node(self, room_id: str) -> None:
        x, y, w, h = self._rect(room_id)
        selected = room_id == self.selected
        outline = "#ffd24a" if selected else "#6a6a8a"
        self.canvas.create_rectangle(
            x,
            y,
            x + w,
            y + h,
            fill="#2a2a38",
            outline=outline,
            width=3 if selected else 2,
        )
        room = self.rooms().get(room_id) or {}
        art = room.get("art") if isinstance(room, dict) else None
        thumbnail = self._thumbnail(room_id, art)
        if thumbnail is not None:
            self.canvas.create_image(x + w // 2, y + 8, image=thumbnail, anchor="n")
            text_y = y + h - 14
        else:
            text_y = y + h // 2
        self.canvas.create_text(
            x + w // 2, text_y, text=room_id, fill="#eaeaea", font=("TkDefaultFont", 10, "bold")
        )
        px, py = self._port(room_id)
        self.canvas.create_oval(
            px - PORT_RADIUS,
            py - PORT_RADIUS,
            px + PORT_RADIUS,
            py + PORT_RADIUS,
            fill="#5a5a7a",
            outline="#9a9ab5",
        )

    def _thumbnail(self, room_id: str, art: Any) -> Any:
        if not art:
            return None
        if room_id in self._thumbnails:
            return self._thumbnails[room_id]
        try:
            from PIL import Image, ImageTk

            path = self.document.root / str(art)
            if not path.is_file():
                return None
            with Image.open(path) as image:
                image = image.convert("RGBA")
                image.thumbnail(THUMB)
                photo = ImageTk.PhotoImage(image)
        except Exception:  # noqa: BLE001 - aperçu facultatif
            return None
        self._thumbnails[room_id] = photo
        return photo

    # -- Interactions ----------------------------------------------------
    def _room_at(self, x: int, y: int) -> str | None:
        for room_id in self.rooms():
            rx, ry, rw, rh = self._rect(room_id)
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return room_id
        return None

    def _port_at(self, x: int, y: int) -> str | None:
        for room_id in self.rooms():
            px, py = self._port(room_id)
            if (px - x) ** 2 + (py - y) ** 2 <= (PORT_RADIUS + 4) ** 2:
                return room_id
        return None

    def _event_xy(self, event: tk.Event) -> tuple[int, int]:
        return self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

    def _on_press(self, event: tk.Event) -> None:
        x, y = self._event_xy(event)
        port = self._port_at(x, y)
        if port is not None:
            self._port_source = port
            self._rubber_line = self.canvas.create_line(
                *self._port(port), x, y, fill="#ffd24a", width=2, dash=(4, 3)
            )
            return
        room_id = self._room_at(x, y)
        if room_id is None:
            self.selected = None
            self._draw()
            return
        self.selected = room_id
        self._drag_room = room_id
        rx, ry, _, _ = self._rect(room_id)
        self._drag_offset = (x - rx, y - ry)
        self._draw()

    def _on_motion(self, event: tk.Event) -> None:
        x, y = self._event_xy(event)
        if self._port_source is not None and self._rubber_line is not None:
            self.canvas.coords(self._rubber_line, *self._port(self._port_source), x, y)
            return
        if self._drag_room is not None:
            dx, dy = self._drag_offset
            self.positions[self._drag_room] = (int(x - dx), int(y - dy))
            self._draw()

    def _on_release(self, event: tk.Event) -> None:
        x, y = self._event_xy(event)
        if self._port_source is not None:
            source = self._port_source
            self._port_source = None
            if self._rubber_line is not None:
                self.canvas.delete(self._rubber_line)
                self._rubber_line = None
            target = self._room_at(x, y)
            if target is not None and target != source:
                self._create_exit(source, target)
            else:
                self._draw()
            return
        if self._drag_room is not None:
            self._drag_room = None
            self.save_positions()

    def _on_double_click(self, event: tk.Event) -> None:
        room_id = self._room_at(*self._event_xy(event))
        if room_id is not None:
            self.on_open(room_id)

    def _on_right_click(self, event: tk.Event) -> None:
        room_id = self._room_at(*self._event_xy(event))
        if room_id is None:
            return
        self.selected = room_id
        self._draw()
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Ouvrir", command=lambda: self.on_open(room_id))
        menu.add_command(label="Sorties réciproques", command=lambda: self._reciprocal_for(room_id))
        menu.add_separator()
        menu.add_command(
            label="Supprimer toutes les sorties", command=lambda: self._clear_exits(room_id)
        )
        menu.tk_popup(event.x_root, event.y_root)

    # -- Mutations -------------------------------------------------------
    def _create_exit(self, source: str, target: str) -> None:
        direction = self._free_direction(source, target)
        self.document.snapshot()
        room = self.rooms()[source]
        exits = room.get("exits")
        if not isinstance(exits, dict):
            exits = CommentedMap()
            room["exits"] = exits
        exits[direction] = target
        self.document.touch()
        self.on_change()
        self._draw()

    def _free_direction(self, source: str, target: str) -> str:
        room = self.rooms()[source]
        return map_model.free_direction(room, self.positions[source], self.positions[target])

    def _guess_direction(self, source: str, target: str) -> str:
        return map_model.guess_direction(self.positions[source], self.positions[target])

    def _reciprocal_for(self, room_id: str) -> None:
        exits = self.rooms()[room_id].get("exits") or {}
        targets = {map_model.exit_target(value) for value in exits.values()}
        changed = False
        for target in targets:
            if not isinstance(target, str) or target not in self.rooms():
                continue
            target_exits = self.rooms()[target].get("exits") or {}
            back = {map_model.exit_target(value) for value in target_exits.values()}
            if room_id in back:
                continue
            self.document.snapshot()
            room = self.rooms()[target]
            mapping = room.get("exits")
            if not isinstance(mapping, dict):
                mapping = CommentedMap()
                room["exits"] = mapping
            mapping[self._free_direction(target, room_id)] = room_id
            self.document.touch()
            changed = True
        if changed:
            self.on_change()
        self._draw()

    def make_reciprocal(self) -> None:
        if self.selected is None:
            return
        self._reciprocal_for(self.selected)

    def _clear_exits(self, room_id: str) -> None:
        room = self.rooms()[room_id]
        if not room.get("exits"):
            return
        self.document.snapshot()
        room.pop("exits", None)
        self.document.touch()
        self.on_change()
        self._draw()

    # -- Export ----------------------------------------------------------
    def export_png(self) -> Path | None:
        return self._export("png")

    def export_pdf(self) -> Path | None:
        return self._export("pdf")

    def _export(self, fmt: str) -> Path | None:
        game_id = str(self.document.meta().get("id", "plan"))
        path = filedialog.asksaveasfilename(
            title=f"Exporter le plan ({fmt.upper()})",
            defaultextension=f".{fmt}",
            initialfile=f"{game_id}-plan.{fmt}",
            filetypes=[(fmt.upper(), f"*.{fmt}"), ("Tous les fichiers", "*")],
        )
        if not path:
            return None
        return self.export_to(Path(path), fmt)

    def export_to(self, path: Path | str, fmt: str | None = None) -> Path | None:
        try:
            return map_export.export(self.document, path, fmt, positions=self.positions)
        except Exception as exc:  # noqa: BLE001 - affiché à l'utilisateur
            messagebox.showerror("Erreur", f"Export impossible : {exc}")
            return None
