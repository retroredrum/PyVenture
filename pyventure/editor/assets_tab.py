"""Onglet de gestion des illustrations du projet."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import assets
from .document import ProjectDocument

PREVIEW = (320, 180)


class AssetsTab(ttk.Frame):
    """Liste les illustrations, permet de les prévisualiser et de les gérer."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        *,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.on_change = on_change or (lambda: None)
        self._photo: object | None = None
        self._statuses: list[assets.AssetStatus] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        columns = ("path", "kind", "owner", "state", "size")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        headings = {
            "path": "Fichier",
            "kind": "Type",
            "owner": "Propriétaire",
            "state": "État",
            "size": "Dimensions",
        }
        widths = {"path": 260, "kind": 80, "owner": 150, "state": 90, "size": 100}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._preview_selected())

        side = ttk.Frame(self)
        side.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.preview = tk.Label(
            side, text="(aucun aperçu)", background="#20202a", foreground="#bbb"
        )
        self.preview.pack(fill="both", expand=True)
        self.detail = ttk.Label(side, text="", wraplength=320, justify="left")
        self.detail.pack(fill="x", pady=4)

        buttons = ttk.Frame(self)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=2)
        ttk.Button(buttons, text="Rafraîchir", command=self.reload).pack(side="left", padx=2)
        ttk.Button(buttons, text="Importer / Remplacer…", command=self.import_selected).pack(
            side="left", padx=2
        )
        ttk.Button(buttons, text="Générer un placeholder", command=self.placeholder_selected).pack(
            side="left", padx=2
        )
        ttk.Button(
            buttons, text="Placeholders manquants", command=self.placeholders_all_missing
        ).pack(side="left", padx=2)

        self.report = ttk.Label(self, text="", foreground="#666", justify="left")
        self.report.grid(row=2, column=0, columnspan=2, sticky="w", padx=6)

    # -- Données ---------------------------------------------------------
    def reload(self) -> None:
        self._statuses = assets.statuses(self.document.root, self.document.data)
        self.tree.delete(*self.tree.get_children())
        for index, status in enumerate(self._statuses):
            size = f"{status.size[0]}×{status.size[1]}" if status.size else "—"
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(status.ref.path, status.ref.kind, status.ref.owner, status.state, size),
            )
        unused = assets.unused_files(self.document.root, self.document.data)
        missing = [status for status in self._statuses if not status.exists]
        parts = [f"{len(self._statuses)} illustration(s) référencée(s)"]
        if missing:
            parts.append(f"{len(missing)} manquante(s)")
        if unused:
            parts.append(f"{len(unused)} fichier(s) inutilisé(s)")
        self.report.configure(text="   |   ".join(parts))
        self._preview_selected()

    def _selected_status(self) -> assets.AssetStatus | None:
        selection = self.tree.selection()
        if not selection:
            return None
        index = int(selection[0])
        if 0 <= index < len(self._statuses):
            return self._statuses[index]
        return None

    def _preview_selected(self) -> None:
        status = self._selected_status()
        if status is None:
            self.preview.configure(image="", text="(aucun aperçu)")
            self.detail.configure(text="")
            return
        path = assets.resolve(self.document.root, status.ref)
        expected = assets.expected_size(self.document.data, status.ref)
        if not status.exists:
            self.preview.configure(image="", text=f"Manquant : {status.ref.path}")
            self.detail.configure(
                text=f"{status.ref.label()} — attendu {expected[0]}×{expected[1]} px"
            )
            return
        try:
            from PIL import Image, ImageTk

            with Image.open(path) as image:
                image = image.convert("RGBA")
                image.thumbnail(PREVIEW)
                photo = ImageTk.PhotoImage(image)
        except Exception as exc:  # noqa: BLE001 - aperçu facultatif
            self.preview.configure(image="", text=f"Aperçu indisponible : {exc}")
            self.detail.configure(text=str(path))
            return
        self._photo = photo
        self.preview.configure(image=photo, text="")
        size = status.size or (0, 0)
        dimensions = f"{size[0]}×{size[1]} px (attendu {expected[0]}×{expected[1]})"
        self.detail.configure(text=f"{status.ref.label()}\n{path}\n{dimensions}")

    # -- Actions ---------------------------------------------------------
    def import_selected(self) -> None:
        status = self._selected_status()
        if status is None:
            messagebox.showinfo("Importer", "Sélectionnez d'abord une illustration dans la liste.")
            return
        source = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("Tous", "*")],
        )
        if not source:
            return
        try:
            assets.import_asset(Path(source), self.document.root, status.ref.path)
        except OSError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        self.reload()
        self.on_change()

    def placeholder_selected(self) -> None:
        status = self._selected_status()
        if status is None:
            return
        expected = assets.expected_size(self.document.data, status.ref)
        target = assets.resolve(self.document.root, status.ref)
        try:
            assets.make_placeholder(target, expected, status.ref.owner)
        except Exception as exc:  # noqa: BLE001 - Pillow ou écriture
            messagebox.showerror("Erreur", str(exc))
            return
        self.reload()

    def placeholders_all_missing(self) -> None:
        missing = assets.missing(self.document.root, self.document.data)
        for ref in missing:
            expected = assets.expected_size(self.document.data, ref)
            try:
                assets.make_placeholder(
                    assets.resolve(self.document.root, ref), expected, ref.owner
                )
            except Exception:  # noqa: BLE001 - on continue
                continue
        self.reload()
