"""Formulaires d'édition Tkinter pour chaque type de contenu."""

from __future__ import annotations

import io
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..core.rules import CONDITION_SPECS, EFFECT_SPECS
from .document import ProjectDocument, make_yaml


def yaml_text(value: Any) -> str:
    """Sérialise une valeur en YAML lisible."""
    if value is None:
        return ""
    stream = io.StringIO()
    make_yaml().dump(value, stream)
    return stream.getvalue()


def parse_yaml_text(text: str) -> Any:
    """Analyse un fragment YAML. Lève ``ValueError`` si invalide."""
    if not text.strip():
        return None
    try:
        return make_yaml().load(text)
    except Exception as exc:  # noqa: BLE001 - remonté à l'UI
        raise ValueError(str(exc)) from exc


class ScrollFrame(ttk.Frame):
    """Cadre défilant verticalement."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        for widget in (self.canvas, self.body):
            widget.bind("<MouseWheel>", self._on_wheel)
            widget.bind("<Button-4>", self._on_wheel)
            widget.bind("<Button-5>", self._on_wheel)

    def _on_body_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def _on_wheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")


class EditorForm(ttk.Frame):
    """Base des formulaires : aides de construction et d'écriture."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        on_change: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.on_change = on_change
        self.columnconfigure(0, weight=1)

    # -- Aides d'écriture ----------------------------------------------
    def _apply(self, mutate: Callable[[], None]) -> None:
        self.document.snapshot()
        mutate()
        self.document.touch()
        self.on_change()

    def _set(self, container: Any, key: str, value: Any) -> None:
        if value is None:
            if key not in container:
                return
            self._apply(lambda: container.pop(key, None))
            return
        if container.get(key) == value:
            return
        self._apply(lambda: container.__setitem__(key, value))

    def _localized_value(self, container: Any, key: str, language: str) -> str:
        value = container.get(key)
        if isinstance(value, dict):
            return str(value.get(language, ""))
        return str(value) if value is not None else ""

    def _set_localized(self, container: Any, key: str, language: str, value: str) -> None:
        if value == self._localized_value(container, key, language):
            return
        self._apply(lambda: self.document.set_localized(container, key, language, value))

    # -- Aides de construction -----------------------------------------
    def _label(self, parent: tk.Misc, text: str, row: int, column: int = 0) -> None:
        ttk.Label(parent, text=text).grid(row=row, column=column, sticky="w", padx=6, pady=3)

    def _entry(
        self, parent: tk.Misc, value: str, row: int, column: int = 1, width: int = 32
    ) -> tuple[tk.StringVar, ttk.Entry]:
        var = tk.StringVar(value=value)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=column, sticky="ew", padx=6, pady=3)
        return var, entry

    def _combo(
        self, parent: tk.Misc, value: str, values: list[str], row: int, column: int = 1
    ) -> tuple[tk.StringVar, ttk.Combobox]:
        var = tk.StringVar(value=value)
        combo = ttk.Combobox(parent, textvariable=var, values=values, state="normal")
        combo.grid(row=row, column=column, sticky="ew", padx=6, pady=3)
        return var, combo

    def _check(
        self, parent: tk.Misc, value: bool, row: int, column: int = 1
    ) -> tuple[tk.BooleanVar, ttk.Checkbutton]:
        var = tk.BooleanVar(value=value)
        check = ttk.Checkbutton(parent, variable=var)
        check.grid(row=row, column=column, sticky="w", padx=6, pady=3)
        return var, check

    def _spin(
        self,
        parent: tk.Misc,
        value: int,
        row: int,
        column: int = 1,
        *,
        from_: int = 0,
        to: int = 9999,
    ) -> tuple[tk.IntVar, ttk.Spinbox]:
        var = tk.IntVar(value=value)
        spin = ttk.Spinbox(parent, from_=from_, to=to, textvariable=var, width=8)
        spin.grid(row=row, column=column, sticky="w", padx=6, pady=3)
        return var, spin

    def _text(self, parent: tk.Misc, value: str, height: int = 4) -> tk.Text:
        widget = tk.Text(parent, height=height, wrap="word", undo=False)
        widget.insert("1.0", value)
        return widget

    def _bind_entry(
        self, widget: ttk.Entry, var: tk.StringVar, commit: Callable[[str], None]
    ) -> None:
        widget.bind("<FocusOut>", lambda _event: commit(var.get()))
        widget.bind("<Return>", lambda _event: commit(var.get()))

    def _bind_combo(
        self, widget: ttk.Combobox, var: tk.StringVar, commit: Callable[[str], None]
    ) -> None:
        widget.bind("<<ComboboxSelected>>", lambda _event: commit(var.get()))
        widget.bind("<FocusOut>", lambda _event: commit(var.get()))
        widget.bind("<Return>", lambda _event: commit(var.get()))

    def _bind_check(
        self, widget: ttk.Checkbutton, var: tk.BooleanVar, commit: Callable[[bool], None]
    ) -> None:
        widget.configure(command=lambda: commit(bool(var.get())))

    def _bind_spin(
        self, widget: ttk.Spinbox, var: tk.IntVar, commit: Callable[[int], None]
    ) -> None:
        widget.bind("<FocusOut>", lambda _event: self._safe_int(commit, var))
        widget.bind("<Return>", lambda _event: self._safe_int(commit, var))

    def _bind_text(self, widget: tk.Text, commit: Callable[[str], None]) -> None:
        widget.bind("<FocusOut>", lambda _event: commit(widget.get("1.0", "end-1c")))

    @staticmethod
    def _safe_int(commit: Callable[[int], None], var: tk.IntVar) -> None:
        try:
            commit(int(var.get()))
        except (tk.TclError, ValueError):
            return

    def _language_section(
        self,
        parent: tk.Misc,
        title: str,
        container: Any,
        key: str,
        *,
        multiline: bool = False,
        height: int = 4,
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill="x", expand=False, padx=6, pady=4)
        frame.columnconfigure(1, weight=1)
        for row, language in enumerate(self.document.languages()):
            self._label(frame, language, row)
            if multiline:
                text = self._text(frame, self._localized_value(container, key, language), height)
                text.grid(row=row, column=1, sticky="ew", padx=6, pady=3)
                self._bind_text(
                    text,
                    lambda value, lang=language: self._set_localized(container, key, lang, value),
                )
            else:
                var, entry = self._entry(
                    frame, self._localized_value(container, key, language), row
                )
                self._bind_entry(
                    entry,
                    var,
                    lambda value, lang=language: self._set_localized(container, key, lang, value),
                )

    # -- Validation YAML ------------------------------------------------
    def _yaml_editor(
        self,
        parent: tk.Misc,
        title: str,
        value: Any,
        commit: Callable[[Any], None],
        kinds: dict[str, dict[str, str]] | None = None,
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill="both", expand=True, padx=6, pady=4)
        frame.columnconfigure(0, weight=1)
        text = self._text(frame, yaml_text(value), height=8)
        row = 0
        if kinds:
            bar = ttk.Frame(frame)
            bar.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
            combo = ttk.Combobox(bar, values=sorted(kinds), state="readonly", width=24)
            combo.pack(side="left")

            def insert_template() -> None:
                kind = combo.get()
                if kind:
                    text.insert("end", _template_for(kind))

            ttk.Button(bar, text="Insérer un modèle", command=insert_template).pack(
                side="left", padx=4
            )
            row += 1
        text.grid(row=row, column=0, sticky="nsew", padx=4, pady=4)
        error = ttk.Label(frame, text="", foreground="#b00")
        error.grid(row=row + 1, column=0, sticky="w", padx=4)

        def do_commit() -> None:
            try:
                parsed = parse_yaml_text(text.get("1.0", "end-1c"))
            except ValueError as exc:
                error.configure(text=f"YAML invalide : {exc}")
                return
            error.configure(text="")
            commit(parsed)

        text.bind("<FocusOut>", lambda _event: do_commit())


