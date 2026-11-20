"""Fenêtre de jeu pygame : art pixel en haut, transcript au centre, saisie en bas."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path

import pygame

from ...core.engine import Engine
from ...core.errors import SaveError
from ...core.events import ArtHint, OutputLine, Style
from ...core.model import GameProject
from ...core.save import default_save_path, load_state, save_state
from ...core.state import INVENTORY, GameState
from .art_view import ArtView, draw_panel
from .command_input import CommandInput
from .inventory_panel import InventoryPanel
from .menu import Menu, MenuItem
from .theme import Fonts, Theme
from .transcript import Transcript

DEFAULT_SIZE = (960, 720)
INPUT_HEIGHT = 46
MIN_SIZE = (640, 480)
FADE_MS = 250
FONT_SCALES = {"small": 0.85, "normal": 1.0, "large": 1.3}
FONT_ORDER = ["small", "normal", "large"]


@dataclass(frozen=True)
class Layout:
    art: pygame.Rect
    sidebar: pygame.Rect
    transcript: pygame.Rect
    command: pygame.Rect


class GameApp:
    """Application pygame autour du moteur."""

    def __init__(
        self,
        project: GameProject,
        *,
        language: str | None = None,
        save_path: Path | None = None,
        size: tuple[int, int] = DEFAULT_SIZE,
        resume: bool = True,
        autosave: bool = True,
        theme: str = "dark",
        font_size: str = "normal",
    ) -> None:
        pygame.init()
        self.project = project
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        title = project.text(project.meta.title, language or project.meta.default_language)
        pygame.display.set_caption(f"PyVenture — {title}")
        self.clock = pygame.time.Clock()

        self.theme = Theme.dark() if theme == "dark" else Theme.light()
        self.font_size = font_size if font_size in FONT_SCALES else "normal"
        self.fonts = Fonts(scale=FONT_SCALES[self.font_size])
        self.engine = Engine(project)
        self.state: GameState = self.engine.new_state(language)
        self.art_hint: ArtHint | None = None
        self.art_view = ArtView(
            project,
            self.fonts.small,
            base_size=(project.meta.art_width, project.meta.art_height),
        )
        self.transcript = Transcript(self.theme, self.fonts)
        self.command = CommandInput(self.theme, self.fonts)
        self.inventory = InventoryPanel(
            self.theme, self.fonts, self.art_view, self.engine.translator
        )
        self.menu = Menu()

        self.running = True
        self.ended = False
        self.autosave_enabled = autosave
        self.save_path = save_path or default_save_path(project)
        self.autosave_path = self.save_path.with_name(f"{self.save_path.stem}.autosave.json")
        self.resumed = False

        self._fade_surface: pygame.Surface | None = None
        self._fade_pos = (0, 0)
        self._fade_start = 0

        if resume and autosave:
            self._resume()
        self._start()

    # -- Cycle de vie ---------------------------------------------------
    def _resume(self) -> None:
        if not self.autosave_path.is_file():
            return
        try:
            self.state = load_state(self.project, self.autosave_path)
        except SaveError:
            return
        self.resumed = True

    def _start(self) -> None:
        result = self.engine.start(self.state)
        self.transcript.append(result.lines)
        self.art_hint = result.art
        if self.resumed:
            self.transcript.append([OutputLine(self._t("game.resumed"), Style.SYSTEM)])

    def run(self) -> int:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
        return 0

    # -- Événements -----------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            width = max(MIN_SIZE[0], event.w)
            height = max(MIN_SIZE[1], event.h)
            self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            return
        if self.ended:
            if event.type == pygame.KEYDOWN:
                self.running = False
            return
        if self.menu.open:
            self._handle_menu_event(event)
            return
        if event.type == pygame.MOUSEWHEEL:
            self.transcript.scroll_by(event.y * self.fonts.body.get_linesize() * 3)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.command.text:
                self.command.text = ""
            else:
                self._open_menu()
            return
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            direction = 1 if event.key == pygame.K_PAGEUP else -1
            self.transcript.scroll_by(direction * self.layout().transcript.height // 2)
            return

        submitted = self.command.handle_event(event, self._completion_candidates)
        if submitted is not None:
            self.submit(submitted)

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.menu.hide()
        elif event.key == pygame.K_UP:
            self.menu.move(-1)
        elif event.key == pygame.K_DOWN:
            self.menu.move(1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._select_menu()

    def submit(self, text: str) -> None:
        """Exécute une commande et met à jour l'affichage."""
        old_hint = self.art_hint
        result = self.engine.execute(text, self.state)
        self.transcript.append(result.lines)
        if result.art is not None:
            if old_hint is not None and old_hint.room != result.art.room:
                self._start_fade(old_hint)
            self.art_hint = result.art
        if result.ended:
            self.ended = True
            self._clear_autosave()
        else:
            self._autosave()
        if result.quit:
            self.running = False

    # -- Menu -----------------------------------------------------------
    def _open_menu(self) -> None:
        self.menu.show(self._t("menu.title"), self._root_menu_items())

    def _root_menu_items(self) -> list[MenuItem]:
        return [
            MenuItem("new_game", self._t("menu.new_game")),
            MenuItem("save", self._t("menu.save")),
            MenuItem("load", self._t("menu.load")),
            MenuItem("language", self._t("menu.language")),
            MenuItem("theme", self._t("menu.theme", theme=self._t(f"theme.{self.theme.name}"))),
            MenuItem("font", self._t("menu.font_size", size=self._t(f"font.{self.font_size}"))),
            MenuItem("help", self._t("menu.help")),
            MenuItem("quit", self._t("menu.quit")),
        ]

    def _select_menu(self) -> None:
        item = self.menu.current()
        if item is None:
            return
        action = item.action
        if action == "new_game":
            self._new_game()
            self.menu.hide()
        elif action == "save":
            self._save()
            self.menu.hide()
        elif action == "load":
            self._load()
            self.menu.hide()
        elif action == "language":
            self.menu.show(
                self._t("menu.language"),
                [MenuItem(f"lang:{code}", code) for code in self.project.languages],
            )
        elif action.startswith("lang:"):
            self._set_language(action.split(":", 1)[1])
            self.menu.hide()
        elif action == "theme":
            self._toggle_theme()
            self.menu.show(self._t("menu.title"), self._root_menu_items())
        elif action == "font":
            self._cycle_font()
            self.menu.show(self._t("menu.title"), self._root_menu_items())
        elif action == "help":
            self.transcript.append([OutputLine(self._t("help.text"), Style.SYSTEM)])
            self.menu.hide()
        elif action == "quit":
            self.running = False

    def _new_game(self) -> None:
        self.state = self.engine.new_state(self.state.language)
        self.transcript.clear()
        result = self.engine.start(self.state)
        self.transcript.append(result.lines)
        self.transcript.append([OutputLine(self._t("game.new_game"), Style.SYSTEM)])
        self.art_hint = result.art
        self.ended = False
        self._clear_autosave()

    def _save(self) -> None:
        with contextlib.suppress(SaveError):
            save_state(self.project, self.state, self.save_path)
            self.transcript.append([OutputLine(self._t("game.saved"), Style.SYSTEM)])

    def _load(self) -> None:
        if not self.save_path.is_file():
            self.transcript.append([OutputLine(self._t("game.no_save"), Style.SYSTEM)])
            return
        try:
            self.state = load_state(self.project, self.save_path)
        except SaveError:
            self.transcript.append([OutputLine(self._t("game.no_save"), Style.SYSTEM)])
            return
        self.transcript.clear()
        result = self.engine.look(self.state)
        self.transcript.append(result.lines)
        self.transcript.append([OutputLine(self._t("game.loaded"), Style.SYSTEM)])
        self.art_hint = result.art
        self.ended = False

    def _set_language(self, code: str) -> None:
        if code not in self.project.languages:
            self.transcript.append(
                [OutputLine(self._t("game.unknown_language", code=code), Style.ERROR)]
            )
            return
        self.state.language = code
        result = self.engine.look(self.state)
        self.transcript.append(result.lines)
        self.transcript.append([OutputLine(self._t("game.language_set", code=code), Style.SYSTEM)])
        self.art_hint = result.art

    def _toggle_theme(self) -> None:
        self.theme = Theme.light() if self.theme.name == "dark" else Theme.dark()
        self._apply_visuals()

    def _cycle_font(self) -> None:
        index = (FONT_ORDER.index(self.font_size) + 1) % len(FONT_ORDER)
        self.font_size = FONT_ORDER[index]
        self.fonts = Fonts(scale=FONT_SCALES[self.font_size])
        self._apply_visuals()

    def _apply_visuals(self) -> None:
        self.transcript.theme = self.theme
        self.transcript.fonts = self.fonts
        self.transcript._cache_width = -1
        self.command.theme = self.theme
        self.command.fonts = self.fonts
        self.inventory.theme = self.theme
        self.inventory.fonts = self.fonts
        self.art_view.font = self.fonts.small
        self.art_view._cache.clear()

    # -- Transitions ----------------------------------------------------
    def _start_fade(self, old_hint: ArtHint) -> None:
        scaled, position = self.art_view.scaled(old_hint, self.state, self.layout().art)
        self._fade_surface = scaled
        self._fade_pos = position
        self._fade_start = pygame.time.get_ticks()

    def _draw_fade(self) -> None:
        if self._fade_surface is None:
            return
        elapsed = pygame.time.get_ticks() - self._fade_start
        if elapsed >= FADE_MS:
            self._fade_surface = None
            return
        alpha = int(255 * (1 - elapsed / FADE_MS))
        faded = self._fade_surface.copy()
        faded.set_alpha(alpha)
        self.screen.blit(faded, self._fade_pos)

    # -- Rendu ----------------------------------------------------------
    def layout(self) -> Layout:
        width, height = self.screen.get_size()
        sidebar_width = min(280, max(180, width // 4))
        top_height = int((height - INPUT_HEIGHT) * 0.52)
        return Layout(
            art=pygame.Rect(0, 0, width - sidebar_width, top_height),
            sidebar=pygame.Rect(width - sidebar_width, 0, sidebar_width, top_height),
            transcript=pygame.Rect(0, top_height, width, height - INPUT_HEIGHT - top_height),
            command=pygame.Rect(0, height - INPUT_HEIGHT, width, INPUT_HEIGHT),
        )

    def draw(self) -> None:
        layout = self.layout()
        self.screen.fill(self.theme.background)
        self.art_view.draw(self.screen, layout.art, self.art_hint, self.state)
        self._draw_fade()
        self.inventory.draw(self.screen, layout.sidebar, self.project, self.state)
        draw_panel(
            self.screen,
            layout.transcript,
            self.theme,
            self.project.text(self.project.meta.title, self.state.language),
            self.fonts.small,
        )
        self.transcript.draw(self.screen, layout.transcript.inflate(0, -24).move(0, 24))
        self.command.draw(
            self.screen, layout.command, self._t("command.prompt"), self._t("menu.hint")
        )
        self.menu.draw(self.screen, self.theme, self.fonts)

    def _completion_candidates(self, _text: str) -> list[str]:
        default = self.project.meta.default_language
        language = self.state.language
        words: set[str] = set()
        words.update(self.project.vocabulary.verbs_for(language, default))
        words.update(self.project.vocabulary.directions_for(language, default))
        for object_id, game_object in self.project.objects.items():
            location = self.state.location_of(object_id)
            if location not in (INVENTORY, self.state.room):
                continue
            words.add(self.project.text(game_object.name, language))
            words.update(game_object.synonyms.get(language, ()))
        return sorted(words)

    # -- Utilitaires ----------------------------------------------------
    def _autosave(self) -> None:
        if not self.autosave_enabled:
            return
        with contextlib.suppress(SaveError):
            save_state(self.project, self.state, self.autosave_path)

    def _clear_autosave(self) -> None:
        if self.autosave_path.is_file():
            self.autosave_path.unlink()

    def _t(self, key: str, **params: object) -> str:
        return self.engine.translator.t(key, self.state.language, **params)
