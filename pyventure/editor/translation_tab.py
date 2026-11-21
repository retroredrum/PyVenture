"""Onglet de traduction : tableau clés × langues, édition côte à côte, CSV."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from . import translation
from .document import ProjectDocument

FILTERS = {
    "Tous": "all",
    "Manquants": "missing",
    "Placeholders": "placeholders",
}


class TranslationTab(ttk.Frame):
    """Tableau des traductions, avec édition côte à côte."""

    def __init__(
        self,
        parent: tk.Misc,
        document: ProjectDocument,
        *,
        on_change: Callable[[], None] | None = None,
        on_play: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.document = document
        self.on_change = on_change or (lambda: None)
        self.on_play = on_play or (lambda _language: None)
        self.entries: list[translation.TranslationEntry] = []
        self._current: translation.TranslationEntry | None = None
        self._editors: dict[str, tk.Text] = {}
        self._pseudo_editor: tk.Text | None = None
        self._editor_languages: tuple[str, ...] = ()

        self._build()
        self.reload()

    # -- Construction ----------------------------------------------------
    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=3)
        self.rowconfigure(3, weight=2)

        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=4, pady=2)
        ttk.Label(toolbar, text="Filtre :").pack(side="left", padx=(0, 4))
        self.filter_var = tk.StringVar(value="Tous")
        combo = ttk.Combobox(
            toolbar, textvariable=self.filter_var, values=list(FILTERS), state="readonly", width=12
        )
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _event: self._populate())
        ttk.Label(toolbar, text="Recherche :").pack(side="left", padx=(8, 4))
        self.search_var = tk.StringVar()
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=20)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda _event: self._populate())
        self.pseudo_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            toolbar,
            text="Pseudo-locale",
            variable=self.pseudo_var,
            command=self._apply_display_columns,
        ).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Rafraîchir", command=self.reload).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Importer CSV…", command=self.import_csv).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Exporter CSV…", command=self.export_csv).pack(side="left", padx=2)

        actions = ttk.Frame(self)
        actions.grid(row=1, column=0, sticky="ew", padx=4, pady=2)
        ttk.Label(actions, text="Langue :").pack(side="left", padx=(0, 4))
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(
            actions, textvariable=self.language_var, state="readonly", width=6
        )
        self.language_combo.pack(side="left")
        ttk.Button(actions, text="Aperçu de la pièce de départ…", command=self.preview).pack(
            side="left", padx=2
        )
        ttk.Button(actions, text="Jouer dans cette langue", command=self.play).pack(
            side="left", padx=2
        )
        ttk.Label(
            actions,
            text="Sélectionnez une ligne puis modifiez les champs ci-dessous (annulable).",
            foreground="#666",
        ).pack(side="left", padx=8)

        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=2)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, show="headings", height=10)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._on_select())

        self.editor_frame = ttk.Frame(self)
        self.editor_frame.grid(row=3, column=0, sticky="nsew", padx=4, pady=2)

        problems_frame = ttk.LabelFrame(self, text="Problèmes de placeholders")
        problems_frame.grid(row=4, column=0, sticky="ew", padx=4, pady=2)
        problems_frame.columnconfigure(0, weight=1)
        self.problems = tk.Listbox(problems_frame, height=3)
        self.problems.grid(row=0, column=0, sticky="ew")

        self.status = ttk.Label(self, text="", anchor="w", foreground="#555")
        self.status.grid(row=5, column=0, sticky="ew", padx=6, pady=(0, 4))

    def _display_columns(self, languages: list[str] | None = None) -> list[str]:
        languages = self._languages() if languages is None else languages
        columns = ["key", "kind", "source"]
        if self.pseudo_var.get():
            columns.append("pseudo")
        columns.extend(languages)
        return columns

    def _apply_display_columns(self) -> None:
        self.tree.configure(displaycolumns=self._display_columns())

    # -- Données ---------------------------------------------------------
    def _languages(self) -> list[str]:
        return list(self.document.languages())

    def reload(self) -> None:
        self.entries = translation.collect_entries(self.document.data)
        languages = self._languages()
        if tuple(languages) != self._editor_languages:
            self._build_editors(languages)
        self._build_columns(languages)
        self._populate()
        self._update_status()
        self._update_language_combo()

        key = self._current.key if self._current is not None else None
        self._current = None
        by_key = {entry.key: entry for entry in self.entries}
        entry = by_key.get(key) if key else None
        if entry is not None and self.tree.exists(entry.key):
            self.tree.selection_set(entry.key)
            self.tree.see(entry.key)
            self._show(entry)
        else:
            self._clear_editors()

    def _build_columns(self, languages: list[str]) -> None:
        columns = ["key", "kind", "source", "pseudo", *languages]
        self.tree.configure(columns=columns, displaycolumns=self._display_columns(languages))
        headings = {"key": "Clé", "kind": "Type", "source": "Source", "pseudo": "Pseudo-locale"}
        widths = {"key": 220, "kind": 130, "source": 220, "pseudo": 200}
        for column in columns:
            self.tree.heading(column, text=headings.get(column, column))
            self.tree.column(column, width=widths.get(column, 120), anchor="w")

    def _build_editors(self, languages: list[str]) -> None:
        for child in self.editor_frame.winfo_children():
            child.destroy()
        self._editors = {}
        self._editor_languages = tuple(languages)
        for column, language in enumerate(languages):
            frame = ttk.LabelFrame(self.editor_frame, text=language)
            frame.grid(row=0, column=column, sticky="nsew", padx=2)
            self.editor_frame.columnconfigure(column, weight=1)
            text = tk.Text(frame, height=5, wrap="word", undo=False)
            text.pack(fill="both", expand=True, padx=2, pady=2)
            text.bind("<FocusOut>", lambda _event, lang=language: self._commit(lang))
            self._editors[language] = text
        pseudo_frame = ttk.LabelFrame(self.editor_frame, text="Pseudo-locale (source)")
        pseudo_frame.grid(row=0, column=len(languages), sticky="nsew", padx=2)
        self.editor_frame.columnconfigure(len(languages), weight=1)
        self._pseudo_editor = tk.Text(pseudo_frame, height=5, wrap="word", undo=False)
        self._pseudo_editor.pack(fill="both", expand=True, padx=2, pady=2)
        self._pseudo_editor.configure(state="disabled")

    def _update_language_combo(self) -> None:
        languages = self._languages()
        self.language_combo.configure(values=languages)
        if not self.language_var.get() and languages:
            self.language_var.set(
                self.document.default_language()
                if self.document.default_language() in languages
                else languages[0]
            )

    def _row_values(self, entry: translation.TranslationEntry) -> tuple[Any, ...]:
        languages = self._languages()
        default = self.document.default_language()
        source = entry.source_text(languages, default)
        values: list[Any] = [entry.key, entry.kind, source, translation.pseudo_locale(source)]
        values.extend(entry.text_for(language) for language in languages)
        return tuple(values)

    def _visible_entries(self) -> list[translation.TranslationEntry]:
        languages = self._languages()
        default = self.document.default_language()
        mode = FILTERS.get(self.filter_var.get(), "all")
        needle = self.search_var.get().strip().lower()
        problem_keys: set[str] = set()
        if mode == "placeholders":
            for problem in translation.placeholder_problems(self.entries, languages, default):
                problem_keys.add(problem.split(" ", 1)[0])
        visible: list[translation.TranslationEntry] = []
        for entry in self.entries:
            if mode == "missing" and not entry.missing(languages):
                continue
            if mode == "placeholders" and entry.key not in problem_keys:
                continue
            if needle:
                haystack = " ".join(
                    [entry.key, entry.kind, *(entry.text_for(language) for language in languages)]
                ).lower()
                if needle not in haystack:
                    continue
            visible.append(entry)
        return visible

    def _populate(self) -> None:
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for entry in self._visible_entries():
            self.tree.insert("", "end", iid=entry.key, values=self._row_values(entry))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])

    def _update_status(self) -> None:
        languages = self._languages()
        default = self.document.default_language()
        report = translation.coverage(self.entries, languages)
        parts = [
            f"{language} : {data['percent']}% ({data['translated']}/{data['total']})"
            for language, data in report.items()
        ]
        self.status.configure(text=f"{len(self.entries)} textes   |   " + "   |   ".join(parts))

        self.problems.delete(0, "end")
        problems = translation.placeholder_problems(self.entries, languages, default)
        if not problems:
            self.problems.insert("end", "Aucun problème de placeholders.")
        for problem in problems:
            self.problems.insert("end", problem)

    # -- Édition ---------------------------------------------------------
    def _on_select(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        by_key = {entry.key: entry for entry in self.entries}
        entry = by_key.get(selection[0])
        if entry is not None:
            self._show(entry)

    def _show(self, entry: translation.TranslationEntry) -> None:
        self._current = entry
        languages = self._languages()
        for language, widget in self._editors.items():
            widget.delete("1.0", "end")
            widget.insert("1.0", entry.text_for(language))
        if self._pseudo_editor is not None:
            source = entry.source_text(languages, self.document.default_language())
            self._pseudo_editor.configure(state="normal")
            self._pseudo_editor.delete("1.0", "end")
            self._pseudo_editor.insert("1.0", translation.pseudo_locale(source))
            self._pseudo_editor.configure(state="disabled")

    def _clear_editors(self) -> None:
        for widget in self._editors.values():
            widget.delete("1.0", "end")
        if self._pseudo_editor is not None:
            self._pseudo_editor.configure(state="normal")
            self._pseudo_editor.delete("1.0", "end")
            self._pseudo_editor.configure(state="disabled")

    def _commit(self, language: str) -> None:
        entry = self._current
        widget = self._editors.get(language)
        if entry is None or widget is None:
            return
        value = widget.get("1.0", "end-1c")
        if value == entry.text_for(language):
            return
        self.document.snapshot()
        translation.set_translation(
            self.document.data,
            entry.path,
            language,
            value,
            is_list=entry.is_list,
            default_language=self.document.default_language(),
        )
        self.document.touch()
        self._refresh_after_edit(entry.key)
        self.on_change()

    def _refresh_after_edit(self, key: str) -> None:
        self.entries = translation.collect_entries(self.document.data)
        by_key = {entry.key: entry for entry in self.entries}
        entry = by_key.get(key)
        if entry is not None and self.tree.exists(key):
            self.tree.item(key, values=self._row_values(entry))
            self._current = entry
        self._update_status()

    # -- CSV -------------------------------------------------------------
    def import_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Importer des traductions", filetypes=[("CSV", "*.csv"), ("Tous", "*")]
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        updates = translation.from_csv(text, self._languages())
        if not updates:
            messagebox.showinfo("Import", "Aucune traduction à importer.")
            return
        self.document.snapshot()
        applied = translation.apply_csv(
            self.document.data, self.entries, updates, self.document.default_language()
        )
        self.document.touch()
        self.reload()
        self.on_change()
        messagebox.showinfo("Import", f"{applied} clé(s) mises à jour.")

    def export_csv(self) -> None:
        game_id = str(self.document.meta().get("id", "project"))
        path = filedialog.asksaveasfilename(
            title="Exporter les traductions",
            defaultextension=".csv",
            initialfile=f"{game_id}-translations.csv",
            filetypes=[("CSV", "*.csv"), ("Tous", "*")],
        )
        if not path:
            return
        content = translation.to_csv(
            self.entries, self._languages(), self.document.default_language()
        )
        try:
            Path(path).write_text(content, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Erreur", str(exc))
            return
        messagebox.showinfo("Export", f"Écrit {path}")

    # -- Aperçu ----------------------------------------------------------
    def preview(self) -> None:
        language = self.language_var.get() or self.document.default_language()
        try:
            project = self.document.project()
        except Exception as exc:  # noqa: BLE001 - affiché dans la fenêtre
            messagebox.showerror("Erreur", str(exc))
            return
        start = project.rooms[project.meta.start_room]
        lines = [
            project.text(project.meta.title, language),
            "",
            project.text(start.name, language),
            project.text(start.description, language),
        ]
        window = tk.Toplevel(self)
        window.title(f"Aperçu — {language}")
        text = tk.Text(window, width=70, height=16, wrap="word")
        text.pack(fill="both", expand=True, padx=6, pady=6)
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")

    def play(self) -> None:
        language = self.language_var.get() or self.document.default_language()
        self.on_play(language)