def _template_for(kind: str) -> str:
    templates = {
        "say": "  - say: message_key\n",
        "set_flag": "  - set_flag: my_flag\n",
        "clear_flag": "  - clear_flag: my_flag\n",
        "set_counter": "  - set_counter: {name: score, value: 0}\n",
        "add_counter": "  - add_counter: {name: score, delta: 10}\n",
        "move_object": "  - move_object: {object: item, to: inventory}\n",
        "remove_object": "  - remove_object: item\n",
        "set_object_state": "  - set_object_state: {object: item, state: on}\n",
        "set_room_variant": "  - set_room_variant: {room: room, variant: changed}\n",
        "set_exit": "  - set_exit: {room: room, direction: n, target: other}\n",
        "remove_exit": "  - remove_exit: {room: room, direction: n}\n",
        "teleport": "  - teleport: room\n",
        "score": "  - score: 10\n",
        "end_game": "  - end_game: ending\n",
        "play_sound": "  - play_sound: sound\n",
        "has": "  - has: item\n",
        "not_has": "  - not_has: item\n",
        "flag": "  - flag: my_flag\n",
        "not_flag": "  - not_flag: my_flag\n",
        "room": "  - room: room\n",
        "object_state": "  - object_state: {object: item, state: on}\n",
        "counter": "  - counter: {name: score, gte: 1}\n",
        "all": "  - all:\n      - flag: a\n      - room: room\n",
        "any": "  - any:\n      - flag: a\n      - flag: b\n",
        "not": "  - not:\n      flag: my_flag\n",
    }
    return templates.get(kind, f"  - {kind}: ...\n")


