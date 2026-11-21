"""Fenêtre principale de l'éditeur Tkinter."""

from __future__ import annotations

import copy
import io
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..core.errors import ProjectError
from . import forms, settings
from .assets_tab import AssetsTab
from .document import ProjectDocument, make_yaml
from .map_view import MapView
from .translation_tab import TranslationTab

TREE_SECTIONS = [
    ("meta", "Projet"),
    ("rooms", "Pièces"),
    ("objects", "Objets"),
    ("interactions", "Interactions"),
    ("messages", "Messages"),
    ("endings", "Fins"),
    ("flags", "Flags & compteurs"),
]


class EditorWindow:
    """Fenêtre d'édition d'un projet PyVenture."""

    def __init__(self, root: tk.Tk, document: ProjectDocument | None = None) -> None:
        self.root = root
        self.document = document or ProjectDocument.new()
        self.selection: tuple[str, Any] | None = None
        self._suppress_select = False
        self._preview: subprocess.Popen | None = None
        self._disk_mtime: float | None = None

        root.title("PyVenture — éditeur")
        root.geometry("1100x760")
        root.minsize(800, 560)

        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_status()
        self.refresh_all()
        self._refresh_recent_menu()
        self._remember_current()
        self._disk_mtime = self._current_mtime()

        root.bind("<Control-n>", lambda _event: self.new_project())
        root.bind("<Control-o>", lambda _event: self.open_project())
        root.bind("<Control-s>", lambda _event: self.save_project())
        root.bind("<Control-Shift-S>", lambda _event: self.save_project_as())
        root.bind("<Control-z>", lambda _event: self.undo())
        root.bind("<Control-y>", lambda _event: self.redo())
        root.bind("<Control-d>", lambda _event: self.duplicate_selected())
        root.bind("<F5>", lambda _event: self.play())

        self._autosave_job: str | None = None
        self._schedule_autosave()
        self._schedule_watch()

    # -- Construction ---------------------------------------------------
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Nouveau projet…", command=self.new_project)
        file_menu.add_command(label="Ouvrir…", command=self.open_project)
        self.recent_menu = tk.Menu(file_menu, tearoff=False)
        file_menu.add_cascade(label="Ouvrir un projet récent", menu=self.recent_menu)
        file_menu.add_command(label="Enregistrer", command=self.save_project)
        file_menu.add_command(label="Enregistrer sous…", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(
            label="Exporter le plan (PNG)…", command=lambda: self.map_view.export_png()
        )
        file_menu.add_command(
            label="Exporter le plan (PDF)…", command=lambda: self.map_view.export_pdf()
        )
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.destroy)
        menubar.add_cascade(label="Fichier", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Annuler", command=self.undo)
        edit_menu.add_command(label="Rétablir", command=self.redo)
        edit_menu.add_command(label="Dupliquer", command=self.duplicate_selected)
        menubar.add_cascade(label="Édition", menu=edit_menu)

        project_menu = tk.Menu(menubar, tearoff=False)
        project_menu.add_command(label="Valider", command=self.validate_now)
        project_menu.add_command(label="Jouer", command=self.play)
        project_menu.add_command(label="Recharger depuis le disque", command=self.reload)
        menubar.add_cascade(label="Projet", menu=project_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="À propos", command=self._about)
        menubar.add_cascade(label="Aide", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=4, pady=2)
        buttons = [
            ("Nouvelle pièce", self.add_room),
            ("Nouvel objet", self.add_object),
            ("Nouvelle interaction", self.add_interaction),
            ("Nouveau message", self.add_message),
            ("Nouvelle fin", self.add_ending),
            ("Dupliquer", self.duplicate_selected),
            ("Supprimer", self.delete_selected),
        ]
        for text, command in buttons:
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=2)

    def _build_body(self) -> None:
        paned = ttk.Panedwindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=4, pady=4)

        left = ttk.Frame(paned)
        self.tree = ttk.Treeview(left, show="tree")
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._on_tree_select())
        paned.add(left, weight=1)

        right = ttk.Frame(paned)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)

        self.form_scroll = forms.ScrollFrame(self.notebook)
        self.notebook.add(self.form_scroll, text="Formulaire")

        yaml_tab = ttk.Frame(self.notebook)
        yaml_tab.columnconfigure(0, weight=1)
        yaml_tab.rowconfigure(0, weight=1)
        self.yaml_text = tk.Text(yaml_tab, wrap="none", undo=False)
        yaml_scroll = ttk.Scrollbar(yaml_tab, orient="vertical", command=self.yaml_text.yview)
        self.yaml_text.configure(yscrollcommand=yaml_scroll.set)
        self.yaml_text.grid(row=0, column=0, sticky="nsew")
        yaml_scroll.grid(row=0, column=1, sticky="ns")
        yaml_bar = ttk.Frame(yaml_tab)
        yaml_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Button(yaml_bar, text="Appliquer le YAML", command=self.apply_yaml).pack(
            side="left", padx=4
        )
        self.yaml_error = ttk.Label(yaml_bar, text="", foreground="#b00")
        self.yaml_error.pack(side="left", padx=8)
        self.notebook.add(yaml_tab, text="YAML")

        validation_tab = ttk.Frame(self.notebook)
        validation_tab.columnconfigure(0, weight=1)
        validation_tab.rowconfigure(0, weight=1)
        self.validation_list = tk.Listbox(validation_tab)
        self.validation_list.grid(row=0, column=0, sticky="nsew")
        val_scroll = ttk.Scrollbar(
            validation_tab, orient="vertical", command=self.validation_list.yview
        )
        self.validation_list.configure(yscrollcommand=val_scroll.set)
        val_scroll.grid(row=0, column=1, sticky="ns")
        self.validation_list.bind("<Double-Button-1>", lambda _event: self._navigate_validation())
        self.validation_list.bind("<Return>", lambda _event: self._navigate_validation())
        ttk.Button(validation_tab, text="Valider", command=self.validate_now).grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        ttk.Label(
            validation_tab,
            text="Double-cliquez sur un problème pour ouvrir l'élément concerné.",
            foreground="#666",
        ).grid(row=2, column=0, sticky="w", padx=4)
        self.notebook.add(validation_tab, text="Validation")

        self.map_view = MapView(
            self.notebook,
            self.document,
            on_change=self._on_map_change,
            on_open=self._open_room_from_map,
        )
        self.notebook.add(self.map_view, text="Carte")

        self.assets_tab = AssetsTab(self.notebook, self.document, on_change=self._on_form_change)
        self.notebook.add(self.assets_tab, text="Assets")

        self.translation_tab = TranslationTab(
            self.notebook,
            self.document,
            on_change=self._on_translation_change,
            on_play=self._play_in_language,
        )
        self.notebook.add(self.translation_tab, text="Traductions")

        paned.add(right, weight=3)

    def _build_status(self) -> None:
        self.status = ttk.Label(self.root, text="", anchor="w", relief="sunken")
        self.status.pack(fill="x", side="bottom")

    # -- Rafraîchissement ----------------------------------------------
    def refresh_all(self) -> None:
        self._refresh_tree()
        self._refresh_yaml()
        self.validate_now()
        self._refresh_status()
        self._refresh_title()
        self._build_form()
        self.map_view.document = self.document
        self.assets_tab.document = self.document
        self.map_view.reload()
        self.assets_tab.reload()
        self.translation_tab.document = self.document
        self.translation_tab.reload()

    def _on_translation_change(self) -> None:
        self._refresh_yaml()
        self._refresh_title()
        self._refresh_status()

    def _play_in_language(self, language: str) -> None:
        self.play(language)

    def _on_map_change(self) -> None:
        current_tab = self.notebook.select()
        self._refresh_tree()
        self._refresh_yaml()
        self.validate_now()
        self._refresh_title()
        self._refresh_status()
        self.assets_tab.reload()
        if current_tab:
            self.notebook.select(current_tab)

    def _open_room_from_map(self, room_id: str) -> None:
        iid = f"rooms:{room_id}"
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self._on_tree_select()
            self.notebook.select(0)

    def _refresh_title(self) -> None:
        name = self.document.path.name if self.document.path else "(nouveau projet)"
        marker = "*" if self.document.dirty else ""
        self.root.title(f"PyVenture — éditeur — {name}{marker}")

    def _refresh_status(self) -> None:
        path = str(self.document.path) if self.document.path else "non enregistré"
        undo = "oui" if self.document.can_undo() else "non"
        redo = "oui" if self.document.can_redo() else "non"
        self.status.configure(text=f"{path}   |   annuler : {undo}   |   rétablir : {redo}")

    def _refresh_tree(self) -> None:
        self._suppress_select = True
        try:
            self.tree.delete(*self.tree.get_children())
            for key, label in TREE_SECTIONS:
                node = self.tree.insert("", "end", iid=f"cat:{key}", text=label, open=True)
                if key in {"meta", "flags"}:
                    continue
                if key == "interactions":
                    for index, interaction in enumerate(self.document.section("interactions")):
                        name = (
                            str(interaction.get("id", f"#{index}"))
                            if isinstance(interaction, dict)
                            else f"#{index}"
                        )
                        self.tree.insert(node, "end", iid=f"interaction:{index}", text=name)
                    continue
                section = self.document.section(key)
                if isinstance(section, dict):
                    for item_id in section:
                        self.tree.insert(node, "end", iid=f"{key}:{item_id}", text=str(item_id))
            if self.selection is not None:
                iid = self._iid_for(self.selection)
                if iid and self.tree.exists(iid):
                    self.tree.selection_set(iid)
        finally:
            self._suppress_select = False

    def _iid_for(self, selection: tuple[str, Any]) -> str | None:
        kind, value = selection
        if kind == "meta":
            return "cat:meta"
        if kind == "flags":
            return "cat:flags"
        if kind == "interaction":
            return f"interaction:{value}"
        return f"{kind}:{value}"

    def _refresh_yaml(self) -> None:
        stream = io.StringIO()
        make_yaml().dump(self.document.data, stream)
        self.yaml_text.delete("1.0", "end")
        self.yaml_text.insert("1.0", stream.getvalue())

    def _build_form(self) -> None:
        for child in self.form_scroll.body.winfo_children():
            child.destroy()
        parent = self.form_scroll.body
        document = self.document
        on_change = self._on_form_change
        selection = self.selection
        try:
            if selection is None or (
                selection[0] != "meta" and selection[0] != "flags" and selection[1] is None
            ):
                forms.EmptyForm(parent, document, on_change).pack(fill="both", expand=True)
            elif selection[0] == "meta":
                forms.MetaForm(parent, document, on_change).pack(fill="both", expand=True)
            elif selection[0] == "rooms":
                forms.RoomForm(parent, document, on_change, selection[1]).pack(
                    fill="both", expand=True
                )
            elif selection[0] == "objects":
                forms.ObjectForm(parent, document, on_change, selection[1]).pack(
                    fill="both", expand=True
                )
            elif selection[0] == "interactions":
                forms.InteractionForm(parent, document, on_change, selection[1]).pack(
                    fill="both", expand=True
                )
            elif selection[0] == "messages":
                forms.MessageForm(parent, document, on_change, selection[1]).pack(
                    fill="both", expand=True
                )
            elif selection[0] == "endings":
                forms.EndingForm(parent, document, on_change, selection[1]).pack(
                    fill="both", expand=True
                )
            elif selection[0] == "flags":
                forms.FlagsForm(parent, document, on_change).pack(fill="both", expand=True)
            else:
                forms.EmptyForm(parent, document, on_change).pack(fill="both", expand=True)
        except Exception as exc:  # noqa: BLE001 - affiché dans l'UI
            ttk.Label(parent, text=f"Erreur de formulaire : {exc}", foreground="#b00").pack(
                anchor="w", padx=10, pady=10
            )

    def _on_form_change(self) -> None:
        self._refresh_tree()
        self._refresh_title()
        self._refresh_status()

    def _on_tree_select(self) -> None:
        if self._suppress_select:
            return
        selection = self.tree.selection()
        if not selection:
            return
        iid = selection[0]
        self.selection = self._parse_iid(iid)
        self._build_form()
        if self.selection is not None and self.selection[0] in {
            "rooms",
            "objects",
            "interactions",
            "messages",
            "endings",
        }:
            self.notebook.select(0)

    @staticmethod
    def _parse_iid(iid: str) -> tuple[str, Any] | None:
        if iid.startswith("cat:"):
            key = iid.split(":", 1)[1]
            return ("meta", None) if key == "meta" else (key, None)
        kind, value = iid.split(":", 1)
        if kind == "interaction":
            return ("interactions", int(value))
        return (kind, value)

    # -- Actions --------------------------------------------------------
    def new_project(self) -> None:
        game_id = simpledialog.askstring("Nouveau projet", "Identifiant :", initialvalue="new-game")
        if not game_id:
            return
        title = (
            simpledialog.askstring("Nouveau projet", "Titre :", initialvalue="New Game")
            or "New Game"
        )
        languages = simpledialog.askstring(
            "Nouveau projet", "Langues (séparées par des virgules) :", initialvalue="en"
        )
        codes = tuple(code.strip() for code in (languages or "en").split(",") if code.strip()) or (
            "en",
        )
        self.document = ProjectDocument.new(
            game_id=game_id, title=title, languages=codes, start_room="start"
        )
        self.selection = None
        self.refresh_all()

    def open_project(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir un projet",
            filetypes=[("Projet PyVenture", "game.yaml"), ("YAML", "*.yaml *.yml"), ("Tous", "*")],
        )
        if not path:
            return
        self.load_path(Path(path))

    def load_path(self, path: Path) -> None:
        try:
            self.document = ProjectDocument.load(path)
        except ProjectError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.selection = None
        self.refresh_all()
        self._remember_current()
        self._disk_mtime = self._current_mtime()

    def save_project(self) -> None:
        if self.document.path is None:
            self.save_project_as()
            return
        self._save_to(self.document.path)

    def save_project_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Enregistrer sous", defaultextension=".yaml", initialfile="game.yaml"
        )
        if not path:
            return
        self._save_to(Path(path))

    def _save_to(self, path: Path) -> None:
        try:
            self.document.save(path)
        except ProjectError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self._backup(path)
        self._remember_current()
        self._disk_mtime = self._current_mtime()
        self.refresh_all()
        self._reload_preview()

    # -- Projets récents -------------------------------------------------
    def _remember_current(self) -> None:
        if self.document.path is None:
            return
        settings.remember_project(self.document.path)
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.delete(0, "end")
        recent = settings.recent_projects()
        if not recent:
            self.recent_menu.add_command(label="(aucun)", state="disabled")
            return
        for entry in recent:
            self.recent_menu.add_command(
                label=Path(entry).name + f"  —  {Path(entry).parent}",
                command=lambda value=entry: self.load_path(Path(value)),
            )
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Effacer la liste", command=self._clear_recent)

    def _clear_recent(self) -> None:
        data = settings.load_settings()
        data["recent"] = []
        settings.save_settings(data)
        self._refresh_recent_menu()

    # -- Hot reload ------------------------------------------------------
    def _current_mtime(self) -> float | None:
        path = self.document.path
        if path is None or not path.is_file():
            return None
        try:
            return path.stat().st_mtime
        except OSError:
            return None

    def _schedule_watch(self) -> None:
        self._watch_job = self.root.after(2000, self._check_external_change)

    def _check_external_change(self) -> None:
        try:
            current = self._current_mtime()
            if (
                current is not None
                and self._disk_mtime is not None
                and current != self._disk_mtime
                and not self.document.dirty
            ):
                self.load_path(self.document.path)
        finally:
            self._schedule_watch()

    def _reload_preview(self) -> None:
        if self._preview is not None and self._preview.poll() is None:
            self._preview.terminate()
            self._preview = None
            self.play()

    def _backup(self, path: Path) -> None:
        backups = path.parent / ".pyventure" / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            (backups / f"{path.stem}-{stamp}.yaml").write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8"
            )
        except OSError:
            return

    def reload(self) -> None:
        if self.document.path is None:
            return
        self.load_path(self.document.path)

    def undo(self) -> None:
        if self.document.undo():
            self.refresh_all()
            self._build_form()

    def redo(self) -> None:
        if self.document.redo():
            self.refresh_all()
            self._build_form()

    def validate_now(self) -> None:
        problems = self.document.validate()
        self.validation_list.delete(0, "end")
        if not problems:
            self.validation_list.insert("end", "Aucun problème détecté.")
        for problem in problems:
            self.validation_list.insert("end", problem)
        return None

    def _navigate_validation(self) -> None:
        selection = self.validation_list.curselection()
        if not selection:
            return
        problem = self.validation_list.get(selection[0])
        iid = self._iid_for_problem(problem)
        if iid is not None and self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)
            self._on_tree_select()

    def _iid_for_problem(self, problem: str) -> str | None:
        candidates: list[tuple[int, str]] = []
        for section in ("rooms", "objects", "messages", "endings"):
            mapping = self.document.section(section)
            if not isinstance(mapping, dict):
                continue
            for item_id in mapping:
                position = problem.find(str(item_id))
                if position >= 0:
                    candidates.append((position, f"{section}:{item_id}"))
        interactions = self.document.section("interactions")
        if isinstance(interactions, list):
            for index, interaction in enumerate(interactions):
                if not isinstance(interaction, dict):
                    continue
                interaction_id = str(interaction.get("id", ""))
                if interaction_id:
                    position = problem.find(interaction_id)
                    if position >= 0:
                        candidates.append((position, f"interaction:{index}"))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][1]

    def apply_yaml(self) -> None:
        text = self.yaml_text.get("1.0", "end-1c")
        try:
            data = make_yaml().load(text)
        except Exception as exc:  # noqa: BLE001 - affiché dans l'UI
            self.yaml_error.configure(text=f"YAML invalide : {exc}")
            return
        if not isinstance(data, dict):
            self.yaml_error.configure(text="La racine doit être un objet YAML.")
            return
        self.yaml_error.configure(text="")
        self.document.snapshot()
        self.document.data = data
        self.document.touch()
        self.refresh_all()
        self._build_form()

    def play(self, language: str | None = None) -> None:
        path = self.document.path
        if path is None or self.document.dirty:
            tmp = Path(self.document.root) / ".pyventure" / "preview.yaml"
            try:
                self.document.save(tmp)
                path = tmp
            except ProjectError as exc:
                messagebox.showerror("Erreur", str(exc))
                return
        command = [
            sys.executable,
            "-m",
            "pyventure",
            "play",
            "--gui",
            "-p",
            str(path),
            "--fresh",
            "--no-autosave",
        ]
        if language:
            command += ["--lang", language]
        try:
            self._preview = subprocess.Popen(command)
        except OSError as exc:
            messagebox.showerror("Erreur", f"Impossible de lancer le jeu : {exc}")

    # -- Ajouts et suppression ------------------------------------------
    def _add(self, section: str, item_id: str, template: CommentedMap) -> None:
        mapping = self.document.section(section)
        unique = item_id
        index = 1
        while unique in mapping:
            index += 1
            unique = f"{item_id}-{index}"
        self.document.snapshot()
        mapping[unique] = template
        self.document.touch()
        self.selection = (section, unique)
        self.refresh_all()
        self._build_form()

    def add_room(self) -> None:
        template = CommentedMap()
        template["name"] = CommentedMap(
            {language: "Nouvelle pièce" for language in self.document.languages()}
        )
        template["description"] = CommentedMap(
            {language: "" for language in self.document.languages()}
        )
        self._add("rooms", "new-room", template)

    def add_object(self) -> None:
        template = CommentedMap()
        template["name"] = CommentedMap(
            {language: "Nouvel objet" for language in self.document.languages()}
        )
        template["description"] = CommentedMap(
            {language: "" for language in self.document.languages()}
        )
        template["location"] = "nowhere"
        template["portable"] = True
        self._add("objects", "new-object", template)

    def add_message(self) -> None:
        template = CommentedMap({language: "" for language in self.document.languages()})
        self._add("messages", "new_message", template)

    def add_ending(self) -> None:
        template = CommentedMap()
        template["title"] = CommentedMap(
            {language: "Nouvelle fin" for language in self.document.languages()}
        )
        template["text"] = CommentedMap({language: "" for language in self.document.languages()})
        self._add("endings", "new-ending", template)

    def add_interaction(self) -> None:
        interactions = self.document.section("interactions")
        template = CommentedMap()
        template["id"] = "new-interaction"
        template["verbs"] = CommentedSeq(["use"])
        template["effects"] = CommentedSeq([CommentedMap({"say": "message_key"})])
        self.document.snapshot()
        interactions.append(template)
        self.document.touch()
        self.selection = ("interactions", len(interactions) - 1)
        self.refresh_all()
        self._build_form()

    def duplicate_selected(self) -> None:
        if self.selection is None:
            return
        kind, value = self.selection
        if kind == "interactions":
            interactions = self.document.section("interactions")
            if not (0 <= value < len(interactions)):
                return
            duplicate = copy.deepcopy(interactions[value])
            if isinstance(duplicate, dict):
                base = str(duplicate.get("id", "interaction"))
                duplicate["id"] = self._unique_interaction_id(base)
            self.document.snapshot()
            interactions.append(duplicate)
            self.document.touch()
            self.selection = ("interactions", len(interactions) - 1)
        elif kind in {"rooms", "objects", "messages", "endings"}:
            section = self.document.section(kind)
            if value not in section:
                return
            duplicate = copy.deepcopy(section[value])
            new_id = self._unique_id(section, str(value))
            self.document.snapshot()
            section[new_id] = duplicate
            self.document.touch()
            self.selection = (kind, new_id)
        else:
            return
        self.refresh_all()
        self._build_form()

    @staticmethod
    def _unique_id(mapping: Any, base: str) -> str:
        candidate = f"{base}-copy"
        index = 1
        while candidate in mapping:
            index += 1
            candidate = f"{base}-copy-{index}"
        return candidate

    def _unique_interaction_id(self, base: str) -> str:
        existing = {
            str(interaction.get("id"))
            for interaction in self.document.section("interactions")
            if isinstance(interaction, dict)
        }
        candidate = f"{base}-copy"
        index = 1
        while candidate in existing:
            index += 1
            candidate = f"{base}-copy-{index}"
        return candidate

    def delete_selected(self) -> None:
        if self.selection is None:
            return
        kind, value = self.selection
        if kind == "interactions":
            interactions = self.document.section("interactions")
            if 0 <= value < len(interactions):
                self.document.snapshot()
                del interactions[value]
                self.document.touch()
        elif kind in {"rooms", "objects", "messages", "endings"}:
            section = self.document.section(kind)
            if value in section:
                self.document.snapshot()
                del section[value]
                self.document.touch()
        else:
            return
        self.selection = None
        self.refresh_all()
        self._build_form()

    # -- Autosave -------------------------------------------------------
    def _schedule_autosave(self) -> None:
        self._autosave_job = self.root.after(30_000, self._autosave)

    def _autosave(self) -> None:
        if self.document.dirty and self.document.path is not None:
            target = self.document.path.parent / ".pyventure" / "autosave.yaml"
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("w", encoding="utf-8") as handle:
                    make_yaml().dump(self.document.data, handle)
            except OSError:
                pass
        self._schedule_autosave()

    def _about(self) -> None:
        messagebox.showinfo(
            "À propos",
            "Éditeur PyVenture\n\n"
            "Éditez les pièces, objets, interactions et messages,\n"
            "validez le projet et lancez-le pour tester.",
        )


def open_editor(path: Path | None = None) -> None:
    """Ouvre la fenêtre d'édition."""
    root = tk.Tk()
    document = None
    if path is not None:
        try:
            document = ProjectDocument.load(path)
        except ProjectError as exc:
            messagebox.showerror("Erreur", str(exc))
    EditorWindow(root, document)
    root.mainloop()
