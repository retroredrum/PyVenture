"""Tests headless de l'interface pygame."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402
from pyventure.core.events import OutputLine, Style  # noqa: E402
from pyventure.core.model import GameProject  # noqa: E402
from pyventure.core.state import GameState  # noqa: E402
from pyventure.ui.pygame.art_view import ArtView  # noqa: E402
from pyventure.ui.pygame.command_input import CommandInput  # noqa: E402
from pyventure.ui.pygame.game import FONT_ORDER, GameApp  # noqa: E402
from pyventure.ui.pygame.text import wrap_text  # noqa: E402
from pyventure.ui.pygame.theme import Fonts, Theme  # noqa: E402
from pyventure.ui.pygame.transcript import Transcript  # noqa: E402

pytestmark = pytest.mark.gui


def test_wrap_text_respects_width() -> None:
    fonts = Fonts()
    text = "Un long paragraphe qui doit etre decoupe en plusieurs lignes courtes pour le test."
    lines = wrap_text(text, fonts.body, 200)
    assert len(lines) > 1
    assert all(fonts.body.size(line)[0] <= 200 for line in lines)


def test_wrap_text_keeps_explicit_newlines() -> None:
    fonts = Fonts()
    lines = wrap_text("ligne un\nligne deux", fonts.body, 500)
    assert lines == ["ligne un", "ligne deux"]


def test_wrap_text_breaks_long_word() -> None:
    fonts = Fonts()
    lines = wrap_text("a" * 200, fonts.body, 60)
    assert len(lines) > 1
    assert all(fonts.body.size(line)[0] <= 60 for line in lines)


def test_transcript_scroll_clamped() -> None:
    pygame.init()
    transcript = Transcript(Theme(), Fonts())
    transcript.append([OutputLine(f"ligne {index}") for index in range(50)])
    surface = pygame.Surface((300, 120))
    transcript.draw(surface, pygame.Rect(0, 0, 300, 120))
    transcript.scroll_by(10_000)
    assert transcript.scroll > 0
    transcript.scroll_by(-10_000)
    assert transcript.scroll == 0


def test_art_placeholder_size(project: GameProject) -> None:
    pygame.init()
    view = ArtView(project, Fonts().small)
    state = GameState.new(project)
    surface = view.surface_for(None, state)
    assert surface.get_size() == (320, 180)
    pygame.quit()


def test_fit_size_fills_available_area() -> None:
    assert ArtView.fit_size((320, 180), (800, 450)) == (800, 450)
    assert ArtView.fit_size((320, 180), (825, 442)) == (786, 442)
    assert ArtView.fit_size((320, 180), (100, 100)) == (100, 56)
    assert ArtView.fit_size((0, 0), (10, 10)) == (0, 0)


def test_fit_size_upscales_low_resolution() -> None:
    width, height = ArtView.fit_size((32, 32), (640, 360))
    assert width == 360
    assert height == 360


def test_layout_art_matches_aspect(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(960, 720))
    layout = app.layout()
    assert layout.art.height > 0
    ratio = 320 / 180
    assert abs(layout.art.width / layout.art.height - ratio) < 0.05

    scaled, _position = app.art_view.scaled(app.art_hint, app.state, layout.art)
    assert abs(scaled.get_width() - layout.art.width) <= 2
    assert abs(scaled.get_height() - layout.art.height) <= 2
    pygame.quit()


def test_layout_art_fills_on_small_window(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(640, 480))
    layout = app.layout()
    scaled, _position = app.art_view.scaled(app.art_hint, app.state, layout.art)
    assert scaled.get_width() == layout.art.width
    assert scaled.get_height() == layout.art.height
    pygame.quit()


def test_command_input_history_and_completion() -> None:
    command = CommandInput(Theme(), Fonts())
    command.text = "regarder"
    command.submit()
    command.text = "inventaire"
    command.submit()

    command.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
    assert command.text == "inventaire"
    command.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
    assert command.text == "regarder"

    command.text = "pre"
    command.handle_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB),
        lambda _text: ["prendre", "pousser"],
    )
    assert command.text == "prendre "


def test_command_input_submit_via_events() -> None:
    command = CommandInput(Theme(), Fonts())
    command.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="look"))
    assert command.text == "look"
    result = command.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert result == "look"
    assert command.text == ""


def test_app_submit_updates_state(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    before = len(app.transcript.lines)
    app.submit("prendre lampe")
    assert app.state.carries("flashlight")
    assert len(app.transcript.lines) > before
    assert app.art_hint is not None
    assert app.art_hint.room == "bedroom"
    pygame.quit()


def test_app_draw_does_not_crash(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app.submit("regarder")
    app.draw()
    assert app.screen.get_size() == (800, 600)
    pygame.quit()


def test_app_completion_candidates(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    candidates = app._completion_candidates("")
    assert "prendre" in candidates
    assert "nord" in candidates
    assert "lampe torche" in candidates
    pygame.quit()


def test_app_ending_sets_flag(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    for command in [
        "prendre lampe",
        "nord",
        "nord",
        "utiliser lampe",
        "est",
        "prendre cle",
        "utiliser cle",
    ]:
        app.submit(command)
    assert app.ended is True
    assert app.state.ended == "escaped"
    pygame.quit()


def test_transcript_style_colors_are_used() -> None:
    theme = Theme()
    assert theme.color(Style.ERROR) != theme.color(Style.ITEM)


def test_theme_variants_differ() -> None:
    assert Theme.dark().name == "dark"
    assert Theme.light().name == "light"
    assert Theme.dark().background != Theme.light().background


def test_menu_opens_and_navigates(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.menu.open is True
    assert app.menu.current() is not None
    first = app.menu.index
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    assert app.menu.index != first
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.menu.open is False
    pygame.quit()


def test_menu_language_switch(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    assert app.state.language == "fr"
    app._open_menu()
    app.menu.index = 3  # « Langue »
    app._select_menu()
    assert app.menu.open is True
    assert [item.action for item in app.menu.items] == ["lang:fr", "lang:en"]
    app.menu.index = 1
    app._select_menu()
    assert app.state.language == "en"
    assert app.menu.open is False
    pygame.quit()


def test_menu_quit_stops_app(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app._open_menu()
    app.menu.index = len(app.menu.items) - 1  # « Quitter »
    app._select_menu()
    assert app.running is False
    pygame.quit()


def test_toggle_theme_and_draw(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app._toggle_theme()
    assert app.theme.name == "light"
    app.draw()
    app._toggle_theme()
    assert app.theme.name == "dark"
    app.draw()
    pygame.quit()


def test_cycle_font_sizes(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    seen = {app.font_size}
    for _ in range(len(FONT_ORDER)):
        app._cycle_font()
        seen.add(app.font_size)
    assert seen == set(FONT_ORDER)
    app.draw()
    pygame.quit()


def test_new_game_resets_inventory(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app.submit("prendre lampe")
    assert app.state.carries("flashlight")
    app._new_game()
    assert not app.state.carries("flashlight")
    assert app.state.room == "bedroom"
    pygame.quit()


def test_save_and_load(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app.submit("prendre lampe")
    app._save()
    assert app.save_path.is_file()
    app.submit("nord")
    assert app.state.room == "corridor"
    app._load()
    assert app.state.room == "bedroom"
    assert app.state.carries("flashlight")
    pygame.quit()


def test_room_change_starts_fade(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    assert app._fade_surface is None
    app.submit("nord")
    assert app._fade_surface is not None
    app.draw()
    pygame.quit()


def test_draw_with_menu_open(project: GameProject, tmp_path) -> None:
    app = GameApp(project, save_path=tmp_path / "save.json", size=(800, 600))
    app._open_menu()
    app.draw()
    assert app.menu.open is True
    pygame.quit()