class MetaForm(EditorForm):
    """Formulaire des métadonnées du projet."""

    def __init__(
        self, parent: tk.Misc, document: ProjectDocument, on_change: Callable[[], None]
    ) -> None:
        super().__init__(parent, document, on_change)
        meta = document.meta()
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=6, pady=6)
        frame.columnconfigure(1, weight=1)

        self._label(frame, "Identifiant", 0)
        var, entry = self._entry(frame, str(meta.get("id", "")), 0)
        self._bind_entry(entry, var, lambda value: self._set(meta, "id", value))

        self._label(frame, "Version", 1)
        var, entry = self._entry(frame, str(meta.get("version", "")), 1)
        self._bind_entry(entry, var, lambda value: self._set(meta, "version", value))

        self._label(frame, "Langue par défaut", 2)
        var, combo = self._combo(
            frame, str(meta.get("default_language", "")), document.languages(), 2
        )
        self._bind_combo(combo, var, lambda value: self._set(meta, "default_language", value))

        self._label(frame, "Pièce de départ", 3)
        var, combo = self._combo(
            frame, str(meta.get("start_room", "")), list(document.section("rooms")), 3
        )
        self._bind_combo(combo, var, lambda value: self._set(meta, "start_room", value))

        self._label(frame, "Score maximal", 4)
        var, spin = self._spin(frame, int(meta.get("max_score", 0)), 4)
        self._bind_spin(spin, var, lambda value: self._set(meta, "max_score", value))

        self._language_section(self, "Titre", meta, "title")
        self._language_section(self, "Description", meta, "description", multiline=True, height=3)

        if meta.get("art") is None:
            self._apply(
                lambda: meta.__setitem__(
                    "art", CommentedMap({"width": 320, "height": 180, "scale": 3})
                )
            )
        art = meta.get("art")
        art_frame = ttk.LabelFrame(self, text="Illustration")
        art_frame.pack(fill="x", padx=6, pady=4)
        art_frame.columnconfigure(1, weight=1)
        for row, (key, default, upper) in enumerate(
            (("width", 320, 4096), ("height", 180, 4096), ("scale", 3, 10))
        ):
            self._label(art_frame, key, row)
            var, spin = self._spin(art_frame, int(art.get(key, default)), row, from_=1, to=upper)
            self._bind_spin(spin, var, lambda value, k=key: self._set(art, k, value))


class MessageForm(EditorForm):
    """Formulaire d'un message."""

    def __init__(
        self, parent: tk.Misc, document: ProjectDocument, on_change: Callable[[], None], key: str
    ) -> None:
        super().__init__(parent, document, on_change)
        self._language_section(
            self, f"Message « {key} »", document.section("messages"), key, multiline=True, height=4
        )


class EndingForm(EditorForm):
    """Formulaire d'une fin."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        on_change: Callable[[], None],
        ending_id: str,
    ) -> None:
        super().__init__(parent, document, on_change)
        endings = document.section("endings")
        ending = endings[ending_id]
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=6, pady=6)
        frame.columnconfigure(1, weight=1)
        self._label(frame, "Identifiant", 0)
        var, entry = self._entry(frame, ending_id, 0)
        self._bind_entry(entry, var, lambda value: self._rename(endings, ending_id, value))
        self._label(frame, "Illustration", 1)
        var, entry = self._entry(frame, str(ending.get("art", "")), 1)
        self._bind_entry(entry, var, lambda value: self._set(ending, "art", value or None))
        self._language_section(self, "Titre", ending, "title")
        self._language_section(self, "Texte", ending, "text", multiline=True, height=5)

    def _rename(self, endings: Any, old: str, new: str) -> None:
        if not new or new == old or new in endings:
            return
        value = endings[old]

        def mutate() -> None:
            keys = list(endings.keys())
            items = list(endings.items())
            index = keys.index(old)
            endings.clear()
            for position, (key, item) in enumerate(items):
                endings[new if position == index else key] = value if position == index else item

        self._apply(mutate)


class RoomForm(EditorForm):
    """Formulaire d'une pièce, avec éditeur de sorties."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        on_change: Callable[[], None],
        room_id: str,
    ) -> None:
        super().__init__(parent, document, on_change)
        self.room_id = room_id
        self.rooms = document.section("rooms")
        self.room = self.rooms[room_id]

        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=6, pady=6)
        frame.columnconfigure(1, weight=1)
        self._label(frame, "Identifiant", 0)
        var, entry = self._entry(frame, room_id, 0)
        self._bind_entry(entry, var, lambda value: self._rename_room(value))
        self._label(frame, "Illustration", 1)
        var, entry = self._entry(frame, str(self.room.get("art", "")), 1)
        self._bind_entry(entry, var, lambda value: self._set(self.room, "art", value or None))

        self._language_section(self, "Nom", self.room, "name")
        self._language_section(
            self, "Description", self.room, "description", multiline=True, height=5
        )

        exits = ttk.LabelFrame(self, text="Sorties")
        exits.pack(fill="x", padx=6, pady=4)
        exits.columnconfigure(0, weight=1)
        self.exits_box = exits
        self._build_exits(exits)

        self._yaml_editor(
            self,
            "Variantes (YAML)",
            self.room.get("variants"),
            lambda value: self._set(self.room, "variants", value or None),
        )
        self._yaml_editor(
            self,
            "Effets à l'entrée (YAML)",
            self.room.get("on_enter"),
            lambda value: self._set(self.room, "on_enter", value or None),
            kinds=EFFECT_SPECS,
        )

    def _build_exits(self, parent: tk.Misc) -> None:
        for child in parent.winfo_children():
            child.destroy()
        exits = self.room.get("exits") or CommentedMap()
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew")
        for column, text in enumerate(("Direction", "Destination", "Cachée", "Message verrouillé")):
            ttk.Label(header, text=text).grid(row=0, column=column, sticky="w", padx=4)
        ttk.Button(header, text="Ajouter", command=self._add_exit).grid(row=0, column=4, padx=4)
        rooms = list(self.rooms)
        for index, (direction, value) in enumerate(list(exits.items())):
            target, hidden, locked = _exit_parts(value)
            row = ttk.Frame(parent)
            row.grid(row=index + 1, column=0, sticky="ew", pady=1)
            dir_var = tk.StringVar(value=str(direction))
            dir_entry = ttk.Entry(row, textvariable=dir_var, width=6)
            dir_entry.grid(row=0, column=0, padx=4)
            target_var = tk.StringVar(value=target)
            target_combo = ttk.Combobox(row, textvariable=target_var, values=rooms, width=18)
            target_combo.grid(row=0, column=1, padx=4)
            hidden_var = tk.BooleanVar(value=hidden)
            hidden_check = ttk.Checkbutton(row, variable=hidden_var)
            hidden_check.grid(row=0, column=2, padx=4)
            locked_var = tk.StringVar(value=locked)
            locked_entry = ttk.Entry(row, textvariable=locked_var, width=18)
            locked_entry.grid(row=0, column=3, padx=4)
            ttk.Button(
                row, text="✕", width=3, command=lambda d=direction: self._remove_exit(d)
            ).grid(row=0, column=4, padx=4)
            self._bind_entry(
                dir_entry, dir_var, lambda new, old=direction: self._rename_exit(old, new)
            )
            self._bind_combo(
                target_combo,
                target_var,
                lambda new, d=direction: self._set_exit(d, new, None, None),
            )
            self._bind_check(
                hidden_check, hidden_var, lambda v, d=direction: self._set_exit(d, None, v, None)
            )
            self._bind_entry(
                locked_entry,
                locked_var,
                lambda new, d=direction: self._set_exit(d, None, None, new),
            )

    def _exits(self) -> CommentedMap:
        exits = self.room.get("exits")
        if not isinstance(exits, dict):
            exits = CommentedMap()
            self.room["exits"] = exits
        return exits

    def _add_exit(self) -> None:
        exits = self._exits()
        direction = "n"
        while direction in exits:
            direction += "x"
        rooms = list(self.rooms)
        target = rooms[0] if rooms else self.room_id
        self._apply(lambda: exits.__setitem__(direction, target))
        self._build_exits(self.exits_box)

    def _remove_exit(self, direction: str) -> None:
        exits = self._exits()
        if direction in exits:
            self._apply(lambda: exits.pop(direction, None))
            self._build_exits(self.exits_box)

    def _rename_exit(self, old: str, new: str) -> None:
        if not new or new == old:
            return
        exits = self._exits()
        if new in exits:
            return
        value = exits[old]

        def mutate() -> None:
            exits.pop(old, None)
            exits[new] = value

        self._apply(mutate)
        self._build_exits(self.exits_box)

    def _set_exit(
        self, direction: str, target: str | None, hidden: bool | None, locked: str | None
    ) -> None:
        exits = self._exits()
        if direction not in exits:
            return
        current_target, current_hidden, current_locked = _exit_parts(exits[direction])
        target = current_target if target is None else target
        hidden = current_hidden if hidden is None else hidden
        locked = current_locked if locked is None else locked
        value = _make_exit(target, hidden, locked)

        def mutate() -> None:
            exits[direction] = value

        self._apply(mutate)

    def _rename_room(self, new: str) -> None:
        if not new or new == self.room_id or new in self.rooms:
            return
        self.document.rename_room(self.room_id, new)
        self.room_id = new
        self.on_change()


class ObjectForm(EditorForm):
    """Formulaire d'un objet."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        on_change: Callable[[], None],
        object_id: str,
    ) -> None:
        super().__init__(parent, document, on_change)
        self.object_id = object_id
        self.objects = document.section("objects")
        self.game_object = self.objects[object_id]

        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=6, pady=6)
        frame.columnconfigure(1, weight=1)
        self._label(frame, "Identifiant", 0)
        var, entry = self._entry(frame, object_id, 0)
        self._bind_entry(entry, var, lambda value: self._rename_object(value))

        self._label(frame, "Emplacement", 1)
        locations = ["inventory", "nowhere", *list(document.section("rooms"))]
        var, combo = self._combo(
            frame, str(self.game_object.get("location", "nowhere")), locations, 1
        )
        self._bind_combo(combo, var, lambda value: self._set(self.game_object, "location", value))

        self._label(frame, "Illustration", 2)
        var, entry = self._entry(frame, str(self.game_object.get("art", "")), 2)
        self._bind_entry(
            entry, var, lambda value: self._set(self.game_object, "art", value or None)
        )

        self._label(frame, "État initial", 3)
        var, entry = self._entry(frame, str(self.game_object.get("initial_state", "")), 3)
        self._bind_entry(
            entry, var, lambda value: self._set(self.game_object, "initial_state", value or None)
        )

        self._label(frame, "Portable", 4)
        var, check = self._check(frame, bool(self.game_object.get("portable", True)), 4)
        self._bind_check(check, var, lambda value: self._set(self.game_object, "portable", value))

        self._language_section(self, "Nom", self.game_object, "name")
        self._language_section(
            self, "Description", self.game_object, "description", multiline=True, height=4
        )

        synonyms = ttk.LabelFrame(self, text="Synonymes (séparés par des virgules)")
        synonyms.pack(fill="x", padx=6, pady=4)
        synonyms.columnconfigure(1, weight=1)
        current = self.game_object.get("synonyms") or {}
        for row, language in enumerate(document.languages()):
            self._label(synonyms, language, row)
            words = ", ".join(current.get(language, ()) or ())
            var, entry = self._entry(synonyms, words, row)
            self._bind_entry(
                entry, var, lambda value, lang=language: self._set_synonyms(lang, value)
            )

        self._yaml_editor(
            self,
            "États (YAML)",
            self.game_object.get("states"),
            lambda value: self._set(self.game_object, "states", value or None),
        )

    def _set_synonyms(self, language: str, value: str) -> None:
        words = [word.strip() for word in value.split(",") if word.strip()]
        synonyms = self.game_object.get("synonyms")
        if not isinstance(synonyms, dict):
            synonyms = CommentedMap()
            self.game_object["synonyms"] = synonyms
        if list(synonyms.get(language, ()) or ()) == words:
            return

        def mutate() -> None:
            if words:
                synonyms[language] = CommentedSeq(words)
            else:
                synonyms.pop(language, None)

        self._apply(mutate)

    def _rename_object(self, new: str) -> None:
        if not new or new == self.object_id or new in self.objects:
            return
        self.document.rename_object(self.object_id, new)
        self.object_id = new
        self.on_change()


class InteractionForm(EditorForm):
    """Formulaire d'une interaction."""

    def __init__(
        self, parent: tk.Misc, document: ProjectDocument, on_change: Callable[[], None], index: int
    ) -> None:
        super().__init__(parent, document, on_change)
        self.index = index
        interactions = document.section("interactions")
        self.interaction = interactions[index]
        objects = list(document.section("objects"))
        rooms = list(document.section("rooms"))

        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=6, pady=6)
        frame.columnconfigure(1, weight=1)
        self._label(frame, "Identifiant", 0)
        var, entry = self._entry(frame, str(self.interaction.get("id", "")), 0)
        self._bind_entry(entry, var, lambda value: self._set(self.interaction, "id", value))

        self._label(frame, "Verbes", 1)
        var, entry = self._entry(frame, _join(self.interaction.get("verbs")), 1)
        self._bind_entry(entry, var, lambda value: self._set_list(self.interaction, "verbs", value))

        self._label(frame, "Objets", 2)
        var, entry = self._entry(frame, _join(self.interaction.get("objects")), 2)
        self._bind_entry(
            entry, var, lambda value: self._set_list(self.interaction, "objects", value)
        )

        self._label(frame, "Objets indirects", 3)
        var, entry = self._entry(frame, _join(self.interaction.get("indirect_objects")), 3)
        self._bind_entry(
            entry, var, lambda value: self._set_list(self.interaction, "indirect_objects", value)
        )

        self._label(frame, "Une seule fois", 4)
        var, check = self._check(frame, bool(self.interaction.get("once", False)), 4)
        self._bind_check(check, var, lambda value: self._set(self.interaction, "once", value))

        self._label(frame, "Priorité", 5)
        var, spin = self._spin(
            frame, int(self.interaction.get("priority", 0)), 5, from_=-100, to=100
        )
        self._bind_spin(spin, var, lambda value: self._set(self.interaction, "priority", value))

        ttk.Label(
            self,
            text=f"Objets : {', '.join(objects) or '—'}    Pièces : {', '.join(rooms) or '—'}",
            foreground="#666",
        ).pack(anchor="w", padx=8)

        self._yaml_editor(
            self,
            "Conditions (YAML)",
            self.interaction.get("when"),
            lambda value: self._set(self.interaction, "when", value or None),
            kinds=CONDITION_SPECS,
        )
        self._yaml_editor(
            self,
            "Effets (YAML)",
            self.interaction.get("effects"),
            lambda value: self._set(self.interaction, "effects", value or CommentedSeq()),
            kinds=EFFECT_SPECS,
        )

    def _set_list(self, container: Any, key: str, value: str) -> None:
        words = [word.strip() for word in value.split(",") if word.strip()]
        if _join(container.get(key)) == ", ".join(words):
            return

        def mutate() -> None:
            if words:
                container[key] = CommentedSeq(words)
            else:
                container.pop(key, None)

        self._apply(mutate)


class FlagsForm(EditorForm):
    """Édition des flags et compteurs."""

    def __init__(
        self, parent: tk.Misc, document: ProjectDocument, on_change: Callable[[], None]
    ) -> None:
        super().__init__(parent, document, on_change)
        flags = document.section("flags")
        counters = document.section("counters")

        flags_frame = ttk.LabelFrame(self, text="Flags")
        flags_frame.pack(fill="x", padx=6, pady=4)
        for row, (name, value) in enumerate(list(flags.items())):
            ttk.Label(flags_frame, text=name).grid(row=row, column=0, sticky="w", padx=4)
            var = tk.BooleanVar(value=bool(value))
            check = ttk.Checkbutton(flags_frame, variable=var)
            check.grid(row=row, column=1, sticky="w", padx=4)
            self._bind_check(check, var, lambda v, key=name: self._set(flags, key, bool(v)))

        counters_frame = ttk.LabelFrame(self, text="Compteurs")
        counters_frame.pack(fill="x", padx=6, pady=4)
        for row, (name, value) in enumerate(list(counters.items())):
            ttk.Label(counters_frame, text=name).grid(row=row, column=0, sticky="w", padx=4)
            var = tk.IntVar(value=int(value))
            spin = ttk.Spinbox(counters_frame, from_=-9999, to=9999, textvariable=var, width=8)
            spin.grid(row=row, column=1, sticky="w", padx=4)
            self._bind_spin(spin, var, lambda v, key=name: self._set(counters, key, int(v)))


class EmptyForm(EditorForm):
    """Panneau affiché quand rien n'est sélectionné."""

    def __init__(
        self, parent: tk.Misc, document: ProjectDocument, on_change: Callable[[], None]
    ) -> None:
        super().__init__(parent, document, on_change)
        ttk.Label(
            self,
            text="Sélectionnez un élément dans l'arbre, ou utilisez l'onglet YAML.",
            padding=20,
        ).pack(anchor="w")


# --- Aides --------------------------------------------------------------


def _join(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _exit_parts(value: Any) -> tuple[str, bool, str]:
    if isinstance(value, str):
        return value, False, ""
    if isinstance(value, dict):
        return (
            str(value.get("room", "")),
            bool(value.get("hidden", False)),
            str(value.get("locked_message", "") or ""),
        )
    return "", False, ""


def _make_exit(target: str, hidden: bool, locked: str) -> Any:
    if not hidden and not locked:
        return target
    data = CommentedMap()
    data["room"] = target
    if locked:
        data["locked_message"] = locked
    if hidden:
        data["hidden"] = True
    return data
